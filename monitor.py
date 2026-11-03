"""Local read-only monitor using the bundled, attributed OSS clients.

SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import asyncio
import contextlib
import copy
import hashlib
import ipaddress
import json
import logging
import math
import os
import re
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
import uuid
import urllib.request
from urllib.parse import quote
from types import SimpleNamespace

BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE/'vendor/kobra-bridge'), str(BASE/'vendor/kobra-connect')]
from aiohttp import web
from kobra_connect import do_handshake, CloudModeError
from history import History
from access import Access
from configuration import printer_ips, load_config, save_config
from spools import Spools
from spoolman_view import gateway, gateway_path
from notifications import Notifications
from motion_control import MotionState, MOTION_ACTIONS, valid_motion
from print_job_control import PrintJobState, PRINT_ACTIONS, ACTIVE_PHASE_CODES
from controls import LightControls, ControlRefused, FAN_FIELDS, TEMP_LIMITS
from light_transport import LightControlClient
from diagnostics import summary as diagnostic_summary
from camera_view import CameraViews, decoder_available

STALE_AFTER = 90
RETRY_AFTER = 15


class Telemetry:
    """Separate received data from connectivity and per-section freshness."""
    def __init__(self, ip, clock=time.monotonic):
        self.ip, self.clock = ip, clock
        self.lock = threading.RLock()
        self.seen = {}
        self.data = {}
        self.connected = False
        self.message = 'Verbindung zum Drucker wird aufgebaut.'
        self.last_project = None
        self.device_values = {}
        self.device_seen = {}
        self.device_session = 0
        self.device_sessions = {}
        self.device_revisions = {}
        self.device_connections = {}
        self.job_task_id = None
        self.job_filename = None
        self.job_elapsed = None
        self.job_phase = None
        self.job_seen = float('-inf')
        self.job_connection = None
        self.job_token = uuid.uuid4().hex
        self.thermal_seen = float("-inf")
        self.thermal_connection = None
        self.thermal_token = None
        self.print_job = PrintJobState(clock)
        self.motion = MotionState(clock)
        self.light_revision = 0
        self.light_connection_id = None

    def link(self, connected, message=''):
        with self.lock:
            if self.connected and not connected:
                self.device_session += 1
            self.connected = connected
            self.message = message

    def receive(self, kind, payload, bridge, connection_id=None):
        with self.lock:self.motion.receive(kind,payload,connection_id)
        if payload.get('code') not in (None, 200) or not isinstance(payload.get('data'), dict):
            return
        raw = payload['data']
        with self.lock:self.print_job.receive(kind,payload,connection_id)
        self.track_speed_job(kind, payload, connection_id)
        # Read received fields directly; bridge defaults are not measurements.
        candidates = {}
        if kind in ('info', 'fan'):
            for source, target in (('fan_speed_pct', 'fan_speed'),
                    ('aux_fan_speed_pct', 'aux_fan_speed'),
                    ('box_fan_level', 'box_fan_level'),
                    ('print_speed_mode', 'speed_mode')):
                if source in raw:
                    candidates[target] = raw[source]
        if kind == 'print' and isinstance(raw.get('settings'), dict):
            if 'print_speed_mode' in raw['settings']:
                candidates['speed_mode'] = raw['settings']['print_speed_mode']
        if kind in ('info','tempature'):
            temps = raw.get('temp') if kind == 'info' else raw
            if isinstance(temps,dict):
                for source,target in (('target_nozzle_temp','nozzle_target'),('target_hotbed_temp','bed_target')):
                    val = temps.get(source)
                    if type(val) in (int,float) and math.isfinite(val) and int(val) == val and 0 <= val <= TEMP_LIMITS[target]:
                        candidates[target] = int(val)
        if kind == 'print' and payload.get('state') not in (None,'done','printing'):
            with self.lock:self.thermal_seen = float('-inf')
        if kind == 'info':
            with self.lock:
                project = raw.get('project')
                idle = raw.get('state') == 'free' and project is None
                printing = (isinstance(project,dict) and project.get('state') == 'printing'
                    and project.get('pause',0) == 0 and self.job_task_id is not None
                    and self.job_filename is not None and project.get('filename') == self.job_filename
                    and type(project.get('task_id')) in (str,int) and str(project['task_id']) == self.job_task_id)
                if idle or printing:
                    self.thermal_seen = self.clock();self.thermal_connection = connection_id
                    self.thermal_token = self.job_token
                else:self.thermal_seen = float('-inf')
        if kind == 'light':
            lights = raw.get('lights')
            chamber = [entry for entry in lights if isinstance(entry, dict)
                       and type(entry.get('type')) is int and entry['type'] == 2] if isinstance(lights, list) else []
            light = chamber[0] if len(chamber) == 1 else raw if raw.get('type') == 2 else {}
            if 'status' in light:
                candidates['light_on'] = light['status']
            if 'brightness' in light:
                candidates['light_brightness'] = light['brightness']
        with self.lock:
            for key, val in candidates.items():
                if key == 'light_on':
                    if type(val) not in (bool, int) or val not in (0, 1):
                        continue
                    val = bool(val)
                elif (type(val) not in (int, float) or not math.isfinite(val)
                        or val < 0 or val > (TEMP_LIMITS[key] if key in TEMP_LIMITS else 100 if key != 'speed_mode' else 255)):
                    continue
                if key in ('speed_mode', 'box_fan_level') and int(val) != val:
                    continue
                if key == 'light_on':
                    self.light_revision += 1
                    self.light_connection_id = connection_id
                self.device_revisions[key] = self.device_revisions.get(key, 0)+1
                self.device_connections[key] = connection_id
                self.device_values[key] = val
                self.device_seen[key] = self.clock()
                self.device_sessions[key] = self.device_session
        groups = []
        if kind == 'info':
            if any(key in raw for key in ('printerName','model','version')):
                groups.append('printer')
            if isinstance(raw.get('temp'),dict) and 'curr_nozzle_temp' in raw['temp']:
                groups.append('temperature')
            if 'state' in raw or 'project' in raw:
                groups.append('print')
        elif kind == 'tempature' and 'curr_nozzle_temp' in raw:
            groups.append('temperature')
        elif kind == 'print' and ('progress' in raw or 'filename' in raw
                or payload.get('state') in ('printing','paused','finished','free','canceled','stoped')):
            groups.append('print')
        elif kind == 'multiColorBox' and isinstance(raw.get('multi_color_box'),list):
            groups.append('ace')
        if not groups:
            return
        with self.lock:
            now = self.clock()
            for group in groups:
                self.seen[group] = now
            state = bridge._state
            fields = {
                'printer':('printer_name','model_id','model_name','firmware_version'),
                'temperature':('nozzle_temp','nozzle_target','bed_temp','bed_target','fan_speed'),
                'print':('print_state','progress','filename','print_duration','remain_time','curr_layer','total_layers'),
            }
            for group in groups:
                for key in fields.get(group, ()):
                    self.data[key] = copy.deepcopy(state.get(key))
            if 'ace' in groups:
                slot_fields = ('index','global_index','box_id','type','color','status','edit_status','consumables_percent')
                has_boxes = bool(raw['multi_color_box'])
                self.data['ace_slots'] = [{k:copy.deepcopy(slot.get(k)) for k in slot_fields} for slot in bridge._ams_slots] if has_boxes else []
                for result, slot in zip(self.data['ace_slots'], bridge._ams_slots):
                    from spools import spool_sku
                    result['sku'] = spool_sku(slot.get('sku'))
                self.data['loaded_slot'] = bridge._ams_loaded_slot if has_boxes else -1
                self.data['ace_drying'] = copy.deepcopy(state.get('ace_drying', {})) if has_boxes else {}
                self.data['ace_units'] = list(bridge._ace_box_ids) if has_boxes else []
            previous = payload['data'].get('last_project')
            if isinstance(previous, dict):
                self.last_project = {k: previous.get(k) for k in
                    ('state','filename','progress','curr_layer','total_layers','print_time')}

    def track_speed_job(self, kind, payload, connection_id):
        raw = payload['data']
        with self.lock:
            if kind == 'info':
                project = raw.get('project')
                if not isinstance(project,dict):
                    if raw.get('state') == 'free':
                        if self.job_phase != 'free' or self.job_connection != connection_id:
                            self.job_token = uuid.uuid4().hex
                        self.job_phase = 'free';self.job_connection = connection_id
                        self.job_seen = float('-inf');self.job_task_id = None;self.job_filename = None;self.job_elapsed = None
                    return
                task = project.get('task_id')
                filename = project.get('filename')
                phase = project.get('state')
                if project.get('pause') == 1:phase = 'paused'
            elif kind == 'print':
                task = raw.get('taskid')
                filename = raw.get('filename')
                phase = payload.get('state')
                if phase not in ('printing','paused','pausing','resuming','finished','canceled','stoped','free'):
                    phase = None
            else:return
            task = str(task) if type(task) in (str,int) and re.fullmatch(r'-1|[1-9][0-9]{0,19}',str(task)) else None
            filename = filename if isinstance(filename,str) and 0 < len(filename) <= 1024 else None
            elapsed = project.get('print_time') if kind == 'info' else raw.get('print_time')
            elapsed = elapsed if type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed >= 0 else None
            changed = ((elapsed is not None and self.job_elapsed is not None and elapsed < self.job_elapsed) or
                       (task is not None and task != self.job_task_id) or
                       (filename is not None and filename != self.job_filename) or
                       connection_id != self.job_connection or
                       (phase is not None and phase != self.job_phase))
            if changed:
                self.job_token = uuid.uuid4().hex
                self.job_seen = float('-inf')
            if phase is not None:self.job_phase = phase
            if task is not None:self.job_task_id = task
            if filename is not None:self.job_filename = filename
            if task is not None and filename is not None and phase == 'printing':
                self.job_seen = self.clock();self.job_connection = connection_id
                if elapsed is not None:self.job_elapsed = elapsed

    def snapshot(self):
        with self.lock:
            now = self.clock()
            ages = {group: max(0, round(now-stamp, 1)) for group,stamp in self.seen.items()}
            latest = min(ages.values()) if ages else None
            if not self.connected:
                status = 'offline' if ages else 'connecting'
            elif latest is None:
                status = 'connecting'
            elif latest > STALE_AFTER:
                status = 'stale'
            else:
                status = 'online'
            return {'read_only':True, 'ip':self.ip, 'connection':status,
                    'message':self.message, 'age_s':latest, 'section_age_s':ages,
                    'stale_after_s':STALE_AFTER, 'data':copy.deepcopy(self.data) if ages else None,
                    'device_status': {key: {'value': value,
                        'age_s': max(0, round(now-self.device_seen[key], 1)),
                        'current_session': self.device_sessions[key] == self.device_session}
                        for key, value in self.device_values.items()},
                    'last_project':copy.deepcopy(self.last_project), 'server_time':time.time()}


class Monitor:
    def __init__(self, ip, runtime, data_dir, history=None, light_control=False, fan_control=False, speed_control=False, temperature_control=False, print_control=False, motion_control=False):
        self.ip, self.runtime, self.data_dir = ip, Path(runtime), data_dir
        self.telemetry = Telemetry(ip)
        self.client = self.bridge = None
        self.task = None
        self.history = history
        self.light_control_enabled = light_control
        self.fan_control_enabled = fan_control
        self.speed_control_enabled = speed_control
        self.temperature_control_enabled = temperature_control
        self.print_control_enabled = print_control
        self.motion_control_enabled = motion_control

    async def connect(self):
        hs = await asyncio.to_thread(do_handshake, self.ip)
        if hs.broker_host != self.ip or hs.broker_port != 9883:
            raise ValueError('Unexpected MQTT broker')
        cert = self.runtime/'anycubic_slicer.crt'
        key = self.runtime/'anycubic_slicer.key'
        cert.write_text(hs.device_cert)
        key.write_text(hs.device_key)
        os.chmod(cert, 0o600)
        os.chmod(key, 0o600)
        # Certificate paths belong to this client, never shared process globals.
        from kobrax_client import KobraXClient
        from kobrax_moonraker_bridge import KobraXBridge
        logging.getLogger().setLevel(logging.WARNING)
        args = SimpleNamespace(read_only=True, model_id=hs.model_id, mode_id=hs.model_id,
            printer_ip=self.ip, device_id=hs.device_id, data_dir=self.data_dir,
            camera_on_print=0, spoolman_server='', poll_interval=3)
        self.client = LightControlClient(self.ip, hs.username, hs.password, hs.model_id, hs.device_id,
                                  client_id='kobra-monitor-'+uuid.uuid4().hex[:12],
                                  control_enabled=self.light_control_enabled, fan_control_enabled=self.fan_control_enabled, speed_control_enabled=self.speed_control_enabled, temperature_control_enabled=self.temperature_control_enabled, print_control_enabled=self.print_control_enabled, motion_control_enabled=self.motion_control_enabled,
                                  cert_file=str(cert), key_file=str(key))
        self.bridge = KobraXBridge(self.client, args=args)
        self.client.callbacks.setdefault('fan/report', lambda payload: None)
        for suffix, original in list(self.client.callbacks.items()):
            kind = suffix.split('/')[0]
            def report(payload, callback=original, kind=kind, source_bridge=self.bridge, source_client=self.client):
                callback(payload)
                self.telemetry.receive(kind, payload, source_bridge, source_client.control_connection_id())
                if self.history:
                    self.history.observe(self.ip,kind,payload,self.telemetry.snapshot())
            self.client.callbacks[suffix] = report
        connection = asyncio.create_task(asyncio.to_thread(self.client.connect))
        try:
            await asyncio.shield(connection)
        except asyncio.CancelledError:
            with contextlib.suppress(Exception):
                await connection
            raise
        self.telemetry.link(True)
        if self.history:self.history.link(self.ip,True)

    def light_snapshot(self):
        client = self.client
        epoch = client.control_connection_id() if client else None
        with self.telemetry.lock:
            return {'online': bool(epoch and epoch == self.telemetry.light_connection_id
                                   and self.telemetry.connected),
                    'connection_id': epoch,
                    'light_on': self.telemetry.device_values.get('light_on'),
                    'light_revision': self.telemetry.light_revision,
                    'light_age_s': max(0, self.telemetry.clock()-self.telemetry.device_seen.get('light_on', float('-inf')))}

    def light_supported(self):
        return bool(self.light_control_enabled and self.client
                    and str(self.client.mode_id) == '20025')

    async def refresh_light(self):
        client = self.client
        if not self.light_supported() or not client.control_connection_id():
            raise ControlRefused('Lichtsteuerung für diesen Drucker nicht verfügbar.')
        await asyncio.wait_for(asyncio.to_thread(client.publish, 'light', 'query', None, 1), 2)

    async def send_light(self, desired, epoch):
        client = self.client
        if not self.light_supported() or not client:
            raise ControlRefused('Lichtsteuerung für diesen Drucker nicht verfügbar.')
        deadline = time.monotonic()+4
        await asyncio.to_thread(client.send_light_once, desired, epoch, send_deadline=deadline)
        # Read back the state explicitly; never retry the control command.
        await asyncio.to_thread(client.publish, 'light', 'query', None, .5)

    def fan_supported(self):
        return bool(self.fan_control_enabled and self.client and str(self.client.mode_id) == '20025')

    def fan_snapshot(self, control):
        field = FAN_FIELDS.get(control)
        client = self.client
        epoch = client.control_connection_id() if client else None
        with self.telemetry.lock:
            return {'online': bool(epoch and epoch == self.telemetry.device_connections.get(field)
                                   and self.telemetry.connected),
                    'connection_id': epoch,
                    'light_on': self.telemetry.device_values.get(field),
                    'light_revision': self.telemetry.device_revisions.get(field, 0),
                    'light_age_s': max(0, self.telemetry.clock()-self.telemetry.device_seen.get(field, float('-inf')))}

    async def refresh_fan(self):
        if not self.fan_supported() or not self.client.control_connection_id():
            raise ControlRefused('Lüftersteuerung für diesen Drucker nicht verfügbar.')
        await asyncio.wait_for(asyncio.to_thread(self.client.publish, 'fan', 'query', None, 1), 2)

    async def send_fan(self, control, desired, epoch):
        if not self.fan_supported():
            raise ControlRefused('Lüftersteuerung für diesen Drucker nicht verfügbar.')
        client = self.client
        await asyncio.to_thread(client.send_fan_once, control, desired, epoch, send_deadline=time.monotonic()+4)
        await asyncio.to_thread(client.publish, 'fan', 'query', None, .5)

    def speed_supported(self):
        return bool(self.speed_control_enabled and self.client and str(self.client.mode_id) == '20025')

    def speed_snapshot(self):
        if not self.speed_supported() or not self.history:return None
        jobs = [j for j in self.history.jobs(self.ip) if j['ended_at'] is None and j['state'] == 'printing']
        if len(jobs) != 1:return None
        client = self.client
        epoch = client.control_connection_id() if client else None
        t = self.telemetry
        with t.lock:
            if not t.job_filename or jobs[0]['filename'] != t.job_filename:return None
            signature = (t.job_token,t.job_task_id,t.job_filename,t.job_connection)
            context = hashlib.sha256(json.dumps([jobs[0]['id'],signature]).encode()).hexdigest()
            return {'online':bool(epoch and t.connected and t.job_phase == 'printing'
                              and epoch == t.job_connection == t.device_connections.get('speed_mode')),
                    'connection_id':epoch,'light_on':t.device_values.get('speed_mode'),
                    'light_revision':t.device_revisions.get('speed_mode',0),
                    'light_age_s':max(0,t.clock()-min(t.job_seen,t.device_seen.get('speed_mode',float('-inf')))),
                    'context':context,'task_id':t.job_task_id,'signature':signature}

    async def refresh_speed(self):
        if not self.speed_supported() or not self.client.control_connection_id():
            raise ControlRefused('Speed Mode ist für diesen Drucker nicht freigegeben.')
        await asyncio.wait_for(asyncio.to_thread(self.client.publish,'info','query',None,1),2)

    async def send_speed(self, desired, epoch, context):
        data = self.speed_snapshot()
        if not data or not data['online'] or data['context'] != context or data['connection_id'] != epoch or data['light_age_s'] > 15:
            raise ControlRefused('Druckauftrag geändert oder veraltet; nicht gesendet.')
        expected, before = data['signature'], data['light_on']
        def guard():
            t = self.telemetry
            with t.lock:
                return (t.connected and t.job_phase == 'printing' and
                    (t.job_token,t.job_task_id,t.job_filename,t.job_connection) == expected and
                    t.device_values.get('speed_mode') == before and
                    t.device_connections.get('speed_mode') == epoch and
                    0 <= t.clock()-min(t.job_seen,t.device_seen.get('speed_mode',float('-inf'))) <= 15)
        client = self.client
        await asyncio.to_thread(client.send_speed_once,desired,data['task_id'],epoch,
            send_deadline=time.monotonic()+4,job_guard=guard)
        await asyncio.to_thread(client.publish,'info','query',None,.5)

    def print_supported(self):
        return bool(self.print_control_enabled and self.client and str(self.client.mode_id)=='20025')

    def print_snapshot(self):
        if not self.print_supported() or not self.history:return None
        epoch=self.client.control_connection_id()
        jobs=[j for j in self.history.jobs(self.ip) if j['ended_at'] is None]
        t=self.telemetry
        with t.lock:
            p=t.print_job
            if p.phase in ACTIVE_PHASE_CODES:
                if len(jobs)!=1 or jobs[0]['filename']!=p.filename:return None
                p.history_id=jobs[0]['id']
            if not p.history_id or not p.task or not p.filename:return None
            signature=p.signature()
            return {'online':bool(t.connected and epoch and epoch==p.connection),
                    'connection_id':epoch,'light_on':p.phase,'light_revision':p.revision,
                    'light_age_s':max(0,p.clock()-p.seen),
                    'context':hashlib.sha256(json.dumps(signature).encode()).hexdigest(),
                    'signature':signature,'task_id':p.task,'filename':p.filename}

    async def refresh_print(self):
        if not self.print_supported() or not self.client.control_connection_id():raise ControlRefused('Druckaktionen nicht freigegeben.')
        await asyncio.wait_for(asyncio.to_thread(self.client.publish,'info','query',None,1),2)

    async def send_print(self,control,epoch,context):
        data=self.print_snapshot()
        if (control not in PRINT_ACTIONS or not data or not data['online'] or data['context']!=context
            or data['connection_id']!=epoch or data['light_age_s']>15 or data['light_on'] not in PRINT_ACTIONS[control][2]):
            raise ControlRefused('Druckauftrag oder Zustand geändert; nicht gesendet.')
        signature,before=data['signature'],data['light_on']
        def guard():
            t=self.telemetry
            with t.lock:
                p=t.print_job
                return t.connected and p.signature()==signature and p.phase==before and 0<=p.clock()-p.seen<=15
        client=self.client
        await asyncio.to_thread(client.send_print_once,PRINT_ACTIONS[control][0],data['task_id'],epoch,
            send_deadline=time.monotonic()+4,job_guard=guard)
        await asyncio.to_thread(client.publish,'info','query',None,.5)

    def motion_supported(self):
        return bool(self.motion_control_enabled and self.client and str(self.client.mode_id)=='20025')

    def motion_snapshot(self):
        if not self.motion_supported():return None
        epoch=self.client.control_connection_id()
        with self.telemetry.lock:
            return self.telemetry.motion.snapshot(epoch,self.telemetry.connected)

    async def refresh_motion(self):
        if not self.motion_supported():raise ControlRefused('Bewegung nicht freigegeben.')
        await asyncio.wait_for(asyncio.to_thread(self.client.publish,'info','query',None,1),2)

    async def send_motion(self,control,desired,epoch,context):
        data=self.motion_snapshot()
        if not data or not data['online'] or data['context']!=context or data['connection_id']!=epoch or data['light_age_s']>15:
            raise ControlRefused('Aktueller Leerlauf fehlt; nicht gesendet.')
        def guard():
            # Socket lock is held by transport; never acquire it again here.
            with self.telemetry.lock:
                current=self.telemetry.motion.snapshot(epoch,self.telemetry.connected)
                return current['online'] and current['context']==context and current['light_age_s']<=15
        await asyncio.to_thread(self.client.send_motion_once,control,desired,epoch,
            send_deadline=time.monotonic()+4,job_guard=guard)

    def temperature_supported(self):
        return bool(self.temperature_control_enabled and self.client and str(self.client.mode_id) == '20025')

    def temperature_state(self, control, epoch):
        # No client lock here: also used inside the transport socket lock.
        t = self.telemetry
        with t.lock:
            context = hashlib.sha256(json.dumps([t.job_token,t.job_task_id,t.job_filename,t.job_phase,t.thermal_connection]).encode()).hexdigest()
            return {'online':bool(t.connected and epoch and epoch == t.thermal_connection == t.device_connections.get(control)
                                  and t.thermal_token == t.job_token),
                'connection_id':epoch,'light_on':t.device_values.get(control),
                'light_revision':t.device_revisions.get(control,0),
                'light_age_s':max(0,t.clock()-min(t.thermal_seen,t.device_seen.get(control,float('-inf')))),
                'context':context}

    def temperature_snapshot(self, control):
        if not self.temperature_supported() or control not in TEMP_LIMITS:return None
        return self.temperature_state(control,self.client.control_connection_id())

    async def refresh_temperature(self):
        if not self.temperature_supported() or not self.client.control_connection_id():
            raise ControlRefused('Temperatursteuerung für diesen Drucker nicht freigegeben.')
        await asyncio.wait_for(asyncio.to_thread(self.client.publish,'info','query',None,1),2)

    async def send_temperature(self, control, desired, epoch, context):
        data = self.temperature_snapshot(control)
        if not data or not data['online'] or data['context'] != context or data['connection_id'] != epoch or data['light_age_s'] > 15:
            raise ControlRefused('Druckerzustand geändert oder veraltet; nicht gesendet.')
        before = data['light_on']
        def guard():
            current = self.temperature_state(control,epoch)
            return current['online'] and current['context'] == context and current['light_on'] == before and 0 <= current['light_age_s'] <= 15
        client = self.client
        await asyncio.to_thread(client.send_temperature_once,control,desired,epoch,
            send_deadline=time.monotonic()+4,job_guard=guard)
        await asyncio.to_thread(client.publish,'info','query',None,.5)

    async def disconnect(self):
        client, bridge = self.client, self.bridge
        self.client = self.bridge = None
        self.telemetry.link(False, 'Verbindung unterbrochen. Neuer Versuch folgt automatisch.')
        if self.history:self.history.link(self.ip,False)
        if client:
            await asyncio.to_thread(client.disconnect)
            reader = getattr(client, '_reader_thread', None)
            if reader:
                await asyncio.to_thread(reader.join, 2)
        if bridge:
            bridge._store._conn.close()
        for name in ('anycubic_slicer.crt', 'anycubic_slicer.key'):
            (self.runtime/name).unlink(missing_ok=True)

    async def run(self):
        try:
            while True:
                try:
                    if self.client is None:
                        self.telemetry.link(False, 'Verbindung zum Drucker wird aufgebaut.')
                        await self.connect()
                        next_info = next_ace = next_light = 0
                        session_started = time.monotonic()
                    connected = self.client._sock is not None and self.client._running
                    self.telemetry.link(connected, '' if connected else 'Drucker nicht erreichbar. Verbindung wird erneuert.')
                    if self.history:self.history.link(self.ip,connected)
                    snapshot = self.telemetry.snapshot()
                    age = snapshot['age_s']
                    if time.monotonic()-session_started>STALE_AFTER and (age is None or age>STALE_AFTER):
                        raise TimeoutError('No fresh telemetry')
                    now = time.monotonic()
                    if connected and now >= next_info:
                        await asyncio.wait_for(asyncio.to_thread(self.client.query_info), timeout=12)
                        next_info = time.monotonic()+(10 if self.speed_control_enabled or self.temperature_control_enabled or self.print_control_enabled else 30)
                    if connected and now >= next_light:
                        await asyncio.wait_for(asyncio.to_thread(self.client.publish,
                            'light', 'query', None, timeout=5), timeout=7)
                        if self.fan_control_enabled:
                            await asyncio.wait_for(asyncio.to_thread(self.client.publish, 'fan', 'query', None, timeout=1), timeout=3)
                        next_light = time.monotonic()+(10 if self.light_control_enabled or self.fan_control_enabled else 30)
                    if connected and now >= next_ace:
                        await asyncio.wait_for(asyncio.to_thread(self.client.query_multicolor_box), timeout=12)
                        next_ace = time.monotonic()+60
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    await self.disconnect()
                    message = ('Bitte LAN-Modus am Drucker aktivieren.' if isinstance(exc,CloudModeError)
                               else 'Drucker nicht erreichbar. Neuer Verbindungsversuch in Kürze.')
                    self.telemetry.link(False, message)
                    await asyncio.sleep(RETRY_AFTER)
        finally:
            await self.disconnect()

    async def start(self, app):
        self.task = asyncio.create_task(self.run())

    async def stop(self, app):
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task


class Fleet:
    """Independent sessions, certificates, caches and databases per printer."""
    def __init__(self, ips, runtime, data_dir, *, light_control_ips=None, fan_control_ips=None, speed_control_ips=None, temperature_control_ips=None, print_control_ips=None, motion_control_ips=None):
        self.motion_control_ips = set(printer_ips(motion_control_ips)) if motion_control_ips else set()
        self.print_control_ips = set(printer_ips(print_control_ips)) if print_control_ips else set()
        self.temperature_control_ips = set(printer_ips(temperature_control_ips)) if temperature_control_ips else set()
        self.speed_control_ips = set(printer_ips(speed_control_ips)) if speed_control_ips else set()
        self.fan_control_ips = set(printer_ips(fan_control_ips)) if fan_control_ips else set()
        self.light_control_ips = set(printer_ips(light_control_ips)) if light_control_ips else set()
        self.started = time.monotonic()
        self.ips = list(ips)
        self.ip = self.ips[0] if self.ips else None
        self.runtime = Path(runtime)
        self.data_dir = Path(data_dir)
        self.config_lock = asyncio.Lock()
        self.monitors = {}
        self.history = History(Path(data_dir)/'history.sqlite3')
        for ip in self.ips:
            private = Path(runtime)/ip
            private.mkdir(mode=0o700)
            self.monitors[ip] = Monitor(ip, private, str(Path(data_dir)/ip),self.history, ip in self.light_control_ips, ip in self.fan_control_ips, ip in self.speed_control_ips, ip in self.temperature_control_ips, ip in self.print_control_ips, ip in self.motion_control_ips)
        self.controls = LightControls(Path(data_dir)/'history.sqlite3', self.light_snapshot,
            self.send_light, enabled=True, fan_snapshot=self.fan_snapshot, fan_sender=self.send_fan, speed_snapshot=self.speed_snapshot, speed_sender=self.send_speed, temperature_snapshot=self.temperature_snapshot, temperature_sender=self.send_temperature, print_snapshot=self.print_snapshot, print_sender=self.send_print, motion_snapshot=self.motion_snapshot, motion_sender=self.send_motion) if self.light_control_ips or self.fan_control_ips or self.speed_control_ips or self.temperature_control_ips or self.print_control_ips or self.motion_control_ips else None
        self.telemetry = self
        self.cameras = CameraViews()
        self.notifications = Notifications(self.history,self.data_dir,self.notification_names)
        self.spools = Spools(self.data_dir)
        self.history.report_materials=self.report_materials

    @property
    def read_only(self):
        return not bool((self.light_control_ips | self.fan_control_ips | self.speed_control_ips | self.temperature_control_ips | self.print_control_ips | self.motion_control_ips) & set(self.ips))

    def light_snapshot(self, ip):
        item = self.monitors.get(ip)
        return item.light_snapshot() if item and item.light_supported() else None

    async def send_light(self, ip, desired, epoch):
        item = self.monitors.get(ip)
        if not item or not item.light_supported():
            raise ControlRefused('Dieser Drucker ist nicht für Lichtsteuerung freigegeben.')
        await item.send_light(desired, epoch)

    def fan_snapshot(self, ip, control):
        item = self.monitors.get(ip)
        return item.fan_snapshot(control) if item and item.fan_supported() else None

    async def send_fan(self, ip, control, desired, epoch):
        item = self.monitors.get(ip)
        if not item or not item.fan_supported():
            raise ControlRefused('Dieser Drucker ist nicht für Lüftersteuerung freigegeben.')
        await item.send_fan(control, desired, epoch)

    def speed_snapshot(self, ip):
        item = self.monitors.get(ip)
        return item.speed_snapshot() if item else None

    async def send_speed(self, ip, desired, epoch, context):
        item = self.monitors.get(ip)
        if not item or not item.speed_supported():
            raise ControlRefused('Dieser Drucker ist nicht für Speed Mode freigegeben.')
        await item.send_speed(desired,epoch,context)

    def temperature_snapshot(self,ip,control):
        item = self.monitors.get(ip)
        return item.temperature_snapshot(control) if item else None

    async def send_temperature(self,ip,control,desired,epoch,context):
        item = self.monitors.get(ip)
        if not item or not item.temperature_supported():raise ControlRefused('Temperatursteuerung nicht freigegeben.')
        await item.send_temperature(control,desired,epoch,context)

    def print_snapshot(self,ip):
        item=self.monitors.get(ip)
        return item.print_snapshot() if item else None

    async def send_print(self,ip,control,epoch,context):
        item=self.monitors.get(ip)
        if not item or not item.print_supported():raise ControlRefused('Druckaktionen nicht freigegeben.')
        await item.send_print(control,epoch,context)

    def motion_snapshot(self,ip):
        item=self.monitors.get(ip)
        return item.motion_snapshot() if item else None

    async def send_motion(self,ip,control,desired,epoch,context):
        item=self.monitors.get(ip)
        if not item or not item.motion_supported():raise ControlRefused('Bewegung nicht freigegeben.')
        await item.send_motion(control,desired,epoch,context)

    def report_materials(self,ip):
        state=self.spools.state()
        printers=[self.monitors[v].telemetry.snapshot() for v in self.ips if v in self.monitors]
        detections=[r for r in self.spools.detections(printers) if r['ip']==ip]
        ids={r['spool_id'] for r in detections if r['status']=='recognized'}
        manual=dict(self.spools.mappings.get(ip,{}))
        return {'basis':'Zum Archivierungszeitpunkt erfasst; keine Verbrauchsmessung.',
                'captured_at':time.time(),'inventory_current':state['inventory_current'],
                'inventory_checked_at':state['checked_at'],'detections':detections,'manual_slots':manual,
                'inventory':[r for r in state['spools'] if r['id'] in ids|set(manual.values())] if state['inventory_current'] else []}

    def notification_names(self):
        return {ip:(item.telemetry.snapshot().get('data') or {}).get('printer_name') or 'Drucker '+str(self.ips.index(ip)+1) for ip,item in self.monitors.items()}

    def snapshot(self):
        printers = [self.monitors[ip].telemetry.snapshot() for ip in self.ips if ip in self.monitors]
        for data in printers:
            item = self.monitors[data['ip']]
            data['read_only'] = not (item.light_control_enabled or item.fan_control_enabled or item.speed_control_enabled or item.temperature_control_enabled or item.print_control_enabled or item.motion_control_enabled)
            motion=item.motion_snapshot()
            wait=self.controls.motion_wait(data['ip']) if self.controls else 0
            data['motion_control']={'enabled':item.motion_control_enabled,'supported':item.motion_supported(),
                'available':bool(motion and motion['online'] and motion['light_age_s']<=15 and wait<=0),
                'context':motion['context'] if motion else None,
                'print_cycle':motion['print_cycle'] if motion else None,
                'age_s':motion['light_age_s'] if motion and math.isfinite(motion['light_age_s']) else None,
                'wait_s':math.ceil(wait)}
            printing=item.print_snapshot()
            data['print_control']={'enabled':item.print_control_enabled,'supported':item.print_supported(),
                'context':printing['context'] if printing else None,
                'phase':printing['light_on'] if printing else 0,
                'age_s':printing['light_age_s'] if printing and math.isfinite(printing['light_age_s']) else None,
                'filename':printing['filename'] if printing else None,
                'available':{key:bool(printing and printing['online'] and printing['light_age_s']<=15 and printing['light_on'] in entry[2]) for key,entry in PRINT_ACTIONS.items()}}
            temperature = item.temperature_snapshot('nozzle_target')
            data['temperature_control'] = {'enabled':item.temperature_control_enabled,'supported':item.temperature_supported(),
                'available':bool(temperature and temperature['online'] and temperature['light_age_s'] <= 15),
                'context':temperature['context'] if temperature else None}
            speed = item.speed_snapshot()
            data['speed_control'] = {'enabled':item.speed_control_enabled,'supported':item.speed_supported(),
                'available':bool(speed and speed['online'] and speed['light_age_s'] <= 15),
                'context':speed['context'] if speed else None}
            data['fan_control'] = {'enabled': item.fan_control_enabled, 'supported': item.fan_supported()}
            data['light_control'] = {'enabled': item.light_control_enabled,
                                     'supported': item.light_supported()}
        return {**(printers[0] if printers else {}), 'configured':bool(printers), 'printers':printers, 'ips':self.ips, 'read_only':self.read_only,'controls':{'chamber_light':bool(self.light_control_ips & set(self.ips)), 'fans':bool(self.fan_control_ips & set(self.ips)), 'speed_mode':bool(self.speed_control_ips & set(self.ips)), 'temperature':bool(self.temperature_control_ips & set(self.ips)), 'print_job':bool(self.print_control_ips & set(self.ips)), 'motion':bool(self.motion_control_ips & set(self.ips))},'history':self.history.jobs(), 'camera_available':self.cameras.available(),'camera_message':decoder_available.message(),'report_archive_error':self.history.report_error}

    async def reorder(self,ips):
        async with self.config_lock:
            if (not isinstance(ips,list) or len(ips)!=len(self.ips)
                    or any(not isinstance(ip,str) for ip in ips)
                    or set(ips)!=set(self.ips)):
                raise ValueError('Die Druckerliste hat sich geändert. Bitte aktualisieren und erneut sortieren.')
            save_config(self.data_dir,ips)
            self.ips=list(ips);self.ip=self.ips[0] if self.ips else None

    async def configure(self,ips):
        ips=printer_ips(ips)
        async with self.config_lock:
            save_config(self.data_dir,ips)
            for ip in list(self.monitors):
                if ip not in ips:
                    await self.monitors.pop(ip).stop(None)
            for ip in ips:
                if ip not in self.monitors:
                    private=self.runtime/ip;private.mkdir(mode=0o700,exist_ok=True)
                    item=Monitor(ip,private,str(self.data_dir/ip),self.history,ip in self.light_control_ips,ip in self.fan_control_ips, ip in self.speed_control_ips, ip in self.temperature_control_ips, ip in self.print_control_ips, ip in self.motion_control_ips)
                    self.monitors[ip]=item
                    await item.start(None)
            self.ips=ips;self.ip=ips[0]
            await self.cameras.prune(ips)

    async def start(self, app):
        for item in self.monitors.values():
            await item.start(app)

    async def stop(self, app):
        await asyncio.gather(*(item.stop(app) for item in self.monitors.values()))
        if self.controls:self.controls.close()
        self.history.close()


def build_app(monitor,access=None):
    allowed = {'/','/api/status','/api/report','/api/timeline','/api/jobs','/api/session','/about','/license','/notice','/assets/setup.js','/assets/setup.css','/health','/assets/monitor.css','/assets/monitor.js','/api/camera/frame','/assets/camera.js','/assets/notifications.js','/assets/diagnostics.js','/assets/spools.js','/service-worker.js','/manifest.webmanifest','/assets/app-icon.svg','/api/notifications','/api/diagnostics','/api/spools','/api/order-report','/api/report-export','/assets/orders.js','/assets/navigation.js','/assets/spool-workspace.js','/assets/controls.js','/assets/fan-controls.js','/assets/speed-controls.js','/assets/print-controls.js','/assets/motion-controls.js','/assets/temperature-controls.js','/favicon.ico'}
    @web.middleware
    async def boundary(request, handler):
        public={'/','/about','/license','/notice','/health','/assets/monitor.css','/assets/monitor.js','/assets/setup.css','/assets/setup.js','/assets/camera.js','/assets/notifications.js','/assets/diagnostics.js','/assets/spools.js','/service-worker.js','/manifest.webmanifest','/assets/app-icon.svg','/favicon.ico','/api/session','/assets/orders.js','/assets/navigation.js','/assets/spool-workspace.js','/assets/controls.js','/assets/fan-controls.js','/assets/speed-controls.js','/assets/print-controls.js','/assets/motion-controls.js','/assets/temperature-controls.js'}
        is_login=access is not None and request.method=='POST' and request.path=='/api/session'
        is_setup=access is not None and request.method=='POST' and request.path in ('/api/setup','/api/order','/api/camera/release','/api/notifications','/api/spools','/api/order-report','/api/controls')
        is_account=access is not None and request.method=='POST' and request.path in ('/api/account','/api/logout')
        integrated=gateway_path(request.path)
        valid_method=integrated or (request.method=='GET' and request.path in allowed) or is_login or is_setup or is_account
        if not valid_method:
            response = web.json_response({'error':'Nur Statusabfragen und lokale Einrichtung erlaubt.','read_only':True}, status=403)
        elif access is not None and request.path not in public and not access.session(request):
            response = web.json_response({'error':'Bitte anmelden.','read_only':True},status=401)
        elif access is not None and access.account is None and request.path not in public|{'/api/account','/api/logout'}:
            response = web.json_response({'error':'Bitte zuerst dein Benutzerkonto einrichten.','read_only':True},status=403)
        elif (is_setup or is_account) and not access.can_write(request):
            response = web.json_response({'error':'Einrichtung bitte aus dieser Oberfläche aufrufen.'},status=403)
        else:
            response = await handler(request)
        if response.content_type == 'application/json' and request.path in ('/api/session','/health','/api/status'):
            # Report the installation mode consistently, including login responses.
            try:
                body = json.loads(response.body)
                if isinstance(body, dict) and 'read_only' in body:
                    body['read_only'] = getattr(monitor, 'read_only', True)
                    response.body = json.dumps(body).encode()
            except (ValueError, TypeError, AttributeError):
                pass
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
            'Referrer-Policy':'no-referrer', 'Content-Security-Policy':
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'"})
        if integrated:
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'; object-src 'none'"
        return response
    app = web.Application(middlewares=[boundary], client_max_size=8192)
    async def index(request): return web.FileResponse(BASE/'static/index.html')
    async def about(request):return web.FileResponse(BASE/'static/about.html')
    async def license_text(request):return web.FileResponse(BASE/'LICENSE',headers={'Content-Type':'text/plain; charset=utf-8'})
    async def notice_text(request):return web.FileResponse(BASE/'NOTICE.md',headers={'Content-Type':'text/plain; charset=utf-8'})
    async def setup_js(request):return web.FileResponse(BASE/'static/setup.js')
    async def camera_js(request):return web.FileResponse(BASE/'static/camera.js')
    async def setup_css(request):return web.FileResponse(BASE/'static/setup.css')
    async def session(request):
        if access is None:return web.json_response({'authenticated':True,'csrf':'','read_only':True})
        if request.method=='POST':return await access.login(request)
        return web.json_response(access.state(request))
    async def control_action(request):
        if access is None or access.account is None or not access.can_write(request):
            return web.json_response({'error':'Anmeldung und Bestätigung erforderlich.'}, status=403)
        service = getattr(monitor, 'controls', None)
        if service is None or not service.enabled:
            return web.json_response({'error':'Die Druckersteuerung ist nicht freigegeben.'}, status=403)
        if request.content_type != 'application/json':
            return web.json_response({'error':'Ungültiges Datenformat.'}, status=400)
        try:
            body = await request.json()
            if not isinstance(body, dict):raise ValueError('Ungültiger Steuerauftrag.')
            action = body.get('action')
            fields = {'prepare': {'action','ip','desired','request_id'},
                      'prepare_fan': {'action','ip','fan','desired','request_id'},
                      'prepare_motion': {'action','ip','operation','desired','request_id','context','present'},
                      'prepare_print': {'action','ip','operation','request_id','context'},
                      'prepare_speed': {'action','ip','desired','request_id','context'},
                      'prepare_temperature': {'action','ip','heater','desired','request_id','context'},
                      'execute': {'action','id','token'}, 'cancel': {'action','id'},
                      'receipt': {'action','id'}}
            if not isinstance(action,str) or action not in fields or set(body) != fields[action]:
                raise ValueError('Ungültiger Steuerauftrag.')
            # Recheck after reading request body; an account change can revoke the session.
            if not access.can_write(request):
                return web.json_response({'error':'Bitte erneut anmelden.'}, status=401)
            actor = hashlib.sha256(access.session(request)['csrf'].encode()).hexdigest()
            if action in ('prepare','prepare_fan','prepare_speed','prepare_temperature','prepare_print','prepare_motion'):
                ip = body['ip']
                item = monitor.monitors.get(ip) if isinstance(ip,str) else None
                fan = body.get('fan') if action == 'prepare_fan' else None
                heater = body.get('heater') if action == 'prepare_temperature' else None
                operation=body.get('operation') if action=='prepare_print' else None
                if action=='prepare_motion':
                    operation=body['operation']
                    if (type(body['present']) is not bool or not isinstance(operation,str) or not valid_motion(operation,body['desired'])
                            or item is None or not item.motion_supported()):
                        raise ControlRefused('Bewegung nur mit bestätigter Anwesenheit am freigegebenen Drucker.')
                    if not isinstance(body['context'],str) or len(body['context'])!=64:raise ControlRefused('Aktueller Leerlauf fehlt.')
                    await item.refresh_motion()
                    current=item.motion_snapshot()
                    if not current or current['context']!=body['context']:raise ControlRefused('Druckerzustand geändert.')
                    if body['present'] is not True and (operation.startswith('home_') or not service.motion_confirmed(actor,ip,current.get('print_cycle'))):
                        raise ControlRefused('Bitte die Anwesenheit vor der ersten Fahrt nach einem Druck bestätigen.')
                elif action=='prepare_print':
                    if not isinstance(operation,str) or operation not in PRINT_ACTIONS or item is None or not item.print_supported():raise ControlRefused('Druckaktion nicht freigegeben.')
                    if not isinstance(body['context'],str) or len(body['context'])!=64:raise ControlRefused('Aktueller Druckauftrag fehlt.')
                    await item.refresh_print()
                    current=item.print_snapshot()
                    if not current or current['context']!=body['context']:raise ControlRefused('Druckauftrag gewechselt; bitte neu auswählen.')
                elif action == 'prepare_temperature':
                    if not isinstance(heater,str) or heater not in TEMP_LIMITS or item is None or not item.temperature_supported():
                        raise ControlRefused('Dieser Drucker oder Heizer ist nicht freigegeben.')
                    if not service._valid_value(heater,body['desired']):raise ControlRefused('Ungültige Solltemperatur.')
                    if not isinstance(body['context'],str) or len(body['context']) != 64:raise ControlRefused('Aktueller Druckerzustand fehlt.')
                    await item.refresh_temperature()
                    current = item.temperature_snapshot(heater)
                    if not current or current['context'] != body['context']:raise ControlRefused('Druckerzustand gewechselt; bitte neu auswählen.')
                elif action == 'prepare_speed':
                    if item is None or not item.speed_supported():
                        raise ControlRefused('Dieser Drucker ist nicht für Speed Mode freigegeben.')
                    if type(body['desired']) is not int or body['desired'] not in (1,2,3):
                        raise ControlRefused('Ungültiger Speed Mode.')
                    if not isinstance(body['context'],str) or len(body['context']) != 64:
                        raise ControlRefused('Aktueller Druckauftrag fehlt.')
                    await item.refresh_speed()
                    current = item.speed_snapshot()
                    if not current or current['context'] != body['context']:
                        raise ControlRefused('Druckauftrag gewechselt; bitte neu auswählen.')
                elif action == 'prepare_fan':
                    if not isinstance(fan,str) or fan not in FAN_FIELDS or item is None or not item.fan_supported():
                        raise ControlRefused('Dieser Drucker oder Lüfter ist nicht freigegeben.')
                    if type(body['desired']) is not int or not 0 <= body['desired'] <= 100:
                        raise ControlRefused('Lüfterstufe muss eine ganze Zahl zwischen 0 und 100 sein.')
                    await item.refresh_fan()
                else:
                    if item is None or not item.light_supported():
                        raise ControlRefused('Dieser Drucker ist nicht für Lichtsteuerung freigegeben.')
                    await item.refresh_light()
                if not access.can_write(request):
                    return web.json_response({'error':'Bitte erneut anmelden.'}, status=401)
                result = await service.prepare(actor,ip,PRINT_ACTIONS[operation][1] if action=='prepare_print' else body['desired'],body['request_id'],
                    **({'control':operation} if operation else {'control':heater} if heater else {'control':'speed_mode'} if action == 'prepare_speed' else {'control':fan} if fan else {}))
                if action=='prepare_motion' and body['present'] is True:
                    service.remember_motion_confirmation(actor,result['id'],current.get('print_cycle'))
            else:
                if not isinstance(body['id'],str) or len(body['id'])!=32:
                    raise ValueError('Ungültige Vorgangskennung.')
                if action == 'execute':result = await service.execute(actor,body['id'],body['token'])
                elif action == 'cancel':result = await service.cancel(actor,body['id'])
                else:result = await service.receipt(actor,body['id'])
            if action=='execute' and result.get('action','').startswith('axis_'):
                latest=monitor.monitors[result['ip']].motion_snapshot()
                result['motion_confirmed']=bool(latest and service.motion_confirmed(actor,result['ip'],latest.get('print_cycle')))
                result['print_cycle']=latest.get('print_cycle') if latest else None
            return web.json_response(result)
        except (ValueError, TypeError, AttributeError) as exc:
            return web.json_response({'error': str(exc) if isinstance(exc,ValueError) else 'Ungültiger Steuerauftrag.'},status=400)
        except (OSError, asyncio.TimeoutError):
            return web.json_response({'error':'Druckerrückmeldung nicht verfügbar; bitte Status prüfen.'},status=503)

    async def setup(request):
        if request.content_type!='application/json':return web.json_response({'error':'Ungültiges Datenformat.'},status=400)
        try:
            body=await request.json()
            ips=printer_ips(body.get('printer_ips'))
            await monitor.configure(ips)
        except (ValueError,TypeError,AttributeError) as exc:
            return web.json_response({'error':str(exc)},status=400)
        return web.json_response({'ok':True,'read_only':True,'ips':ips})

    async def order(request):
        if request.content_type!='application/json':
            return web.json_response({'error':'Ungültiges Datenformat.'},status=400)
        try:
            body=await request.json()
            await monitor.reorder(body.get('printer_ips'))
        except (ValueError,TypeError,AttributeError) as exc:
            return web.json_response({'error':str(exc) if isinstance(exc,ValueError) else 'Ungültige Druckerliste.'},status=400)
        return web.json_response({'ok':True,'read_only':True,'ips':monitor.ips})

    async def css(request): return web.FileResponse(BASE/'static/monitor.css')
    async def js(request): return web.FileResponse(BASE/'static/monitor.js')
    async def motion_controls_js(request): return web.FileResponse(BASE/'static/motion-controls.js')

    async def print_controls_js(request): return web.FileResponse(BASE/'static/print-controls.js')

    async def temperature_controls_js(request): return web.FileResponse(BASE/'static/temperature-controls.js')

    async def speed_controls_js(request): return web.FileResponse(BASE/'static/speed-controls.js')
    async def fan_controls_js(request): return web.FileResponse(BASE/'static/fan-controls.js')
    async def controls_js(request): return web.FileResponse(BASE/'static/controls.js')
    async def status(request):
        data=monitor.telemetry.snapshot()
        service=getattr(monitor,'controls',None)
        if service and access.session(request):
            actor=hashlib.sha256(access.session(request)['csrf'].encode()).hexdigest()
            for printer in data.get('printers',[]):
                motion=printer.get('motion_control')
                if motion:motion['confirmed']=service.motion_confirmed(actor,printer['ip'],motion.get('print_cycle'))
        return web.json_response(data)
    async def report(request):
        job_id=request.query.get('job','')
        if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):
            return web.json_response({'error':'Ungültiger Auftrag.'},status=400)
        history=getattr(monitor,'history',None)
        text=await asyncio.to_thread(history.report,job_id) if history else None
        if text is None:return web.json_response({'error':'Auftrag nicht gefunden.'},status=404)
        return web.Response(text=text,content_type='text/markdown',charset='utf-8',headers={
            'Content-Disposition':f'attachment; filename="Kobra-Druckbericht-{job_id[:8]}.md"'})
    async def order_report(request):
        history=getattr(monitor,'history',None)
        if history is None:return web.json_response({'error':'Historie nicht verfügbar.'},status=503)
        try:
            if request.method=='GET':
                return web.json_response(await asyncio.to_thread(history.reports.detail,request.query.get('job','')))
            if request.content_type!='application/json':raise ValueError('JSON erforderlich.')
            body=await request.json()
            job=body.get('job','')
            action=body.get('action')
            if action=='save':
                result=await asyncio.to_thread(history.reports.save,job,body.get('annotation',{}))
            elif action=='archive':
                await asyncio.to_thread(history.reports.freeze,job,'Manuell nachträglich archiviert')
                result=await asyncio.to_thread(history.reports.detail,job)
            elif action=='backfill':
                result={'archived':await asyncio.to_thread(history.reports.bootstrap),'read_only':True}
            elif action=='bundle':
                data=await asyncio.to_thread(history.reports.bundle,body.get('jobs'))
                return web.Response(body=data,content_type='application/zip',headers={'Content-Disposition':'attachment; filename="Kobra-Auftragsberichte.zip"'})
            else:raise ValueError('Unbekannte Aktion.')
            return web.json_response(result)
        except RuntimeError as exc:return web.json_response({'error':str(exc)},status=409)
        except (ValueError,TypeError,AttributeError) as exc:return web.json_response({'error':str(exc)},status=400)
        except Exception:return web.json_response({'error':'Bericht konnte nicht gespeichert werden. Bisherige Archivversionen bleiben erhalten.'},status=503)

    async def report_export(request):
        try:
            version=request.query.get('version','')
            if not version.isascii() or not version.isdigit() or len(version)>8:raise ValueError('Ungültige Version.')
            history=getattr(monitor,'history',None)
            if history is None:return web.json_response({'error':'Historie nicht verfügbar.'},status=503)
            data,mime,name=await asyncio.to_thread(history.reports.export,request.query.get('job',''),int(version),request.query.get('format','pdf'))
            return web.Response(body=data,content_type=mime,headers={'Content-Disposition':f'attachment; filename="{name}"'})
        except (ValueError,TypeError):return web.json_response({'error':'Archivversion oder Format nicht gefunden.'},status=404)

    async def orders_js(request):return web.FileResponse(BASE/'static/orders.js')
    async def navigation_js(request):return web.FileResponse(BASE/'static/navigation.js')
    async def health(request):
        result={'ok':True,'service':'kobra-monitor','read_only':True,'ip':monitor.ip,'ips':getattr(monitor,'ips',[monitor.ip])}
        cameras=getattr(monitor,'cameras',None)
        if cameras is not None and hasattr(cameras,'available'):result['camera_available']=cameras.available()
        return web.json_response(result)
    async def timeline(request):
        job_id=request.query.get('job','')
        if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):
            return web.json_response({'error':'Ungültiger Auftrag.'},status=400)
        history=getattr(monitor,'history',None)
        result=await asyncio.to_thread(history.timeline,job_id) if history else None
        if result is None:return web.json_response({'error':'Auftrag nicht gefunden.'},status=404)
        return web.json_response(result)
    async def camera_frame(request):
        viewer=request.query.get('viewer','legacy')
        if viewer!='legacy' and (len(viewer)!=32 or any(c not in '0123456789abcdef' for c in viewer)):
            return web.json_response({'error':'Ungültige Kameraansicht.'},status=400)
        if viewer=='legacy':return await monitor.cameras.frame(request.query.get('ip',''),monitor.ips)
        return await monitor.cameras.frame(request.query.get('ip',''),monitor.ips,viewer)
    async def camera_release(request):
        try:body=await request.json()
        except (ValueError,TypeError):body={}
        viewer=body.get('viewer','') if isinstance(body,dict) else ''
        if not isinstance(viewer,str) or len(viewer)!=32 or any(c not in '0123456789abcdef' for c in viewer):
            return web.json_response({'error':'Ungültige Kameraansicht.'},status=400)
        await monitor.cameras.release(viewer)
        return web.json_response({'released':True,'read_only':True})
    async def notification_assets(request):
        file={'/assets/spools.js':'spools.js','/assets/diagnostics.js':'diagnostics.js','/assets/notifications.js':'notifications.js','/service-worker.js':'service-worker.js','/manifest.webmanifest':'manifest.webmanifest','/assets/app-icon.svg':'app-icon.svg'}[request.path]
        response=web.FileResponse(BASE/'static'/file)
        if file=='service-worker.js':response.headers['Service-Worker-Allowed']='/'
        return response
    async def diagnostics(request):
        return web.json_response(await asyncio.to_thread(diagnostic_summary,monitor))

    async def spools(request):
        service=getattr(monitor,'spools',None)
        if service is None:return web.json_response({'error':'Spulenverwaltung hier nicht verfügbar.'},status=503)
        def snapshots():
            return [p.telemetry.snapshot() for ip,p in getattr(monitor,'monitors',{}).items()
                    if ip in getattr(monitor,'ips',[])]
        def with_detections(result):
            return {**result, 'detections': service.detections(snapshots())}
        try:
            if request.method=='GET':return web.json_response(with_detections(service.state()))
            if request.content_type!='application/json':raise ValueError('Ungültiges Datenformat.')
            body=await request.json()
            if body.get('action')=='configure':result=await service.configure(body.get('url'))
            elif body.get('action')=='refresh':result=await service.refresh()
            elif body.get('action')=='link_sku':
                if body.get('spool_id') is not None and body.get('unique_confirmed') is not True:
                    raise ValueError('Bitte bestätigen, dass diese Kennung nur zu dieser Spule gehört.')
                if body.get('spool_id') is not None and (not isinstance(body.get('ip'),str) or type(body.get('slot')) is not int):
                    raise ValueError('Bitte den gemeldeten Steckplatz auswählen.')
                result=await service.link_sku(body.get('sku'),body.get('spool_id'),snapshots(),(body.get('ip'),body.get('slot')))
            elif body.get('action')=='assign':
                ip=body.get('ip')
                printer=monitor.monitors.get(ip) if isinstance(ip,str) else None
                snapshot=printer.telemetry.snapshot() if printer else {}
                slots=(snapshot.get('data') or {}).get('ace_slots') or []
                reported={slot.get('global_index',slot.get('index')) for slot in slots if isinstance(slot,dict)}
                # Removing an old mapping remains possible after a slot/printer disappears.
                if body.get('spool_id') is None and ip in service.mappings:
                    reported.update(int(slot) for slot in service.mappings[ip])
                ips=list(getattr(monitor,'ips',[]))
                if body.get('spool_id') is None and ip in service.mappings:ips.append(ip)
                result=await service.assign(ip,body.get('slot'),body.get('spool_id'),ips,reported)
            else:raise ValueError('Unbekannte Aktion.')
            return web.json_response(with_detections(result))
        except ValueError as exc:
            return web.json_response({'error':str(exc)[:350] or 'Bitte die Angaben prüfen.'},status=400)
        except (TypeError,AttributeError):
            return web.json_response({'error':'Bitte die Angaben prüfen.'},status=400)

    async def notifications(request):
        service=getattr(monitor,'notifications',None)
        if service is None:return web.json_response({'error':'Benachrichtigungen sind hier nicht verfügbar.'},status=503)
        try:
            if request.method=='GET':return web.json_response({**service.state(),'public_key':service.public_key()})
            if request.content_type!='application/json':raise ValueError('Ungültiges Datenformat.')
            body=await request.json()
            action=body.get('action')
            if action=='subscribe':
                device_id=service.subscribe(body.get('subscription'),body.get('label'),body.get('preferences'),request.headers.get('Origin',''))
                return web.json_response({'ok':True,'id':device_id,'read_only':True})
            device_id=body.get('id')
            if not isinstance(device_id,str) or len(device_id)!=32 or any(c not in '0123456789abcdef' for c in device_id):raise ValueError('Ungültiges Gerät.')
            if action=='remove':service.remove(device_id)
            elif action=='test':service.test(device_id)
            else:raise ValueError('Unbekannte Aktion.')
            return web.json_response({'ok':True,'read_only':True})
        except (ValueError,TypeError,AttributeError):
            return web.json_response({'error':'Die Angaben sind ungültig oder das Gerät ist nicht verfügbar. Bitte prüfen und gegebenenfalls eine Minute warten.'},status=400)

    async def favicon(request): return web.Response(status=204)
    async def jobs(request):
        ip=request.query.get('ip','')
        if ip not in getattr(monitor,'ips',[]):
            return web.json_response({'error':'Drucker nicht konfiguriert.'},status=400)
        try:
            page_text=request.query.get('page','0')
            if len(page_text)>7 or not page_text.isascii() or not page_text.isdigit():raise ValueError()
            query={'search':request.query.get('search',''),'state':request.query.get('state','all'),'page':int(page_text)}
            history=getattr(monitor,'history',None)
            if history is None:return web.json_response({'error':'Historie nicht verfügbar.'},status=503)
            result=await asyncio.to_thread(history.archive,ip,**query)
        except ValueError:
            return web.json_response({'error':'Ungültiger Suchfilter.'},status=400)
        return web.json_response(result)
    async def integrated_spoolman(request):
        return await gateway(request,getattr(monitor,'spools',None),access)
    async def spool_workspace_js(request):return web.FileResponse(BASE/'static/spool-workspace.js')
    async def blocked(request): return web.json_response({'error':'Nur Statusabfragen erlaubt.'},status=403)
    app.router.add_get('/about',about)
    app.router.add_get('/license',license_text)
    app.router.add_get('/notice',notice_text)
    app.router.add_get('/', index)
    app.router.add_get('/assets/setup.js',setup_js)
    app.router.add_get('/assets/setup.css',setup_css)
    app.router.add_get('/assets/camera.js',camera_js)
    app.router.add_get('/api/session',session)
    app.router.add_post('/api/session',session)
    if access is not None:
        app.router.add_post('/api/account',access.save_account)
        app.router.add_post('/api/logout',access.logout)
    app.router.add_post('/api/setup',setup)
    app.router.add_post('/api/order',order)
    app.router.add_get('/assets/monitor.css',css)
    app.router.add_get('/assets/monitor.js',js)
    app.router.add_get('/assets/controls.js',controls_js)
    app.router.add_get('/assets/fan-controls.js',fan_controls_js)
    app.router.add_get('/assets/temperature-controls.js',temperature_controls_js)
    app.router.add_get('/assets/motion-controls.js',motion_controls_js)
    app.router.add_get('/assets/print-controls.js',print_controls_js)
    app.router.add_get('/assets/speed-controls.js',speed_controls_js)
    app.router.add_post('/api/controls',control_action)
    app.router.add_get('/api/status',status)
    app.router.add_get('/api/report',report)
    app.router.add_get('/api/order-report',order_report)
    app.router.add_post('/api/order-report',order_report)
    app.router.add_get('/api/report-export',report_export)
    app.router.add_get('/assets/orders.js',orders_js)
    app.router.add_get('/assets/navigation.js',navigation_js)
    app.router.add_get('/api/timeline',timeline)
    app.router.add_get('/api/jobs',jobs)
    app.router.add_get('/health',health)
    app.router.add_get('/api/camera/frame',camera_frame)
    if access is not None:app.router.add_post('/api/camera/release',camera_release)
    for path in ('/assets/notifications.js','/assets/diagnostics.js','/assets/spools.js','/service-worker.js','/manifest.webmanifest','/assets/app-icon.svg'):
        app.router.add_get(path,notification_assets)
    app.router.add_get('/api/notifications',notifications)
    app.router.add_get('/api/diagnostics',diagnostics)
    app.router.add_get('/api/spools',spools)
    if access is not None:app.router.add_post('/api/spools',spools)
    if access is not None:app.router.add_post('/api/notifications',notifications)
    app.router.add_get('/favicon.ico',favicon)
    app.router.add_get('/assets/spool-workspace.js',spool_workspace_js)
    app.router.add_route('*','/spoolman',integrated_spoolman)
    app.router.add_route('*','/spoolman/{path:.*}',integrated_spoolman)
    app.router.add_route('*','/{path:.*}',blocked)
    if getattr(monitor,'cameras',None) is not None:
        app.on_startup.append(monitor.cameras.start)
        app.on_cleanup.append(monitor.cameras.stop)
    if getattr(monitor,'notifications',None) is not None:
        app.on_startup.append(monitor.notifications.start)
        app.on_cleanup.append(monitor.notifications.stop)
    app.on_startup.append(monitor.start)
    app.on_cleanup.append(monitor.stop)
    return app


async def serve(args):
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix='kobra-monitor-') as runtime:
        data_dir = Path(args.data_dir)
        data_dir.mkdir(exist_ok=True, mode=0o700)
        monitor = Fleet(args.ips, runtime, str(data_dir),
            light_control_ips=printer_ips(os.environ['KOBRA_LIGHT_CONTROL_IPS'].split(','))
            if os.environ.get('KOBRA_LIGHT_CONTROL_IPS','').strip() else None,
            fan_control_ips=printer_ips(os.environ['KOBRA_FAN_CONTROL_IPS'].split(','))
            if os.environ.get('KOBRA_FAN_CONTROL_IPS','').strip() else None,
            speed_control_ips=printer_ips(os.environ['KOBRA_SPEED_CONTROL_IPS'].split(','))
            if os.environ.get('KOBRA_SPEED_CONTROL_IPS','').strip() else None,
            temperature_control_ips=printer_ips(os.environ['KOBRA_TEMPERATURE_CONTROL_IPS'].split(','))
            if os.environ.get('KOBRA_TEMPERATURE_CONTROL_IPS','').strip() else None,
            motion_control_ips=printer_ips(os.environ['KOBRA_MOTION_CONTROL_IPS'].split(','))
                if os.environ.get('KOBRA_MOTION_CONTROL_IPS','').strip() else None,
            print_control_ips=printer_ips(os.environ['KOBRA_PRINT_CONTROL_IPS'].split(','))
            if os.environ.get('KOBRA_PRINT_CONTROL_IPS','').strip() else None)
        access=Access(data_dir)
        runner = web.AppRunner(build_app(monitor,access), access_log=None)
        try:
            await runner.setup()
            await web.TCPSite(runner,args.listen,args.port).start()
            print(f'Kobra Monitor: http://127.0.0.1:{args.port}',flush=True)
            print('Begrenzte Druckersteuerung freigegeben. Anmeldung im Browser.' if not monitor.read_only else
                  'Nur lesen. Anmeldung und Einrichtung im Browser.',flush=True)
            if not access.account:print('Erste Einrichtung: python monitor.py --show-setup-link',flush=True)
            if args.open:
                import webbrowser
                webbrowser.open(f'http://127.0.0.1:{args.port}/'+('' if Access(args.data_dir).account else '#access='+quote(Access(args.data_dir).token,safe='')))
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:loop.add_signal_handler(sig,stop.set)
                except NotImplementedError:
                    signal.signal(sig,lambda *_:loop.call_soon_threadsafe(stop.set))
            await stop.wait()
        finally:
            await runner.cleanup()


def main():
    parser=argparse.ArgumentParser(description='Lokaler Kobra-Statusmonitor – ausschließlich lesend')
    parser.add_argument('--ip',action='append',help='Lokale Drucker-IP; für mehrere Drucker wiederholen')
    parser.add_argument('--port',type=int,default=7125,help='Lokaler Port der Statusübersicht')
    parser.add_argument('--open',action='store_true',help='Statusübersicht im Browser öffnen')
    parser.add_argument('--listen',default=os.environ.get('KOBRA_LISTEN','127.0.0.1'),help='Lokale Bindeadresse; Standard nur dieser Rechner')
    parser.add_argument('--data-dir',default=os.environ.get('KOBRA_DATA_DIR',str(BASE/'.state')),help='Dauerhafter Datenordner')
    parser.add_argument('--show-setup-link',action='store_true',help='Geschützten Link für die einmalige Kontoeinrichtung anzeigen')
    parser.add_argument('--show-access-code',action='store_true',help='Lokalen Zugangscode anzeigen und beenden')
    args=parser.parse_args()
    try:ipaddress.ip_address(args.listen)
    except ValueError:parser.error('Ungültige Bindeadresse.')
    if args.show_access_code or args.show_setup_link:
        access=Access(args.data_dir)
        if access.account:
            print('Ein Benutzerkonto ist eingerichtet. Bitte mit Benutzername und Passwort anmelden.')
            return
        print(f'http://127.0.0.1:{args.port}/#access='+quote(access.token,safe='') if args.show_setup_link else access.token)
        return
    try:
        configured=args.ip or ([v.strip() for v in os.environ['KOBRA_PRINTER_IPS'].split(',')] if os.environ.get('KOBRA_PRINTER_IPS') else load_config(args.data_dir))
        args.ips=printer_ips(configured) if configured else []
    except ValueError as exc:parser.error(str(exc))
    if not 1024<=args.port<=65535: parser.error('Port muss zwischen 1024 und 65535 liegen.')
    if args.open:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/health',timeout=0.7) as response:
                running=json.loads(response.read())
            if running.get('service')=='kobra-monitor' and set(running.get('ips',[running.get('ip')]))==set(args.ips) and type(running.get('read_only')) is bool:
                import webbrowser
                webbrowser.open(f'http://127.0.0.1:{args.port}/'+('' if Access(args.data_dir).account else '#access='+quote(Access(args.data_dir).token,safe='')))
                print('Der Kobra Monitor läuft bereits. Statusübersicht geöffnet.',flush=True)
                return
        except (OSError,ValueError):
            pass
    try:
        asyncio.run(serve(args))
    except OSError as exc:
        if exc.errno in (48,98):
            print(f'Port {args.port} ist bereits belegt. Beende den anderen Dienst oder wähle --port 7126.',file=sys.stderr)
            raise SystemExit(1) from None
        raise


if __name__=='__main__': main()
