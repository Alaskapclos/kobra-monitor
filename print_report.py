"""Local Markdown reports from stored observations; no network operations.
SPDX-License-Identifier: GPL-3.0-only
"""
import math
from datetime import datetime
from zoneinfo import ZoneInfo


def render_report(job, samples, events):
    def stamp(at):
        return datetime.fromtimestamp(at, ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y %H:%M:%S')
    def clean(value):
        return str(value).replace('\r', ' ').replace('\n', ' ').replace('|', '/').replace('`', "'")
    def numeric(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    def temperature(key):
        values = [s['data'].get('data', {}).get(key) for s in samples]
        values = [v for v in values if numeric(v)]
        return f'{min(values):g}–{max(values):g} °C' if values else 'Keine Messwerte'

    labels = {'completed': 'Abgeschlossen', 'cancelled': 'Abgebrochen',
              'unknown_end': 'Ende nicht beobachtet'}
    ended = job['ended_at']
    last = ended if ended is not None else job['last_seen']
    duration = max(0, last-job['first_seen'])
    lines = ['# Druckbericht', '', f"Datei: {clean(job['filename'])}",
             f"Drucker: {clean(job['ip'])}",
             f"Auftragskennung: {clean(job['id'])}",
             f"Status: {labels.get(job['state'], 'Laufender Auftrag ('+clean(job['state'])+')')}", '',
             '## Beobachtete Zeiten', '', 'Zeitzone: Europe/Berlin.', '',
             f"- Erstmals erkannt: {stamp(job['first_seen'])}",
             f"- Letzte Auftragsbeobachtung: {stamp(last)}",
             f"- Beobachtungsdauer: {int(duration//3600)} h {int(duration%3600//60)} min {int(duration%60)} s",
             '- Zeitangaben beruhen auf Aufzeichnungen, nicht auf zwischengespeicherten Firmware-Laufzeiten.']
    if ended is not None:
        lines.append(f"- {'Abschluss' if job['state']=='completed' else 'Ende'}: {stamp(ended)}")
    else:
        lines.append('- Kein bestätigtes Druckende; dieser Bericht ist vorläufig.')
    lines += ['', '## Abdeckung und Zustände', '']
    if job['observed_start']:
        lines.append('Der Beginn wurde nach einer aktuellen Leerlaufbeobachtung erkannt.')
    else:
        lines.append('Die automatische Kennzeichnung bestätigt keinen beobachteten Beginn. Vorbereitungsereignisse sind unten aufgeführt; alte Laufzeitwerte können bei früheren Monitorversionen diese Kennzeichnung beeinflusst haben.')
    for event in events:
        kind = event['kind']
        details = event['details']
        if kind == 'state':
            text = f"{clean(details.get('from', '?'))} → {clean(details.get('to', '?'))}"
        elif kind in ('start_observed', 'active_job_discovered'):
            text = f"Auftrag erkannt: {clean(details.get('state', '?'))}"
        elif kind == 'printer_error':
            text = f"Druckermeldung: {clean(details.get('state', '?'))}; Code {clean(details.get('code', '?'))}; {clean(details.get('message', ''))}"
        else:
            text = clean(kind)
        lines.append(f"- {stamp(event['at'])}: {text}")
    intervals = [b['at']-a['at'] for a,b in zip(samples, samples[1:])]
    gaps = [v for v in intervals if v > 90]
    disconnected = [e for e in events if e['kind']=='disconnected']
    offline = [s for s in samples if s['data'].get('connection') in ('offline','stale')]
    errors = [e for e in events if e['kind']=='printer_error']
    lines += ['', f'- Gespeicherte Stichproben: {len(samples)}.',
              f'- Größter Stichprobenabstand: {max(intervals):.1f} s.' if intervals else '- Stichprobenabstand nicht bestimmbar.',
              f'- Verbindungsunterbrechungen: {len(disconnected)}; veraltete/offline Stichproben: {len(offline)}; Druckerfehlermeldungen: {len(errors)}.']
    if gaps:
        lines.append(f'- {len(gaps)} Stichprobenabstände über 90 s: In diesen Zeiträumen ist der Verlauf nicht vollständig rekonstruierbar.')
    if not samples:
        lines.append('- Keine Stichproben vorhanden; Temperaturen und Filamentverlauf nicht belegbar.')
    elif not gaps and not disconnected and not offline:
        lines.append('- In den gespeicherten Stichproben und Ereignissen ist keine Überwachungslücke belegt. Dies ist keine kontinuierliche Aufzeichnung jedes Telegramms.')
    if samples and samples[0]['at']-job['first_seen']>90:
        lines.append('- Die erste Stichprobe liegt über 90 s nach der Erkennung; Messwerte am Beginn fehlen.')
    if samples and last-samples[-1]['at']>90:
        lines.append('- Die letzte Stichprobe liegt über 90 s vor der letzten Auftragsbeobachtung; Messwerte am Ende fehlen.')
    lines += ['', '## Temperaturen', '',
              f"- Düse: {temperature('nozzle_temp')}", f"- Bett: {temperature('bed_temp')}",
              '- Minima/Maxima umfassen Vorbereitung und Abkühlung, soweit aufgezeichnet. Sie beschreiben keine Regelgenauigkeit.',
              '', '## ACE und Filament', '']
    slots = {}; loaded = set(); climate = []
    for sample in samples:
        data = sample['data'].get('data') or {}
        value = data.get('loaded_slot')
        if numeric(value) and value >= 0: loaded.add(value)
        for slot in data.get('ace_slots') or []:
            # Box and native slot identify a slot even in partial reports.
            slots[(slot.get('box_id',0), slot.get('index'))] = slot
        temp = (data.get('ace_drying') or {}).get('current_temp')
        if numeric(temp): climate.append(temp)
    for (box, index),slot in sorted(slots.items(), key=lambda item: str(item[0])):
        lines.append(f"- Box {clean(box)}, Slotindex {clean(index)}: {clean(slot.get('type') or 'Unbekannt')}; Farbe RGB {clean(slot.get('color', 'unbekannt'))}.")
    if not slots: lines.append('- Keine ACE-Slotdaten aufgezeichnet.')
    lines.append('- Gemeldete geladene Slotindizes (nullbasiert): '+(', '.join(str(v) for v in sorted(loaded)) if loaded else 'keine')+'.')
    if climate: lines.append(f'- ACE-Temperatur: {min(climate):g}–{max(climate):g} °C.')
    lines += ['- Slotlisten können in einzelnen Meldungen unvollständig sein. Die Übersicht fasst die beobachteten Slots zusammen.',
              '- Restprozente und Luftfeuchtigkeit sind unvalidierte Druckerangaben. Nullwerte belegen weder leere Spulen noch reale 0 % Feuchte.',
              '', '## Hinweise', '',
              'Dieser Bericht wird ausschließlich aus der lokalen Historie erstellt. Der Download sendet keine Anfrage und keinen Steuerbefehl an einen Drucker. Ein gemeldeter Abschluss bewertet nicht die physische Qualität des Bauteils.', '']
    return '\n'.join(lines)
