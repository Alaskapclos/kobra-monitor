# SPDX-License-Identifier: GPL-3.0-only
"""Optional S1 chamber-light and three-fan transport.

Generic methods retain the read-only frame policy. Narrow, separately enabled
entrypoints require the exact current socket identity and never reconnect/retry.
"""
import json
import math
import re
import time
import uuid

from kobrax_client import KobraXClient, _build_publish
from read_only_policy import validate_read_only_frame


class LightControlClient(KobraXClient):
    def __init__(self, *args, control_enabled=False, fan_control_enabled=False, **kwargs):
        if type(control_enabled) is not bool or type(fan_control_enabled) is not bool:
            raise ValueError('Explicit boolean control mode required')
        expected_read_only = True
        if 'read_only' in kwargs and kwargs['read_only'] is not expected_read_only:
            raise ValueError('Conflicting transport modes')
        kwargs['read_only'] = expected_read_only
        super().__init__(*args, **kwargs)
        self.control_enabled = control_enabled
        self.fan_control_enabled = fan_control_enabled
        self._control_identity = uuid.uuid4().hex

    def _send(self, frame):
        # Generic publish/publish_web and background bridge code cannot write.
        validate_read_only_frame(frame, self.mode_id, self.device_id)
        return super()._send(frame)

    def control_connection_id(self):
        with self._lock:
            if not self._running or self._sock is None:
                return None
            return self._control_identity + ':' + str(self._sock_gen)

    def send_light_once(self, on, expected_connection_id, *, send_deadline):
        if type(on) is not bool:
            raise ValueError('Light state must be boolean')
        return self._send_control_once('light', 'control',
            {'type':2, 'status':1 if on else 0, 'brightness':100 if on else 0},
            expected_connection_id, send_deadline=send_deadline)

    def send_fan_once(self, fan, value, expected_connection_id, *, send_deadline):
        fields = {'part_fan':'fan_speed_pct', 'aux_fan':'aux_fan_speed_pct',
                  'chamber_fan':'box_fan_level'}
        if not isinstance(fan, str) or fan not in fields or type(value) is not int or not 0 <= value <= 100:
            raise ValueError('Invalid fan or level')
        if not self.fan_control_enabled:
            raise PermissionError('Fan control is not enabled')
        return self._send_control_once('fan', 'setSpeed', {fields[fan]:value},
            expected_connection_id, send_deadline=send_deadline, fan=True)

    def _send_control_once(self, kind, action, data, expected_connection_id, *, send_deadline, fan=False):
        # Capture this monotonic deadline before scheduling a worker. A queued
        # or lock-blocked worker must not send after its caller has timed out.
        now = time.monotonic()
        if (type(send_deadline) not in (int, float) or not math.isfinite(send_deadline)
                or not 0 < send_deadline - now <= 5):
            raise TimeoutError('Send authorization expired or invalid')
        if not (self.fan_control_enabled if fan else self.control_enabled):
            raise PermissionError('Light control is not enabled')
        # Initial scope is the two observed stock S1s, not unknown model families.
        if str(self.mode_id) != '20025':
            raise ValueError('Light control is not validated for this model')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(self.device_id)):
            raise ValueError('Invalid device identity')
        body = {'type':kind, 'action':action, 'msgid':str(uuid.uuid4()),
                'timestamp':int(time.time() * 1000),
                'data':data}
        frame = _build_publish(self._web_topic(kind), json.dumps(body, separators=(',', ':')))
        if not self._lock.acquire(timeout=max(0, send_deadline - time.monotonic())):
            raise TimeoutError('Connection lock not available before send deadline')
        try:
            if time.monotonic() >= send_deadline:
                raise TimeoutError('Send authorization expired; not sent')
            identity = self._control_identity + ':' + str(self._sock_gen)
            if (not isinstance(expected_connection_id, str)
                    or identity != expected_connection_id or not self._running
                    or self._sock is None):
                raise ConnectionError('Connection changed before sending; not sent')
            # Exactly one call. A partial/failed write has an uncertain outcome.
            # The caller must not reconnect or retry this command.
            self._sock.sendall(frame)
        finally:
            self._lock.release()
