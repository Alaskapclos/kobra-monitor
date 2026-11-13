"""Bounded, read-only previews of verified originals; never executes G-code.
SPDX-License-Identifier: GPL-3.0-only
"""
import math
import re
import struct
import zipfile
import xml.etree.ElementTree as ET

MAX_MEMBER = 32 * 1024**2
MAX_SEGMENTS = 500000
MAX_TRIANGLES = 30000
NUMBER = re.compile(r'([A-Z])\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))')


def member(z, name, limit=MAX_MEMBER):
    info = z.getinfo(name)
    if info.file_size > limit:
        raise ValueError('Diese Datei ist für die Vorschau zu groß. Das Original bleibt verfügbar.')
    with z.open(info) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Vorschaulimit überschritten.')
    return data


def catalog(path):
    with zipfile.ZipFile(path) as z:
        sources = []
        for item in z.infolist():
            if not item.filename.lower().endswith(('.model', '.gcode')): continue
            is_model = item.filename.lower().endswith('.model')
            # Sliced Anycubic packages may contain only an empty 3MF shell.
            if is_model and item.file_size <= 65536 and not re.search(rb'<(?:[A-Za-z_][\w.-]*:)?object\b', member(z, item.filename, 65536)):
                continue
            sources.append({'name': item.filename, 'kind': 'model' if is_model else 'gcode'})
        return {'images': [i.filename for i in z.infolist() if i.filename.lower().endswith('.png') and i.file_size <= 8 * 1024**2][:32],
                'sources': sources[:32]}


def image(path, name):
    with zipfile.ZipFile(path) as z:
        if name not in catalog(path)['images']:
            raise ValueError('Vorschaubild nicht gefunden.')
        data = member(z, name, 8 * 1024**2)
    if len(data) < 24 or data[:16] != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR':
        raise ValueError('Kein unterstütztes PNG-Bild.')
    width, height = struct.unpack('>II', data[16:24])
    if not 0 < width <= 4096 or not 0 < height <= 4096 or width * height > 8000000:
        raise ValueError('Vorschaubild überschreitet das Größenlimit.')
    return data


def point(values):
    result = [float(v) for v in values]
    if not all(math.isfinite(v) and abs(v) <= 100000 for v in result):
        raise ValueError('Koordinaten außerhalb des Vorschaubereichs.')
    return result


def toolpaths(data):
    """Linear extrusion paths only. Unsupported motion fails explicitly, not silently."""
    pos = dict.fromkeys('XYZE', 0.0)
    absolute = extruder_absolute = True
    unit = 1
    segments = []
    for index, raw in enumerate(data.decode('utf-8-sig', errors='strict').splitlines()):
        if index > 1000000 or len(raw) > 8192:
            raise ValueError('G-Code überschreitet das Vorschaulimit.')
        line = re.sub(r'\([^)]*\)', '', raw.split(';', 1)[0]).strip().upper()
        if not line:
            continue
        tokens = NUMBER.findall(line)
        commands = [(k, float(v)) for k, v in tokens if k in 'GM']
        values = {k: float(v) * unit for k, v in tokens if k in 'XYZE'}
        point(values.values())
        if any(k == 'G' and v in (2, 3, 5, 28, 29) for k, v in commands):
            if any(v in (2, 3, 5) for k, v in commands if k == 'G'):
                raise ValueError('Kurvenbefehle in dieser Datei werden noch nicht dargestellt.')
            # Homing never resets E. Its XYZ result depends on the machine;
            # require subsequent absolute coordinates/G92 before drawing again.
            axes = re.findall(r'[XYZ](?=\s|$|[-+\d.])', line) or list('XYZ')
            for axis in axes: pos[axis] = None
            continue
        for kind, command in commands:
            if kind == 'G' and command in (20, 21): unit = 25.4 if command == 20 else 1
            elif kind == 'G' and command in (90, 91): absolute = command == 90
            elif kind == 'M' and command in (82, 83): extruder_absolute = command == 82
        if ('G', 92) in commands:
            pos.update(values)
            continue
        if not any(k == 'G' and v in (0, 1) for k, v in commands):
            if any(k == 'G' and v not in (4, 20, 21, 90, 91) for k, v in commands):
                raise ValueError('Diese G-Code-Variante wird noch nicht vollständig unterstützt.')
            continue
        new = dict(pos)
        for key, value in values.items():
            new[key] = value if (extruder_absolute if key == 'E' else absolute) else (pos[key] + value if pos[key] is not None else None)
        moving = any(key in values and new[key] != pos[key] for key in 'XYZ')
        if new['E'] > pos['E'] and moving:
            if any(pos[k] is None or new[k] is None for k in 'XYZ'):
                raise ValueError('Druckbahn mit unbekannter Position nach einer Referenzfahrt. Bitte das Vorschaubild verwenden.')
            a, b = point(pos[k] for k in 'XYZ'), point(new[k] for k in 'XYZ')
            segments.append(a + b)
            if len(segments) > MAX_SEGMENTS:
                raise ValueError('Zu viele Druckbahnen für die interaktive Vorschau. Bitte das Vorschaubild verwenden.')
        pos = new
    if not segments:
        raise ValueError('Keine darstellbaren Extrusionsbahnen gefunden.')
    return {'kind': 'gcode', 'segments': segments, 'note': 'Druckbahnen · vereinfachte Darstellung, keine Drucksimulation oder Kollisionsprüfung.'}


