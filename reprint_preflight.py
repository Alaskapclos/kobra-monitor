# SPDX-License-Identifier: GPL-3.0-only
"""Read-only repeat-print preparation. Never authorizes a printer command.

Slicer metadata is descriptive, not proof that arbitrary G-code is safe. A
successful inspection is deliberately NOT a start permission or a safety scan.
"""
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile

MAX_METADATA = 1024 * 1024
MAX_GCODE = 32 * 1024 * 1024
MAX_LINE = 64 * 1024
MODEL = 'Anycubic Kobra S1'


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('Doppelte Angabe in Slicer-Metadaten.')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Ungültiger Zahlenwert.')))


def _number(value, low, high):
    if isinstance(value, bool): raise ValueError('Ungültiger Zahlenwert.')
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Zahlenwert außerhalb des unterstützten Bereichs.')
    return value


def inspect(path):
    """Describe one complete, unmodified Anycubic S1 plate, fail closed otherwise.

    No extraction to disk; independently hash the inner G-code. The enclosing
    original's hash must also be verified by the caller against its catalog.
    """
    try:
        with zipfile.ZipFile(path) as package:
            names = package.namelist()
            if len(names) > 2048 or len(names) != len(set(names)):
                raise ValueError('Mehrdeutiges Druckpaket.')
            gcodes = [n for n in names if n.lower().endswith('.gcode')]
            if len(gcodes) != 1 or gcodes[0] != 'Metadata/plate_1.gcode':
                raise ValueError('Vorerst wird genau eine Druckplatte im Anycubic-Format unterstützt.')

            def read(name):
                if package.getinfo(name).file_size > MAX_METADATA:
                    raise ValueError('Slicer-Metadaten überschreiten das Prüflimit.')
                return package.read(name)

            settings = _json(read('Metadata/project_settings.config'))
            if not isinstance(settings, dict) or settings.get('printer_model') != MODEL:
                raise ValueError('Die Datei wurde nicht eindeutig für den Anycubic Kobra S1 geslicet.')
            area = settings.get('printable_area')
            if (not isinstance(area, list) or len(area) != 4 or
                    any(not isinstance(p, str) for p in area) or
                    set(area) != {'0x0','250x0','250x250','0x250'} or
                    _number(settings.get('printable_height'), 1, 250) != 250):
                raise ValueError('Das Bauraumprofil entspricht nicht dem unterstützten Kobra S1.')
            xml = read('Metadata/slice_info.config')
            if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
                raise ValueError('XML-Erweiterungen werden nicht unterstützt.')
            # Require UTF-8 before XML parsing; this also rejects UTF-16 DTD bypasses.
            root = ET.fromstring(xml.decode('utf-8-sig'))
            plates = root.findall('plate')
            if len(plates) != 1: raise ValueError('Mehrere Druckplatten werden noch nicht unterstützt.')
            plate = plates[0]
            items = plate.findall('metadata')
            meta = {n.get('key'):n.get('value') for n in items}
            if len(meta) != len(items) or meta.get('index') != '1' or meta.get('printer_model_id') != MODEL:
                raise ValueError('Widersprüchliche Druckplatten-Metadaten.')
            nozzles = settings.get('nozzle_diameter')
            if not isinstance(nozzles, list) or len(nozzles) != 1:
                raise ValueError('Düsendurchmesser ist nicht eindeutig.')
            nozzle = _number(nozzles[0], .1, 1.2)
            if nozzle != _number(meta.get('nozzle_diameters'), .1, 1.2):
                raise ValueError('Düsendurchmesser widersprechen sich.')
            if meta.get('outside') != 'false':
                raise ValueError('Die Slicer-Angabe zum Bauraum ist unklar oder meldet eine Überschreitung.')
            if any(n.get('skipped') != 'false' for n in plate.findall('object')):
                raise ValueError('Dateien mit übersprungenen Objekten werden noch nicht unterstützt.')

            info = package.getinfo(gcodes[0])
            if not 0 < info.file_size <= MAX_GCODE:
                raise ValueError('G-Code überschreitet das derzeitige Prüflimit von 32 MB.')
            sha = hashlib.sha256(); tools = set(); paint = None; count = 0
            with package.open(info) as stream:
                while True:
                    raw = stream.readline(MAX_LINE + 1)
                    if not raw: break
                    count += len(raw)
                    if len(raw) > MAX_LINE or count > MAX_GCODE:
                        raise ValueError('G-Code überschreitet das Prüflimit.')
                    sha.update(raw)
                    line = raw.decode('utf-8').strip()
                    if line.startswith('; paint_info = '):
                        current = _json(line.partition('=')[2])
                        if paint is not None and current != paint:
                            raise ValueError('Mehrdeutige Filamentzuordnung.')
                        paint = current
                    command = line.partition(';')[0].strip()
                    match = re.fullmatch(r'T(\d+)', command, re.I)
                    if match:
                        tool = int(match[1])
                        if tool > 15: raise ValueError('Nicht unterstützte Werkzeugauswahl.')
                        tools.add(tool)
                    elif re.match(r'^T\d', command, re.I):
                        raise ValueError('Nicht eindeutige Werkzeugauswahl im G-Code.')
            if count != info.file_size: raise ValueError('G-Code ist unvollständig.')
            expected = read(gcodes[0] + '.md5').decode('ascii').strip().lower()
            if not re.fullmatch('[a-f0-9]{32}', expected):
                raise ValueError('Slicer-Prüfsumme fehlt.')
            # Stream a second time rather than holding the sliced plate in RAM.
            md5 = hashlib.md5(usedforsecurity=False)
            with package.open(info) as stream:
                for chunk in iter(lambda: stream.read(256 * 1024), b''): md5.update(chunk)
            if expected != md5.hexdigest(): raise ValueError('Die Slicer-Prüfsumme stimmt nicht.')
            if not isinstance(paint, list) or not 1 <= len(paint) <= 16:
                raise ValueError('Filamentbedarf ist nicht eindeutig dokumentiert.')
            materials = []; indices = set()
            for item in paint:
                if not isinstance(item, dict): raise ValueError('Ungültige Filamentangabe.')
                index = item.get('paint_index'); color = item.get('paint_color'); material = item.get('material_type')
                if type(index) is not int or not 0 <= index <= 15 or index in indices:
                    raise ValueError('Doppelte oder ungültige Filamentnummer.')
                if not isinstance(material, str) or not 1 <= len(material) <= 40 or any(ord(c) < 32 for c in material):
                    raise ValueError('Materialtyp fehlt.')
                if not isinstance(color, list) or len(color) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
                    raise ValueError('Filamentfarbe ist nicht eindeutig.')
                types, colors, diameters = (settings.get(key) for key in
                    ('filament_type','filament_colour','filament_diameter'))
                if any(not isinstance(values, list) or len(values) <= index for values in (types, colors, diameters)):
                    raise ValueError('Projektprofil enthält keine vollständigen Filamentdaten.')
                if (types[index] != material or not isinstance(colors[index], str) or
                        colors[index].lower() != '#' + ''.join(f'{c:02x}' for c in color) or
                        _number(diameters[index], 1, 3) != 1.75):
                    raise ValueError('Projektprofil und Druckplatte haben unterschiedliche Filamentdaten.')
                matches = [n for n in plate.findall('filament') if n.get('id') == str(index + 1)]
                if len(matches) != 1 or matches[0].get('type') != material or matches[0].get('color', '').lower() != '#' + ''.join(f'{c:02x}' for c in color):
                    raise ValueError('Filamentangaben von G-Code und Druckplatte widersprechen sich.')
                indices.add(index)
                materials.append({'paint_index':index, 'type':material,
                                  'color':'#' + ''.join(f'{c:02x}' for c in color),
                                  'estimated_g':_number(matches[0].get('used_g'), 0, 100000)})
            if len(plate.findall('filament')) != len(materials) or tools != indices:
                raise ValueError('Werkzeugauswahl und Filamentbedarf stimmen nicht eindeutig überein.')
            return {'source_model':MODEL, 'nozzle_mm':nozzle, 'gcode_entry':gcodes[0],
                    'gcode_sha256':sha.hexdigest(), 'gcode_bytes':count,
                    'materials':sorted(materials, key=lambda m:m['paint_index']),
                    'slicer_warning_count':len(plate.findall('warning')),
                    'slicer_warnings':[{'message':n.get('msg','')[:160],'code':n.get('error_code','')[:40]}
                                       for n in plate.findall('warning')[:32]],
                    'printer_commands_sent':False, 'start_authorized':False,
                    'notice':'Nur Dateivorprüfung. Düse, Material, Druckbett und Start müssen separat geprüft werden. G-Code wird nicht auf Gefahrlosigkeit zertifiziert.'}
    except (KeyError, TypeError, UnicodeError, ET.ParseError, zipfile.BadZipFile,
            OverflowError, RuntimeError, RecursionError, NotImplementedError) as exc:
        raise ValueError('Druckdatei enthält keine vollständig unterstützten Slicer-Metadaten.') from exc
