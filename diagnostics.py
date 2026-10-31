# SPDX-License-Identifier: GPL-3.0-only
"""Allowlisted operational summary for the owner; no printer I/O or private data."""
import math
from pathlib import Path
import time


def summary(fleet, clock=time.monotonic):
    version=(Path(__file__).resolve().parent/'VERSION').read_text().strip()
    printers=[]
    for index, ip in enumerate(fleet.ips, 1):
        item=fleet.monitors.get(ip)
        snapshot=item.telemetry.snapshot() if item else {}
        state=snapshot.get('connection')
        if state not in ('online','offline','stale','connecting'):state='connecting'
        age=snapshot.get('age_s')
        age=round(age,1) if type(age) in (int,float) and math.isfinite(age) and age>=0 else None
        section=snapshot.get('section_age_s') or {}
        temperature=section.get('temperature')
        fresh_temperature=(state=='online' and type(temperature) in (int,float)
                           and math.isfinite(temperature) and 0<=temperature<=90)
        printers.append({'number':index,'state':state,'age_seconds':age,
                         'temperature_current':fresh_temperature})
    with fleet.history.lock:
        jobs=fleet.history.db.execute('SELECT count(*) FROM jobs').fetchone()[0]
        devices=fleet.history.db.execute('SELECT count(*) FROM push_devices').fetchone()[0]
        failed=fleet.history.db.execute("SELECT count(*) FROM push_devices WHERE last_status='failed'").fetchone()[0]
        pending=fleet.history.db.execute("SELECT count(*) FROM push_queue WHERE status='pending'").fetchone()[0]
    task=fleet.notifications.task
    return {'format':'kobra-monitor-check-v1','version':version,'read_only':True,
            'uptime_seconds':max(0,int(clock()-fleet.started)),
            'printers':printers,'camera_decoder_ready':bool(fleet.cameras.available()),
            'history':{'available':True,'jobs':jobs},
            'notifications':{'worker_running':bool(task and not task.done()),
                             'devices':devices,'devices_with_errors':failed,'pending':pending}}
