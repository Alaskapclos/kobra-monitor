# SPDX-License-Identifier: GPL-3.0-only
"""Read live Fleet state for an update plan; never send commands or authorize deployment.

Consumers must recheck immediately before stopping services. A cached result is
not permission to install an update later. Disconnected printers remain unknown.
"""
from dataclasses import dataclass
import math
import time


@dataclass(frozen=True)
class Readiness:
    ready: bool
    reason: str
    contexts: tuple = ()
    checked_at: float = 0


def assess_fleet(fleet, clock=time.monotonic):
    ips = tuple(fleet.ips)
    if len(ips) != len(set(ips)):
        return Readiness(False, 'Die Druckerliste ist nicht eindeutig.')
    # An active historical job is not silently abandoned merely because a device
    # was removed or now reports an ambiguous/idle value.
    if fleet.history.has_active_jobs():
        return Readiness(False, 'Ein Druckauftrag ist noch aktiv. Update zurückgestellt.')
    contexts = []
    for ip in ips:
        monitor = fleet.monitors.get(ip)
        if monitor is None or monitor.client is None:
            return Readiness(False, 'Aktuelle Druckerdaten fehlen. Update zurückgestellt.')
        epoch = monitor.client.control_connection_id()  # Reads identity; no socket send.
        telemetry = monitor.telemetry
        with telemetry.lock:
            data = telemetry.motion.snapshot(epoch, telemetry.connected)
        age = data.get('light_age_s')
        if (data.get('online') is not True or type(age) not in (int, float) or
                not math.isfinite(age) or not 0 <= age <= 15 or not data.get('context')):
            return Readiness(False, 'Leerlauf nicht aktuell bestätigt. Update zurückgestellt.')
        contexts.append((ip, data['connection_id'], data['context']))
    if ips != tuple(fleet.ips):
        return Readiness(False, 'Die Druckerliste hat sich geändert. Erneut prüfen.')
    return Readiness(True, 'Alle eingerichteten Drucker melden aktuellen Leerlauf.',
                     tuple(contexts), clock())


def same_idle_state(previous, current, clock=time.monotonic):
    """A second live assessment is required; changes invalidate a prepared plan."""
    return (isinstance(previous, Readiness) and isinstance(current, Readiness) and
            previous.ready and current.ready and previous.contexts == current.contexts and
            0 <= current.checked_at - previous.checked_at <= 900 and
            0 <= clock() - current.checked_at <= 2)
