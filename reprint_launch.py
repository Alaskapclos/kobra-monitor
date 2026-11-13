# SPDX-License-Identifier: GPL-3.0-only
"""Restricted stock-S1/direct-ACE launch packet; no network operations here.

This is an experimental protocol contract until physically accepted on a stock
S1. Root-file start with an uploaded .gcode.3mf is NOT validated by unit tests.
"""
import re
from reprint_transfer import remote_name


def rgba(value):
    if not isinstance(value,list) or len(value) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in value):
        raise ValueError('Aktuelle ACE-Farbe fehlt.')
    return value + [255]


def material_family(value):
    normalized = value.upper().strip() if isinstance(value,str) else ''
    return 'PLA' if normalized in ('PLA','PLA+') else normalized


def mapping_for(materials, assignments, slots):
    """Explicit choices only. Preserve T indices and fill gaps with a used tray.

    Initial transport scope is ONE direct four-slot ACE (box 0) on model 20025.
    Never guess topology or reuse a previous job's .acm mapping.
    """
    if not isinstance(materials,list) or not 1 <= len(materials) <= 16 or not isinstance(assignments,list):
        raise ValueError('Filamentauswahl fehlt.')
    choices = {}
    for item in assignments:
        if (not isinstance(item,dict) or set(item) != {'paint_index','slot'} or
                type(item['paint_index']) is not int or type(item['slot']) is not int or
                item['paint_index'] in choices or not 0 <= item['slot'] <= 3):
            raise ValueError('Ungültige oder doppelte Filamentauswahl.')
        choices[item['paint_index']] = item['slot']
    if set(choices) != {m['paint_index'] for m in materials}:
        raise ValueError('Jedes tatsächlich verwendete Filament muss ausdrücklich zugeordnet werden.')
    if not isinstance(slots,list) or not 1 <= len(slots) <= 4:raise ValueError('Aktuelle ACE-Slots fehlen.')
    available = {}
    for slot in slots:
        if not isinstance(slot,dict): raise ValueError('Ungültige ACE-Meldung.')
        index=slot.get('global_index')
        if (type(index) is not int or not 0 <= index <= 3 or
                type(slot.get('box_id')) is not int or slot['box_id'] != 0 or
                type(slot.get('index')) is not int or slot['index'] != index or index in available):
            raise ValueError('Vorerst wird ein direkt angeschlossener ACE mit vier Slots unterstützt.')
        available[index]=slot
    result={}
    for material in materials:
        i=material['paint_index'];slot=available.get(choices[i])
        if not slot or type(slot.get('status')) is not int or slot['status'] != 5 or slot.get('edit_status')==2 or not slot.get('type'):
            raise ValueError('Ein ausgewählter ACE-Slot ist nicht eindeutig belegt.')
        if material_family(material['type']) != material_family(slot['type']):
            raise ValueError('Materialfamilie von Datei und ausgewähltem ACE-Slot stimmt nicht überein.')
        color=material['color']
        if not isinstance(color,str) or not re.fullmatch('#[a-fA-F0-9]{6}',color):raise ValueError('Slicer-Farbe fehlt.')
        if not isinstance(slot['type'],str) or not re.fullmatch(r'[A-Za-z0-9 +_.-]{1,40}',slot['type']):raise ValueError('ACE-Materialtyp nicht unterstützt.')
        result[i]={'paint_index':i,'ams_index':choices[i],
                   'paint_color':[int(color[n:n+2],16) for n in (1,3,5)]+[255],
                   'ams_color':rgba(slot.get('color')),'material_type':slot['type']}
    # Firmware treats the mapping as an indexed list. Gap entries point at an
    # explicitly selected occupied tray, never at an empty/unselected slot.
    fallback=result[min(result)]
    return [result.get(i,dict(fallback,paint_index=i)) for i in range(max(result)+1)]


def start_payload(operation, md5, size, mapping):
    name=remote_name(operation)
    if (not isinstance(md5,str) or not re.fullmatch('[a-f0-9]{32}',md5) or
            type(size) is not int or not 0 < size <= 256 * 1024**2 or
            not isinstance(mapping,list) or not 1 <= len(mapping) <= 16):
        raise ValueError('Geprüfter Übertragungsbeleg fehlt.')
    clean=[]
    for i,item in enumerate(mapping):
        if (not isinstance(item,dict) or set(item) != {'paint_index','ams_index','paint_color','ams_color','material_type'} or
                type(item['paint_index']) is not int or item['paint_index'] != i or
                type(item['ams_index']) is not int or not 0 <= item['ams_index'] <= 3 or
                not isinstance(item['material_type'],str) or not re.fullmatch(r'[A-Za-z0-9 +_.-]{1,40}',item['material_type'])):
            raise ValueError('Ungültige ACE-Startzuordnung.')
        for key in ('paint_color','ams_color'):
            if (not isinstance(item[key],list) or len(item[key]) != 4 or item[key][-1] != 255 or
                    any(type(c) is not int or not 0 <= c <= 255 for c in item[key])):
                raise ValueError('Ungültige ACE-Startfarbe.')
        clean.append({key:list(value) if isinstance(value,list) else value for key,value in item.items()})
    return {'filename':name,'filepath':'/','filetype':1,'task_mode':1,
            'taskid':str(1+int(operation[:15],16)%2147483646),'md5':md5,'filesize':size,
            'ams_settings':{'use_ams':True,'ams_box_mapping':clean},
            'task_settings':{'auto_leveling':1,'vibration_compensation':0,'flow_calibration':0}}
