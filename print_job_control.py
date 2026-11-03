# SPDX-License-Identifier: GPL-3.0-only
"""Received job identity for optional pause/resume/stop; never issues commands."""
import math
import re
import uuid

PRINT_ACTIONS = {'print_pause':('pause',2,(1,)),
                 'print_resume':('resume',1,(2,)),
                 'print_stop':('stop',3,(1,2))}
PHASES = {'printing':1, 'paused':2, 'pause':2, 'canceled':3, 'cancelled':3,
          'stoped':3, 'stopped':3, 'finished':4}

class PrintJobState:
    def __init__(self,clock):
        self.clock=clock
        self.token=uuid.uuid4().hex
        self.task=None;self.filename=None;self.connection=None;self.elapsed=None
        self.phase=0;self.seen=float('-inf');self.revision=0;self.history_id=None

    def receive(self,kind,payload,connection):
        if kind not in ('info','print'):return
        raw=payload['data']
        project=raw.get('project') if kind=='info' else raw
        if kind=='info' and not isinstance(project,dict):
            # Free is not proof of an explicitly cancelled job.
            if self.phase:
                self.token=uuid.uuid4().hex;self.history_id=None
            self.phase=0;self.seen=float('-inf');return
        if not isinstance(project,dict):return
        phase=project.get('state') if kind=='info' else payload.get('state')
        if kind=='info' and project.get('pause')==1:phase='paused'
        if phase in (None,'done') and kind=='print':return # command ack is not state
        task=project.get('task_id') if kind=='info' else project.get('taskid')
        task=str(task) if type(task) in (str,int) and re.fullmatch(r'-1|[1-9][0-9]{0,19}',str(task)) else None
        filename=project.get('filename')
        filename=filename if isinstance(filename,str) and 0<len(filename)<=1024 else None
        elapsed=project.get('print_time')
        elapsed=elapsed if type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>=0 else None
        changed=(connection!=self.connection or (task is not None and task!=self.task)
                 or (filename is not None and filename!=self.filename)
                 or (elapsed is not None and self.elapsed is not None and elapsed<self.elapsed)
                 or (self.phase in (3,4) and PHASES.get(phase) in (1,2)))
        if changed:
            self.token=uuid.uuid4().hex;self.history_id=None;self.seen=float('-inf')
        # Missing fields and intermediate states immediately disarm old actions.
        # Only a full status, never an acknowledgement/default, refreshes authority.
        next_phase=PHASES.get(phase,0)
        if not next_phase and self.phase:
            self.token=uuid.uuid4().hex;self.history_id=None
        self.phase=next_phase;self.seen=float('-inf')
        if task is None or filename is None or not self.phase:return
        self.task=task;self.filename=filename;self.connection=connection
        self.elapsed=elapsed if elapsed is not None else self.elapsed
        self.seen=self.clock();self.revision+=1

    def signature(self):return (self.token,self.task,self.filename,self.connection,self.history_id)