def model(data):
    if b'\x00' in data or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('XML-Deklarationen werden nicht unterstützt.')
    root = ET.fromstring(data)
    ns = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
    if root.tag != ns + 'model' or root.get('requiredextensions'):
        raise ValueError('Dieses 3MF-Modell benötigt noch nicht unterstützte Erweiterungen.')
    unit = {'micron': .001, 'millimeter': 1, 'centimeter': 10, 'inch': 25.4, 'foot': 304.8, 'meter': 1000}.get(root.get('unit', 'millimeter'))
    if unit is None: raise ValueError('Unbekannte Modelleinheit.')
    resources = root.find(ns + 'resources')
    if resources is None: raise ValueError('Keine Modellgeometrie vorhanden.')
    objects = {obj.get('id'): obj for obj in resources.findall(ns + 'object')}
    triangles = []
    visits = 0
    def transform(value, matrix):
        x, y, z = value
        return point([x*matrix[0]+y*matrix[3]+z*matrix[6]+matrix[9], x*matrix[1]+y*matrix[4]+z*matrix[7]+matrix[10], x*matrix[2]+y*matrix[5]+z*matrix[8]+matrix[11]])
    def visit(identifier, chain, matrices):
        nonlocal visits
        visits += 1
        if visits > 10000: raise ValueError('Zu viele Modellinstanzen für die Vorschau.')
        if identifier in chain or len(chain) > 16 or identifier not in objects:
            raise ValueError('Nicht unterstützte Modellreferenz.')
        obj = objects[identifier]
        mesh = obj.find(ns + 'mesh')
        if mesh is not None:
            vertices = [point(v.get(k) for k in ('x','y','z')) for v in mesh.findall(ns + 'vertices/' + ns + 'vertex')]
            if len(vertices) > 100000: raise ValueError('Modell überschreitet das Vorschaulimit.')
            for tri in mesh.findall(ns + 'triangles/' + ns + 'triangle'):
                points = []
                for key in ('v1','v2','v3'):
                    index = int(tri.get(key))
                    if not 0 <= index < len(vertices): raise ValueError('Ungültiger Modellindex.')
                    p = vertices[index]
                    for matrix in matrices: p = transform(p, matrix)
                    points.extend(point(v * unit for v in p))
                triangles.append(points)
                if len(triangles) > MAX_TRIANGLES: raise ValueError('Modell ist für die interaktive Vorschau zu detailliert.')
        for component in obj.findall(ns + 'components/' + ns + 'component'):
            if any(key.endswith('}path') for key in component.attrib): raise ValueError('Mehrteilige 3MF-Erweiterung noch nicht unterstützt.')
            visit(component.get('objectid'), chain + [identifier], [matrix_for(component)] + matrices)
    def matrix_for(item):
        value = point(item.get('transform', '1 0 0 0 1 0 0 0 1 0 0 0').split())
        if len(value) != 12: raise ValueError('Ungültige Modelltransformation.')
        return value
    for item in root.findall(ns + 'build/' + ns + 'item'):
        if any(key.endswith('}path') for key in item.attrib): raise ValueError('Mehrteilige 3MF-Erweiterung noch nicht unterstützt.')
        visit(item.get('objectid'), [], [matrix_for(item)])
    if not triangles: raise ValueError('Keine Modellgeometrie vorhanden.')
    return {'kind': 'model', 'triangles': triangles, 'note': 'Modellgeometrie · einfarbig, ohne Material- und Textureffekte. Druckbahnen können davon abweichen.'}


def geometry(path, name):
    with zipfile.ZipFile(path) as z:
        sources = catalog(path)['sources']
        source = next((s for s in sources if s['name'] == name), None)
        if source is None: raise ValueError('Vorschauquelle nicht gefunden.')
        data = member(z, name)
    try:
        return model(data) if source['kind'] == 'model' else toolpaths(data)
    except (ET.ParseError, UnicodeError, TypeError, IndexError, OverflowError) as exc:
        raise ValueError('Datei kann nicht als verlässliche 3D-Vorschau gelesen werden.') from exc
