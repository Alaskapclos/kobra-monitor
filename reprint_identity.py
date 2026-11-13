# SPDX-License-Identifier: GPL-3.0-only
"""Only confirmed 0.36 archive starts: S1 info clamps their oversized task IDs.

Do not combine arbitrary task IDs or match a job solely by its filename.
"""
import copy
import json
from reprint_transfer import remote_name

INT32_MAX=2147483647


def legacy_dispatch(db,ip,filename,task):
    if not isinstance(filename,str) or type(task) not in (str,int):return None
    task=str(task)
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='archive_dispatches'").fetchone():return None
    for row in db.execute("SELECT id,sha256,receipt,metadata FROM archive_dispatches WHERE ip=? AND state='confirmed' ORDER BY created DESC LIMIT 50",(ip,)).fetchall():
        try:
            receipt=json.loads(row['receipt']);original=receipt.get('task_id')
            if type(original) not in (str,int) or not str(original).isdigit():continue
            if not INT32_MAX<int(original)<2**63 or task not in (str(original),str(INT32_MAX)):continue
            if filename!=remote_name(row['id']):continue
            source=json.loads(row['metadata'])['source_job']
            if not isinstance(source,str):continue
            return {'task':str(original),'sha256':row['sha256'],'source_job':source}
        except (ValueError,TypeError,KeyError,AttributeError):continue
    return None


def normalize(history,ip,kind,payload):
    if kind not in ('info','print') or not isinstance(payload,dict) or payload.get('code') not in (None,200):return payload
    data=payload.get('data')
    if not isinstance(data,dict):return payload
    projects=[data.get('project'),data.get('last_project')] if kind=='info' else [data]
    result=payload
    with history.lock:
        for index,project in enumerate(projects):
            if not isinstance(project,dict):continue
            key='task_id' if kind=='info' else 'taskid';task=project.get(key)
            if str(task)!=str(INT32_MAX):continue
            filename=project.get('filename')
            if filename is None and kind=='print':
                current=history.db.execute('SELECT filename FROM jobs WHERE ip=? AND ended_at IS NULL ORDER BY first_seen DESC LIMIT 1',(ip,)).fetchone()
                filename=current['filename'] if current else None
            known=legacy_dispatch(history.db,ip,filename,task)
            if known:
                if result is payload:result=copy.deepcopy(payload)
                target=result['data'].get(('project','last_project')[index]) if kind=='info' else result['data']
                target[key]=known['task']
    return result
