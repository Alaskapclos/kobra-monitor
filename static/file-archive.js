/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraFiles=(()=>{
  const $=id=>document.getElementById(id);
  let files=[],busy=false,jobGeneration=0,thumbnails=[];
  const text=(tag,value)=>{const node=document.createElement(tag);node.textContent=value;return node;};
  const size=value=>(value/1024/1024).toLocaleString('de-DE',{maximumFractionDigits:1})+' MB';
  const date=value=>new Date(value*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin'});
  function renderFiles(){
    for(const dispose of thumbnails)dispose();thumbnails=[];
    const search=$('files-search').value.trim().toLocaleLowerCase('de-DE');
    $('files-list').replaceChildren();
    const visible=files.filter(file=>file.names.some(name=>name.toLocaleLowerCase('de-DE').includes(search)));
    if(!visible.length)$('files-list').append(text('p',files.length?'Keine passende Datei.':'Noch keine Originaldatei empfangen. Ein Druckbericht allein enthält keine wiederverwendbare Druckdatei.'));
    for(const file of visible){
      const row=document.createElement('article');row.className='archive-file-card';
      const preview=text('button','');preview.type='button';preview.className='archive-thumbnail';preview.setAttribute('aria-label','Vorschau öffnen: '+file.names.join(' / '));
      preview.addEventListener('click',()=>window.kobraPreview.open(file,preview));thumbnails.push(window.kobraPreview.thumbnail(preview,file));
      row.append(preview,text('strong',file.names.join(' / ')),text('p',`${size(file.size)} · ${date(file.created_at)}`));
      const open=text('button','Vorschau öffnen');open.type='button';open.className='timeline-button';open.addEventListener('click',()=>window.kobraPreview.open(file,open));
      const a=text('a','Original herunterladen');a.className='timeline-button';a.href='/api/archive/original?sha256='+file.sha256;a.download='';row.append(open,a);if(window.kobraReprints?.button)row.append(window.kobraReprints.button(file,true));$('files-list').append(row);
    }
  }
  $('files-search').addEventListener('input',renderFiles);
  async function refresh(){
    if(!window.kobraAuth.authenticated||busy)return;busy=true;
    try{
      const data=await window.kobraAuth.archiveRequest();files=data.files;
      $('files-message').textContent=`${files.length} ${files.length===1?'Originaldatei':'Originaldateien'} erfasst · ${size(data.used_bytes)} von ${size(data.max_bytes)} belegt. Prüfung beim Eingang; Originale und Zuordnungen werden mit dem Monitor gesichert.`;
      renderFiles();
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
    target.append(text('p',detail.original?(detail.original.link_method==='reprint'?'Original aus bestätigter Archivwiederholung':'Originaldatei manuell zugeordnet')+' · SHA-256: '+detail.original.sha256:'Keine Originaldatei zugeordnet. Ein gleicher Dateiname allein belegt den Dateiinhalt nicht.'));
    if(detail.original&&detail.job.state==='completed'&&detail.job.ended_at&&window.kobraReprints?.button)target.append(window.kobraReprints.button({...detail.job,sha256:detail.original.sha256}));
    try{
      const data=await window.kobraAuth.archiveRequest();if(generation!==jobGeneration)return;
      if(detail.original){
        const file=data.files.find(file=>file.sha256===detail.original.sha256);
        if(file){const preview=text('button','Zugeordnete Datei ansehen');preview.type='button';preview.className='timeline-button';preview.addEventListener('click',()=>{window.kobraPreview.open(file,preview);$('file-preview').scrollIntoView({behavior:'smooth',block:'start'});});target.append(preview);}
      }
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
