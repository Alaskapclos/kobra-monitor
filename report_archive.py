# SPDX-License-Identifier: GPL-3.0-only
"""Versioned local customer reports. No network, printer or inventory writes."""
import hashlib
import io
import json
import re
import sqlite3
import threading
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

GENERATOR_VERSION=Path(__file__).with_name('VERSION').read_text().strip()
FIELDS = {'customer_order': 100, 'position': 80, 'part': 200, 'approver': 100, 'note': 2000}
STATES = {'pending': 'Nicht geprüft', 'accepted': 'Freigegeben', 'rejected': 'Beanstandet'}
FONT_LOCK = threading.Lock()


def stamp(value):
    return datetime.fromtimestamp(value, ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y %H:%M:%S')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def pdf_report(markdown, title):
    from reportlab import rl_config
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    with FONT_LOCK:
        if 'KobraReport' not in pdfmetrics.getRegisteredFontNames():
            font = next(Path(p)/'Vera.ttf' for p in rl_config.TTFSearchPath if (Path(p)/'Vera.ttf').exists())
            pdfmetrics.registerFont(TTFont('KobraReport', str(font)))
    normal = ParagraphStyle('body', fontName='KobraReport', fontSize=9, leading=14,
                            spaceAfter=6, splitLongWords=True, textColor=colors.HexColor('#26332e'))
    h1 = ParagraphStyle('title', parent=normal, fontSize=20, leading=26, spaceAfter=16)
    h2 = ParagraphStyle('section', parent=normal, fontSize=12, leading=18, spaceBefore=14, spaceAfter=8)
    stream = io.BytesIO()
    doc = SimpleDocTemplate(stream, title=title, author='Kobra Monitor', pagesize=(595.28, 841.89),
                            leftMargin=48, rightMargin=48, topMargin=55, bottomMargin=50)
    chars = pdfmetrics.getFont('KobraReport').face.charToGlyph
    missing = False
    story = []
    for line in markdown.splitlines():
        if not line.strip():
            story.append(Spacer(1, 4)); continue
        style = h2 if line.startswith('## ') else h1 if line.startswith('# ') else normal
        text = line.removeprefix('## ').removeprefix('# ').replace('→','->')
        if any(ord(c) not in chars for c in text): missing = True
        text = ''.join(c if ord(c) in chars else '?' for c in text)
        story.append(Paragraph(escape(text), style))
    if missing:
        story.append(Paragraph('Einzelne Zeichen sind im PDF als ? dargestellt. Den vollständigen Unicode-Text enthält der JSON-/Markdown-Export.', normal))
    def footer(canvas, _doc):
        canvas.setFont('KobraReport', 8)
        canvas.setFillColor(colors.HexColor('#64715c'))
        canvas.drawString(48, 26, 'Kobra Monitor · Archivierter Druckbericht')
        canvas.drawRightString(547, 26, f'Seite {_doc.page}')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()


class ReportArchive:
    def __init__(self, history):
        self.h = history
        self.directory = Path(history.db.execute('PRAGMA database_list').fetchone()[2]).parent/'report-archive'
        history.db.executescript('''
          CREATE TABLE IF NOT EXISTS job_annotations(job_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,fields TEXT NOT NULL,updated_at REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS report_versions(job_id TEXT NOT NULL,version INTEGER NOT NULL,created_at REAL NOT NULL,reason TEXT NOT NULL,payload TEXT NOT NULL,markdown TEXT NOT NULL,pdf BLOB NOT NULL,sha256 TEXT NOT NULL,PRIMARY KEY(job_id,version));
          CREATE TRIGGER IF NOT EXISTS report_no_update BEFORE UPDATE ON report_versions BEGIN SELECT RAISE(ABORT,'Archived report versions are immutable'); END;
          CREATE TRIGGER IF NOT EXISTS report_no_delete BEFORE DELETE ON report_versions BEGIN SELECT RAISE(ABORT,'Archived report versions are immutable'); END;
        ''')

    def job(self, job_id):
        row = self.h.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None: raise ValueError('Auftrag nicht gefunden.')
        return dict(row)

    def annotation(self, job_id):
        row = self.h.db.execute('SELECT * FROM job_annotations WHERE job_id=?', (job_id,)).fetchone()
        return {'revision': row['revision'], **json.loads(row['fields'])} if row else {
            'revision': 0, **{k: '' for k in FIELDS}, 'approval': 'pending', 'approved_at': None}

    def detail(self, job_id):
        with self.h.lock:
            job = self.job(job_id)
            versions = [dict(r) for r in self.h.db.execute(
                'SELECT version,created_at,reason,sha256 FROM report_versions WHERE job_id=? ORDER BY version DESC', (job_id,))]
            return {'read_only': True, 'job': job, 'annotation': self.annotation(job_id), 'versions': versions, 'original': self.h.files.linked(job_id)}

    def save(self, job_id, body):
        with self.h.lock:
            self.job(job_id)
            old = self.annotation(job_id)
            if type(body.get('expected_revision')) is not int or body['expected_revision'] != old['revision']:
                raise RuntimeError('Der Auftrag wurde inzwischen geändert. Bitte neu öffnen.')
            if set(body) - (set(FIELDS) | {'approval', 'expected_revision'}):
                raise ValueError('Unbekannte Auftragsangabe.')
            fields = {}
            for key, limit in FIELDS.items():
                value = body.get(key, '')
                if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 and not (c == '\n' and key == 'note') for c in value):
                    raise ValueError('Auftragsangaben sind zu lang oder enthalten ungültige Zeichen.')
                fields[key] = value.strip()
            approval = body.get('approval', 'pending')
            if self.job(job_id)['ended_at'] is None and approval != 'pending':
                raise ValueError('Qualitätsabnahme erst nach Druckende eintragen.')
            if approval not in STATES or (approval != 'pending' and not fields['approver']):
                raise ValueError('Für eine Qualitätsabnahme bitte einen Prüfernamen eintragen.')
            fields['approval'] = approval
            fields['approved_at'] = (old['approved_at'] if approval == old['approval'] and fields['approver'] == old['approver'] else self.h.clock()) if approval != 'pending' else None
            if fields == {k: v for k, v in old.items() if k != 'revision'}:
                return self.detail(job_id)
            try:
                self.h.db.execute('INSERT OR REPLACE INTO job_annotations VALUES(?,?,?,?)',
                                  (job_id, old['revision']+1, canonical(fields), self.h.clock()))
                version=None
                if self.job(job_id)['ended_at'] is not None:
                    version=self.freeze(job_id, 'Auftragsangaben / Qualitätsabnahme geändert', commit=False)
                self.h.db.commit()
                if version:self.write_files(job_id,version)
            except Exception:
                self.h.db.rollback(); raise
            return self.detail(job_id)

    def freeze(self, job_id, reason='Druckende', materials=None, commit=True):
        with self.h.lock:
            job = self.job(job_id)
            if job['ended_at'] is None: raise ValueError('Laufende Aufträge erhalten erst nach ihrem Ende eine Archivversion.')
            if reason=='Druckende' and job['state']=='unknown_end':reason='Ende nicht beobachtet'
            elif reason=='Druckende' and job['state']=='cancelled':reason='Druck abgebrochen'
            annotation = self.annotation(job_id)
            last = self.h.db.execute('SELECT * FROM report_versions WHERE job_id=? ORDER BY version DESC LIMIT 1', (job_id,)).fetchone()
            original = self.h.files.linked(job_id)
            if last and json.loads(last['payload'])['annotation'] == annotation and json.loads(last['payload']).get('original') == original:
                self.write_files(job_id,last['version'])
                return last['version']
            now = self.h.clock()
            version = (last['version']+1) if last else 1
            # Later revisions retain the originally captured material evidence.
            if last: materials = json.loads(last['payload'])['materials']
            evidence = {'samples': [], 'events': []}
            for row in self.h.db.execute('SELECT at,data FROM samples WHERE ip=? AND job_id=? AND at>=? AND at<=? ORDER BY at',
                                         (job['ip'], job_id, job['first_seen'], job['ended_at']+1)):
                evidence['samples'].append({'at': row['at'], 'data': json.loads(row['data'])})
            for row in self.h.db.execute('SELECT at,kind,details FROM events WHERE ip=? AND at>=? AND at<=? AND (job_id=? OR job_id IS NULL) ORDER BY at,id',
                                         (job['ip'], job['first_seen'], job['ended_at']+1, job_id)):
                evidence['events'].append({**dict(row), 'details': json.loads(row['details'])})
            payload = {'schema': 'kobra-customer-report-v1', 'generator_version':GENERATOR_VERSION, 'job': job, 'annotation': annotation,
                       'version': version, 'created_at': now, 'reason': reason, 'evidence': evidence,
                       'original': original, 'materials': materials or {'basis': 'Keine zeitgleiche Spoolman-Zuordnung am Druckende gespeichert.'},
                       'limits': ['Kein gemessener Grammverbrauch.', 'Keine automatische Bewertung der Bauteilqualität.',
                                  ('Original aus bestätigter Archivwiederholung zugeordnet; eine unabhängige Inhaltsprüfsumme vom Drucker liegt nicht vor.' if original.get('link_method')=='reprint' else 'Originaldatei wurde manuell zugeordnet; die Druckerausführung dieses Inhalts ist damit nicht unabhängig belegt.') if original else 'Keine Originaldatei zugeordnet; kein Datei-Inhaltshash verfügbar.']}
            from print_report import render_report
            markdown = '# Kundenauftragsbericht\n\n'
            for label, key in [('Kundenauftrag', 'customer_order'), ('Position', 'position'), ('Teil', 'part')]:
                markdown += f'{label}: {annotation[key] or "Nicht angegeben"}\n\n'
            markdown += f'Archivversion: {version} · Erstellt: {stamp(now)} Europe/Berlin\n\n'
            markdown += f'Qualitätsabnahme (manuell): {STATES[annotation["approval"]]}\n\n'
            if annotation['approved_at']:
                markdown += f'Prüfer: {annotation["approver"]} · Zeitpunkt: {stamp(annotation["approved_at"])}\n\n'
            if annotation['note']: markdown += 'Manuelle Anmerkung:\n\n'+'\n'.join('> '+s for s in annotation['note'].splitlines())+'\n\n'
            markdown += render_report(job, evidence['samples'], evidence['events']).replace('# Druckbericht','## Druckdaten',1)
            material=payload['materials']
            markdown += '\n## Gespeicherte Materialzuordnung\n\n'+material.get('basis','Zuordnung gespeichert.')+'\n\n'
            if material.get('captured_at'):
                markdown += 'Erfasst: '+stamp(material['captured_at'])+' Europe/Berlin\n\n'
                markdown += 'Spoolman-Bestand zu diesem Zeitpunkt: '+('aktuell' if material.get('inventory_current') else 'nicht aktuell / nicht verfügbar')+'.\n\n'
            for detection in material.get('detections',[]):
                markdown += f"- Slot {detection['slot']+1}: Kennung {detection.get('sku') or 'nicht gemeldet'}; Erkennung {detection['status']}; Spoolman-ID {detection.get('spool_id') or 'nicht eindeutig'}.\n"
            for slot,spool in material.get('manual_slots',{}).items():
                markdown += f'- Feste manuelle Zuordnung: Slot {int(slot)+1} -> Spoolman #{spool}.\n'
            for spool in material.get('inventory',[]):
                markdown += '- Spoolman #'+str(spool['id'])+': '+' / '.join(str(spool.get(k) or 'nicht angegeben') for k in ('vendor','name','material'))+'; Buchrestgewicht: '+str(spool.get('remaining_weight') if spool.get('remaining_weight') is not None else 'unbekannt')+' g.\n'
            if original:
                origin='Zuordnung aus bestätigter Archivwiederholung.' if original.get('link_method')=='reprint' else 'Manuelle Zuordnung.'
                markdown += '\n## Zugeordnete Originaldatei\n\nSHA-256: '+original['sha256']+'\n\nGröße: '+str(original['size'])+' Bytes. '+origin+'\n'
                if original.get('link_method')=='reprint':
                    markdown += '\nErfolgreicher Quellauftrag: '+str(original.get('source_job') or '')+'\n\nUrsprüngliche Datei: '+str(original.get('source_filename') or '')+'\n'
            markdown+='\n' 
            markdown += '\n'.join('- '+s for s in payload['limits'])+'\n'
            raw = canonical(payload)
            pdf = pdf_report(markdown, 'Druckbericht '+(annotation['customer_order'] or job_id))
            digest = hashlib.sha256(raw.encode()+markdown.encode()+pdf).hexdigest()
            self.h.db.execute('INSERT INTO report_versions VALUES(?,?,?,?,?,?,?,?)',
                              (job_id, version, now, reason, raw, markdown, pdf, digest))
            if commit:
                self.h.db.commit()
                self.write_files(job_id,version)
            return version

    def write_files(self, job_id, version):
        # Only fixed application-owned directories, never request-supplied paths.
        if not re.fullmatch('[a-f0-9]{32}',job_id): raise ValueError('Ungültiger Auftrag.')
        target=self.directory/job_id/('v'+str(version))
        for directory in (self.directory,self.directory/job_id,target):
            if directory.is_symlink(): raise OSError('Archivordner darf kein symbolischer Link sein.')
            directory.mkdir(mode=0o700,exist_ok=True)
        for fmt in ('pdf','json','md'):
            data,_,name=self.export(job_id,version,fmt)
            path=target/name
            if path.exists():
                if path.is_symlink() or path.read_bytes()!=data: raise OSError('Archivdatei wurde verändert.')
                continue
            descriptor,temporary=tempfile.mkstemp(prefix='.report-',dir=target)
            try:
                with os.fdopen(descriptor,'wb') as stream:
                    stream.write(data);stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,path)
            finally: Path(temporary).unlink(missing_ok=True)

    def bootstrap(self):
        # Bounded, restartable backfill. Never invent end-time material links.
        with self.h.lock:
            ids = [r[0] for r in self.h.db.execute('SELECT id FROM jobs WHERE ended_at IS NOT NULL AND id NOT IN (SELECT job_id FROM report_versions) ORDER BY first_seen LIMIT 100')]
        for job_id in ids: self.freeze(job_id, 'Bestehender Auftrag nachträglich archiviert')
        return len(ids)

    def export(self, job_id, version, fmt):
        with self.h.lock:
            row = self.h.db.execute('SELECT * FROM report_versions WHERE job_id=? AND version=?', (job_id, version)).fetchone()
            if row is None: raise ValueError('Archivversion nicht gefunden.')
            payload = json.loads(row['payload'])
            if hashlib.sha256(row['payload'].encode()+row['markdown'].encode()+bytes(row['pdf'])).hexdigest()!=row['sha256']:
                raise ValueError('Archiv-Prüfsumme stimmt nicht. Bitte Sicherung prüfen.')
            def slug(s): return re.sub(r'[^A-Za-z0-9_-]+', '-', s).strip('-')[:60]
            a = payload['annotation']
            name = '_'.join(filter(None, [slug(a['customer_order']), slug(a['position']), datetime.fromtimestamp(payload['created_at'],ZoneInfo('Europe/Berlin')).strftime('%Y-%m-%d'), job_id, 'v'+str(version)]))
            if fmt == 'pdf': data, mime = bytes(row['pdf']), 'application/pdf'
            elif fmt == 'json': data, mime = canonical({**payload, 'archive_sha256': row['sha256']}).encode(), 'application/json'
            elif fmt == 'md': data, mime = row['markdown'].encode(), 'text/markdown'
            else: raise ValueError('Unbekanntes Exportformat.')
            return data, mime, name+'.'+fmt

    def bundle(self, ids):
        if not isinstance(ids,list) or not 1 <= len(ids) <= 25 or any(not isinstance(s,str) for s in ids) or len(set(ids)) != len(ids):
            raise ValueError('Bitte 1 bis 25 unterschiedliche Aufträge auswählen.')
        stream = io.BytesIO(); total = 0; manifest = []
        with self.h.lock, zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for job_id in ids:
                detail = self.detail(job_id)
                if not detail['versions']: raise ValueError('Für einen ausgewählten Auftrag fehlt noch eine Archivversion.')
                version = detail['versions'][0]['version']
                manifest.append({'job_id': job_id, **detail['versions'][0]})
                for fmt in ('pdf','json','md'):
                    data, _, name = self.export(job_id, version, fmt)
                    total += len(data)
                    if total > 64*1024*1024: raise ValueError('Auswahl zu groß. Bitte weniger Aufträge wählen.')
                    archive.writestr(name,data)
            archive.writestr('manifest.json',canonical(manifest))
        return stream.getvalue()
