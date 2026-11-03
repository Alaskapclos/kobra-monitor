# SPDX-License-Identifier: GPL-3.0-only
"""Restricted manual moves; a sent command is never proof of physical completion."""
import hashlib
import json
import time
import uuid

MOTION_ACTIONS = {'axis_x':1, 'axis_y':2, 'axis_z':3, 'home_xy':4, 'home_z':3}
STEPS = (1,15,50)

def valid_motion(action, value):
    return (type(value) is int and action in MOTION_ACTIONS and
            (value == 1 if action.startswith('home_') else abs(value) in STEPS))

def motion_payload(action, value):
    if not valid_motion(action,value):raise ValueError('Invalid manual movement')
    return {'axis':MOTION_ACTIONS[action],
            'move_type':2 if action.startswith('home_') else 1 if value > 0 else 0,
            'distance':0 if action.startswith('home_') else abs(value)}

class MotionState:
    def __init__(self, clock=time.monotonic):
        self.clock=clock;self.seen=float('-inf');self.revision=0
        self.connection=None;self.token=uuid.uuid4().hex;self.idle=False
    def receive(self,kind,payload,connection):
        if kind not in ('info','print','axis'):return
        raw=payload.get('data')
        if kind=='axis' and payload.get('state') in ('done',None):return
        idle=(kind=='info' and isinstance(raw,dict) and raw.get('state')=='free'
              and raw.get('project') is None and payload.get('code') in (None,200))
        if not idle or not self.idle or connection!=self.connection:self.token=uuid.uuid4().hex
        self.idle=idle;self.connection=connection;self.seen=self.clock() if idle else float('-inf')
        self.revision+=1
    def snapshot(self,epoch,connected):
        context=hashlib.sha256(json.dumps([self.token,self.connection]).encode()).hexdigest()
        return {'online':bool(connected and self.idle and epoch and epoch==self.connection),
                'connection_id':epoch,'context':context,'light_on':0,
                'light_revision':self.revision,'light_age_s':max(0,self.clock()-self.seen)}
