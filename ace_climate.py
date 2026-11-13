# SPDX-License-Identifier: GPL-3.0-only
"""Observed ACE climate only; absent fields never become synthetic zero/off."""
import math
import time
import uuid

FIELDS={'current_temp':('current_temp','cur_temp','temperature','temp','drying_temp','chamber_temp'),
        'humidity':('humidity','current_humidity','cur_humidity','relative_humidity','humidity_value'),
        'status':('status',),'target_temp':('target_temp',),'duration':('duration',),'remain_time':('remain_time',)}


def number(value, maximum=100):
    if isinstance(value,bool):return None
    try:value=float(value)
    except (ValueError,TypeError,OverflowError):return None
    return value if math.isfinite(value) and 0<=value<=maximum else None


class AceClimate:
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.units={};self.generation=uuid.uuid4().hex

    def receive(self,data,connection):
        boxes=data.get('multi_color_box')
        if not isinstance(boxes,list):return
        valid=[b for b in boxes if isinstance(b,dict) and type(b.get('id')) is int and 0<=b['id']<=3]
        ids=[b['id'] for b in valid]
        if len(set(ids))!=len(ids):
            self.units={};self.generation=uuid.uuid4().hex;return
        if set(ids)!=set(self.units):self.generation=uuid.uuid4().hex
        self.units={i:self.units[i] for i in ids if i in self.units}
        for box in valid:
            item=self.units.setdefault(box['id'],{'values':{},'seen':{},'connections':{},'revision':0,'configuration':uuid.uuid4().hex})
            nested=box.get('drying_status',box.get('drying_settings'))
            # A top-level status is attributable only when exactly one ACE is present.
            if not isinstance(nested,dict) and len(valid)==1:nested=data.get('drying_status',data.get('drying_settings'))
            nested=nested if isinstance(nested,dict) else {}
            for field,aliases in FIELDS.items():
                sources=[nested,box] if field in ('current_temp','humidity') else [nested]
                present=[s[k] for s in sources for k in aliases if k in s]
                if not present:continue
                v=number(present[0],1440 if field in ('duration','remain_time') else 100)
                if field=='status' and v not in (0,1):v=None
                if field in ('status','target_temp','duration','remain_time') and v is not None:
                    if int(v)!=v:v=None
                    else:v=int(v)
                if field in ('status','target_temp','duration') and (item['values'].get(field)!=v or item['connections'].get(field)!=connection):item['configuration']=uuid.uuid4().hex
                item['values'][field]=v;item['seen'][field]=self.clock();item['connections'][field]=connection
                if field=='status':item['revision']+=1

    def public(self,connection,online):
        return [dict(id=i,**u['values'],ages={k:max(0,self.clock()-s) for k,s in u['seen'].items()},
                     current={k:bool(online and connection and c==connection) for k,c in u['connections'].items()},
                     revision=u['revision'],configuration=u['configuration']) for i,u in sorted(self.units.items())]


def drying_options(on,temperature=None,duration=None,*,maximum=55):
    if type(maximum) is not int or maximum not in (55,65):raise ValueError('Ungültige ACE-Temperaturgrenze.')
    if type(on) is not bool:raise ValueError('Trocknungszustand muss An oder Aus sein.')
    if not on:
        if temperature is not None or duration is not None:raise ValueError('Ausschalten benötigt keine Heizparameter.')
        return {'status':0}
    # Configured device limit: no inferred ACE-generation capability or automatic preset.
    if type(temperature) is not int or not 30<=temperature<=maximum:raise ValueError('Temperatur außerhalb der ACE-Grenze.')
    if type(duration) is not int or not 10<=duration<=1440:raise ValueError('Dauer: 10 bis 1440 Minuten.')
    return {'status':1,'target_temp':temperature,'duration':duration,'remain_time':duration}
