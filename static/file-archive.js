/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraFiles=(()=>{
  const $=id=>document.getElementById(id);
  let files=[],busy=false,jobGeneration=0;
  const text=(tag,value)=>{const node=document.createElement(tag);node.textContent=value;return node;};
  const size=value=>(value/1024/1024).toLocaleString('de-DE',{maximumFractionDigits:1})+' MB';
  const date=value=>new Date(value*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin'});
  async function refresh(){
    if(!window.kobraAuth.authenticated||busy)return;busy=true;
    try{
      const data=await window.kobraAuth.archiveRequest();files=data.files;
      $('files-message').textContent=`${files.length} ${files.length===1?'Originaldatei':'Originaldateien'} erfasst · ${size(data.used_bytes)} von ${size(data.max_bytes)} belegt. Prüfung beim Eingang; Originale und Zuordnungen werden mit dem Monitor gesichert.`;
      $('files-list').replaceChildren();
      if(!files.length)$('files-list').append(text('p','Noch keine Originaldatei empfangen. Ein Druckbericht allein enthält keine wiederverwendbare Druckdatei.'));
      for(const file of files){
        const row=document.createElement('div');row.className='report-version';
        row.append(text('strong',file.names.join(' / ')),text('p',`Eingang vollständig geprüft · ${size(file.size)} · ${date(file.created_at)}`),text('small','SHA-256: '+file.sha256));
        const a=text('a','Originaldatei herunterladen');a.className='timeline-button';a.href='/api/archive/original?sha256='+file.sha256;a.download='';row.append(a);$('files-list').append(row);
      }
      $('files-clients').replaceChildren();
      for(const client of data.clients){
        const row=document.createElement('div');row.className='report-version';
        const recent=client.last_seen&&Date.now()/1000-client.last_seen<120;
        const states={ready:'Bereit',pending:'Dateien warten auf Übertragung',blocked:'Lokale Übernahme blockiert – Helfer prüfen'};
        row.append(text('strong',client.name),text('p',client.disabled?'Zugang widerrufen':(recent?states[client.status]||'Verbunden':'Keine aktuelle Rückmeldung')+(client.last_seen?' · Zuletzt: '+date(client.last_seen):'')));
        if(!client.disabled){const button=text('button','Computerzugang widerrufen');button.type='button';button.className='timeline-button';button.addEventListener('click',async()=>{
          if(!confirm('Zugang dieses Computers widerrufen? Seine vorhandenen Originaldateien bleiben erhalten.'))return;
          try{await window.kobraAuth.archiveRequest({action:'revoke',id:client.id});await refresh();}catch(error){$('files-message').textContent=error.message;}
        });row.append(button);}$('files-clients').append(row);
      }
    }catch(error){$('files-message').textContent=error.message;}finally{busy=false;}
  }
  $('files-refresh').addEventListener('click',refresh);
  $('files-pair').addEventListener('submit',async event=>{
    event.preventDefault();const button=event.currentTarget.querySelector('button');button.disabled=true;
    try{
      const config=await window.kobraAuth.archiveRequest({action:'pair',name:$('files-client-name').value});
      const url=URL.createObjectURL(new Blob([JSON.stringify(config,null,2)+'\n'],{type:'application/json'}));
      const a=text('a','');a.href=url;a.download='archive-client.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
      await refresh();$('files-message').textContent='Private Computer-Konfiguration heruntergeladen. Jetzt mit dem Archivhelfer verbinden; Zugang nicht weitergeben.';
    }catch(error){$('files-message').textContent=error.message;}finally{button.disabled=false;}
  });
  async function forJob(detail){
    const generation=++jobGeneration,target=$('order-original');target.replaceChildren();
    target.append(text('p',detail.original?'Originaldatei manuell zugeordnet · SHA-256: '+detail.original.sha256:'Keine Originaldatei zugeordnet. Ein gleicher Dateiname allein belegt den Dateiinhalt nicht.'));
    try{
      const data=await window.kobraAuth.archiveRequest();if(generation!==jobGeneration)return;
      if(!data.files.length)return;
      const label=text('label','Originaldatei auswählen'),select=document.createElement('select');
      select.append(new Option('Bitte anhand der Datei und Prüfsumme prüfen',''));
      for(const file of data.files)select.append(new Option(file.names.join(' / ')+' · '+file.sha256.slice(0,12),file.sha256));
      label.append(select);const button=text('button','Geprüfte Datei diesem Auftrag zuordnen');button.type='button';button.className='timeline-button';button.disabled=true;select.addEventListener('change',()=>{button.disabled=!select.value;});
      button.addEventListener('click',async()=>{
        if(!confirm('Diese Originaldatei ausdrücklich diesem Auftrag zuordnen? Der Dateiname allein ist kein Nachweis. Bei abgeschlossenen Aufträgen entsteht eine neue Berichtsversion.'))return;
        button.disabled=true;
        try{await window.kobraAuth.archiveRequest({action:'link',job:detail.job.id,sha256:select.value});const result=await window.kobraAuth.orderReport(null,detail.job.id);window.kobraOrders?.originalUpdated(result);await forJob(result);window.dispatchEvent(new Event('kobra-report-changed'));$('order-message').textContent='Originaldatei zugeordnet. Die Berichtsversionen sind aktualisiert.';}
        catch(error){target.append(text('p',error.message));button.disabled=false;}
      });target.append(label,button);
    }catch(error){if(generation===jobGeneration)target.append(text('p',error.message));}
  }
  window.kobraAuth.ready.then(refresh);window.addEventListener('kobra-authenticated',refresh);window.addEventListener('hashchange',()=>{if(location.hash==='#orders')refresh();});
  setInterval(()=>{if(location.hash==='#orders')refresh();},60000);
  return {refresh,forJob};
})();
