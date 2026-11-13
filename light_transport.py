# SPDX-License-Identifier: GPL-3.0-only
"""Optional S1 chamber-light, three-fan and job-bound speed-mode transport.

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
from motion_control import motion_payload


class LightControlClient(KobraXClient):
    def __init__(self, *args, control_enabled=False, fan_control_enabled=False, speed_control_enabled=False, temperature_control_enabled=False, print_control_enabled=False, motion_control_enabled=False, archive_start_enabled=False, drying_control_enabled=False, drying_max_temperature=55, **kwargs):
        if type(drying_max_temperature) is not int or drying_max_temperature not in (55,65):raise ValueError('Invalid drying temperature capability')
        self.drying_max_temperature=drying_max_temperature
        if type(drying_control_enabled) is not bool:raise ValueError('Explicit drying permission required')
        if type(archive_start_enabled) is not bool:raise ValueError('Explicit boolean archive-start mode required')
        if type(motion_control_enabled) is not bool or type(print_control_enabled) is not bool or type(temperature_control_enabled) is not bool or type(control_enabled) is not bool or type(fan_control_enabled) is not bool or type(speed_control_enabled) is not bool:
            raise ValueError('Explicit boolean control mode required')
        expected_read_only = True
        if 'read_only' in kwargs and kwargs['read_only'] is not expected_read_only:
            raise ValueError('Conflicting transport modes')
        kwargs['read_only'] = expected_read_only
        super().__init__(*args, **kwargs)
        self.control_enabled = control_enabled
        self.fan_control_enabled = fan_control_enabled
        self.speed_control_enabled = speed_control_enabled
        self.temperature_control_enabled = temperature_control_enabled
        self.print_control_enabled = print_control_enabled
        self.motion_control_enabled = motion_control_enabled
        self.archive_start_enabled = archive_start_enabled
        self.drying_control_enabled = drying_control_enabled
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

    def send_speed_once(self, mode, task_id, expected_connection_id, *, send_deadline, job_guard):
        if type(mode) is not int or mode not in (1,2,3):
            raise ValueError('Invalid speed mode')
        if not isinstance(task_id,str) or not re.fullmatch(r'-1|[1-9][0-9]{0,19}', task_id):
            raise ValueError('Observed print task ID required')
        if not callable(job_guard):
            raise ValueError('Current print job guard required')
        return self._send_control_once('print', 'update',
            {'taskid':task_id, 'settings':{'print_speed_mode':mode}}, expected_connection_id,
            send_deadline=send_deadline, speed=True, job_guard=job_guard)

    def send_motion_once(self,action,value,epoch,*,send_deadline,job_guard):
        if not callable(job_guard):raise ValueError('Current idle guard required')
        return self._send_control_once('axis','turnOff' if action=='motors_off' else 'move',motion_payload(action,value),epoch,
            send_deadline=send_deadline,motion=True,job_guard=job_guard)

    def send_print_once(self, action, task_id, expected_connection_id, *, send_deadline, job_guard):
        if not isinstance(action,str) or action not in ('pause','resume','stop'):
            raise ValueError('Invalid print action')
        if not isinstance(task_id,str) or not re.fullmatch(r'-1|[1-9][0-9]{0,19}',task_id):
            raise ValueError('Observed print task required')
        if not callable(job_guard):raise ValueError('Current print guard required')
        return self._send_control_once('print',action,{'taskid':task_id},expected_connection_id,
            send_deadline=send_deadline,printing=True,job_guard=job_guard)

    def send_archive_start_once(self, operation, md5, size, mapping, expected_connection_id, *, send_deadline, job_guard):
        from reprint_launch import start_payload
        if not callable(job_guard):raise ValueError('Current idle/material guard required')
        return self._send_control_once('print','start',start_payload(operation,md5,size,mapping),expected_connection_id,
            send_deadline=send_deadline,archive_start=True,job_guard=job_guard)

    def send_temperature_once(self, heater, value, expected_connection_id, *, send_deadline, job_guard):
        limits = {'nozzle_target':320, 'bed_target':120}
        if not isinstance(heater,str) or heater not in limits or type(value) is not int or not 0 <= value <= limits[heater]:
            raise ValueError('Invalid heater or target temperature')
        if not callable(job_guard):raise ValueError('Current printer context required')
        # Slicer SET_TEMPERATURE: type selects exactly one heater. The other
        # numeric field is a protocol placeholder, not a second heater command.
        return self._send_control_once('tempature','set',
            {'type':0 if heater == 'nozzle_target' else 1,
             'target_nozzle_temp':value if heater == 'nozzle_target' else 0,
             'target_hotbed_temp':value if heater == 'bed_target' else 0},
            expected_connection_id,send_deadline=send_deadline,temperature=True,job_guard=job_guard)

    def send_drying_once(self, box, options, expected_connection_id, *, send_deadline, job_guard):
        from ace_climate import drying_options
        if type(box) is not int or not 0 <= box <= 3 or not isinstance(options,dict):raise ValueError('Invalid ACE target')
        on=options.get('status')
        if type(on) is not int or on not in (0,1):raise ValueError('Invalid drying state')
        expected=drying_options(bool(on),options.get('target_temp'),options.get('duration'),maximum=self.drying_max_temperature)
        if options != expected:raise ValueError('Unexpected drying parameters')
        return self._send_control_once('multiColorBox','setDry',{'multi_color_box':[{'id':box,'drying_status':expected}]},
            expected_connection_id,send_deadline=send_deadline,drying=True,job_guard=job_guard)

    def _send_control_once(self, kind, action, data, expected_connection_id, *, send_deadline, fan=False, speed=False, temperature=False, printing=False, motion=False, archive_start=False, drying=False, job_guard=None):
        # Capture this monotonic deadline before scheduling a worker. A queued
        # or lock-blocked worker must not send after its caller has timed out.
        now = time.monotonic()
        if (type(send_deadline) not in (int, float) or not math.isfinite(send_deadline)
                or not 0 < send_deadline - now <= 5):
            raise TimeoutError('Send authorization expired or invalid')
        if not (self.drying_control_enabled if drying else self.archive_start_enabled if archive_start else self.motion_control_enabled if motion else self.print_control_enabled if printing else self.temperature_control_enabled if temperature else self.speed_control_enabled if speed else self.fan_control_enabled if fan else self.control_enabled):
            raise PermissionError('Light control is not enabled')
        # Initial scope is the two observed stock S1s, not unknown model families.
        if str(self.mode_id) != '20025':
            raise ValueError('Light control is not validated for this model')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(self.device_id)):
            raise ValueError('Invalid device identity')
        body = {'type':kind, 'action':action, 'msgid':str(uuid.uuid4()),
                'timestamp':int(time.time() * 1000),
                'data':data}
        frame = _build_publish(self._pub_topic(kind) if archive_start or drying else self._web_topic(kind), json.dumps(body, separators=(',', ':')))
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
            if (speed or temperature or printing or motion or archive_start or drying) and not job_guard():
                raise ConnectionError('Print job changed before sending; not sent')
            if time.monotonic() >= send_deadline:
                raise TimeoutError('Send authorization expired; not sent')
            # Exactly one call. A partial/failed write has an uncertain outcome.
            # The caller must not reconnect or retry this command.
            self._sock.sendall(frame)
        finally:
            self._lock.release()
