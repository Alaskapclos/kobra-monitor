/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraDiagnostics=(()=>{
  const $=id=>document.getElementById(id);
  let lastReport=null,busy=false;
  function clientSummary(){
    const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
    return {https:location.protocol==='https:',secure_context:window.isSecureContext,
      push_supported:'serviceWorker' in navigator&&'PushManager' in window&&'Notification' in window,
      notification_permission:'Notification' in window?Notification.permission:'unsupported',
      ios_home_screen_required:ios,
      home_screen:window.matchMedia('(display-mode: standalone)').matches||!!navigator.standalone};
  }
  function row(title,value,detail,level='ok'){
    const item=document.createElement('div'),icon=document.createElement('span'),content=document.createElement('div'),heading=document.createElement('strong'),status=document.createElement('p'),help=document.createElement('p');
    item.className='check-row check-'+level;icon.className='check-mark';icon.textContent=level==='ok'?'✓':level==='warning'?'!':'i';icon.setAttribute('aria-hidden','true');
    heading.textContent=title;status.textContent=value;help.textContent=detail;help.className='check-detail';content.append(heading,status,help);item.append(icon,content);$('check-results').append(item);
  }
  function render(report){
    const server=report.monitor,client=report.browser;$('check-results').replaceChildren();
    row('Monitor','Version '+server.version+' · Nur lesen','Der Dienst ist erreichbar. Laufzeit: '+Math.floor(server.uptime_seconds/60)+' Minuten.');
    row('Zugriff',client.https?'HTTPS aktiv':'HTTP-Adresse geöffnet',client.https?'Diese Verbindung ist verschlüsselt.':'Für Handy-Benachrichtigungen die HTTPS-Adresse dieser Installation verwenden.',client.https?'ok':'warning');
    if(!server.printers.length)row('Drucker','Noch kein Drucker eingerichtet','Unter „Einrichten“ die IP-Adresse des Druckers eintragen.','info');
    const states={online:'Aktuelle Daten empfangen',stale:'Messwerte sind veraltet',offline:'Verbindung unterbrochen',connecting:'Warte auf Druckerdaten'};
    for(const printer of server.printers){
      const fresh=printer.state==='online';let detail=fresh?'Temperaturen sind aktuell.':'LAN-Modus und gespeicherte Adresse unter „Einrichten“ prüfen. Der Monitor-Rechner bzw. das NAS muss den Drucker im Heimnetz erreichen.';
      if(fresh&&!printer.temperature_current)detail='Die Verbindung liefert Daten, aber die Temperaturwerte fehlen oder sind veraltet.';
      if(printer.age_seconds!==null)detail+=' Letzte Messwerte vor '+Math.round(printer.age_seconds)+' Sekunden.';
      row('Drucker '+printer.number,states[printer.state]||'Warte auf Daten',detail,fresh&&printer.temperature_current?'ok':'warning');
    }
    row('Kameraaufbereitung',server.camera_decoder_ready?'Bereit':'Zurzeit nicht verfügbar',server.camera_decoder_ready?'Öffne die Kameraansicht, um das tatsächliche Bild zu prüfen.':'FFmpeg auf dem Monitor-Rechner oder NAS prüfen. Handy und Mac als reine Anzeige brauchen es nicht. Die Erkennung wird automatisch wiederholt.',server.camera_decoder_ready?'ok':'warning');
    row('Druckverlauf',server.history.jobs+' gespeicherte Aufträge','Der gespeicherte Verlauf ist lesbar. Den aktuellen Sicherungsstand prüfst du beim eingerichteten Sicherungsdienst.');
    const push=server.notifications;
    row('Benachrichtigungsdienst',push.worker_running?'Aktiv · '+push.devices+' angemeldete Geräte':'Zurzeit nicht aktiv',push.worker_running?(push.pending?push.pending+' Meldungen warten auf einen Sendeversuch.':'Zurzeit wartet keine Meldung auf Versand.'):'Monitor-Protokoll prüfen und den Dienst auf dem Monitor-Rechner bzw. NAS prüfen.',push.worker_running?'ok':'warning');
    if(push.devices_with_errors)row('Zustellung',push.devices_with_errors+' Geräte mit Zustellfehler','Unter „Benachrichtigungen“ den Gerätestatus aktualisieren und eine Testmeldung senden.','warning');
    const reason=window.kobraNotifications?.support()||(!client.push_supported?'Dieser Browser unterstützt keine Push-Meldungen.':'');
    let hint=reason||'Unter „Benachrichtigungen“ dieses Gerät aktivieren und den Empfang mit einer Testmeldung bestätigen.';
    row('Benachrichtigungen auf diesem Gerät',reason?'Einrichtung benötigt Aufmerksamkeit':client.notification_permission==='granted'?'Im Browser erlaubt':'Noch nicht erlaubt',hint,reason?'warning':client.notification_permission==='granted'?'ok':'info');
  }
  async function check(){
    if(busy)return;busy=true;$('check-run').disabled=true;$('check-copy').disabled=true;$('check-message').textContent='Wird geprüft …';lastReport=null;$('check-report').hidden=true;$('check-report').value='';
    try{
      const response=await fetch('/api/diagnostics',{signal:AbortSignal.timeout(15000)});
      if(response.status===401){window.kobraAuth?.login();throw new Error('Bitte erneut anmelden und die Prüfung wiederholen.');}
      if(!response.ok)throw new Error('Betriebsstatus nicht erreichbar. Prüfe die Verbindung zum Monitor.');
      lastReport={monitor:await response.json(),browser:clientSummary()};render(lastReport);$('check-copy').disabled=false;
      $('check-message').textContent='Prüfung abgeschlossen. Ein laufender Druck wird dabei nicht verändert.';
    }catch(error){$('check-results').replaceChildren();$('check-message').textContent=error.message||'Bitte erneut versuchen.';}
    finally{busy=false;$('check-run').disabled=false;}
  }
  $('check-open').addEventListener('click',()=>{const open=$('check-content').hidden;$('check-content').hidden=!open;$('check-open').setAttribute('aria-expanded',String(open));$('check-open').textContent=open?'Schließen':'Öffnen';if(open)check();});
  $('check-run').addEventListener('click',check);
  $('check-copy').addEventListener('click',async()=>{
    if(!lastReport)return;const text=JSON.stringify(lastReport,null,2);
    try{await navigator.clipboard.writeText(text);$('check-message').textContent='Prüfbericht kopiert. Er enthält keine Zugangsdaten, Dateinamen, Druckernamen oder IP-Adressen.';}
    catch{const field=$('check-report');field.hidden=false;field.value=text;field.focus();field.select();$('check-message').textContent='Du kannst den markierten Prüfbericht jetzt kopieren.';}
  });
  return {clientSummary};
})();
