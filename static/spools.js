/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraSpools=(()=>{
  const $=id=>document.getElementById(id);
  let state=null,printers=[],selected=null,busy=false,signature='',shownFresh=null,loaded=false;
  function caption(spool){
    const weight=typeof spool.remaining_weight==='number'&&Number.isFinite(spool.remaining_weight)?Math.round(spool.remaining_weight)+' g Rest in Spoolman':'Restgewicht unbekannt';
    return '#'+spool.id+' · '+[spool.vendor,spool.name,spool.material].filter(Boolean).join(' · ')+' · '+weight;
  }
  function draw(){
    const target=$('spools-assignments');target.replaceChildren();if(!state)return;
    $('spools-refresh').disabled=busy||!state.configured;
    const visit=$('spools-visit');visit.hidden=true;visit.removeAttribute('href');
    try{const url=new URL(state.url);if(state.configured&&['http:','https:'].includes(url.protocol)&&!url.username&&!url.password){visit.href=url.href;visit.hidden=false;}}catch{}
    const current=state.inventory_current&&state.checked_at!==null&&(Date.now()/1000-state.checked_at)<=60;shownFresh=current;
    $('spools-updated').textContent=state.checked_at?'Bestand gelesen: '+new Date(state.checked_at*1000).toLocaleString()+(current?'':' · Nicht aktuell; bitte aktualisieren.'):'Noch kein Bestand gelesen.';
    const mappings=state.mappings||{},chosen=printers.find(p=>p.ip===selected);
    const rows=[];
    if(chosen){for(const slot of chosen.data?.ace_slots||[]){const index=slot.global_index??slot.index;if(Number.isInteger(index)&&index>=0&&index<16)rows.push({ip:selected,slot:index,missing:false});}}
    for(const [ip,slots] of Object.entries(mappings))for(const slot of Object.keys(slots)){
      if(!printers.some(p=>p.ip===ip)||(ip===selected&&!rows.some(r=>r.ip===ip&&r.slot===Number(slot))))rows.push({ip,slot:Number(slot),missing:true});
    }
    if(!rows.length){const p=document.createElement('p');p.textContent='Wähle einen Drucker mit gemeldeten ACE-Steckplätzen.';target.append(p);}
    for(const row of rows){
      const card=document.createElement('div'),label=document.createElement('label'),select=document.createElement('select'),button=document.createElement('button'),detail=document.createElement('p');
      card.className='spool-assignment';label.textContent=(row.missing?'Nicht mehr gemeldeter Steckplatz':'Ausgewählter Drucker')+' · SLOT '+(row.slot+1);
      select.setAttribute('aria-label','Spule für Slot '+(row.slot+1));
      const empty=document.createElement('option');empty.value='';empty.textContent='Keine feste Slot-Zuordnung';select.append(empty);
      const assigned=mappings[row.ip]?.[String(row.slot)];
      const linkedIds=new Set(Object.values(state.sku_links||{}));
      for(const spool of state.spools){const option=document.createElement('option');option.value=String(spool.id);option.textContent=caption(spool)+(linkedIds.has(spool.id)?' · folgt ihrer Kennung':'');option.disabled=linkedIds.has(spool.id);select.append(option);}
      if(assigned&&!state.spools.some(s=>s.id===assigned)){const option=document.createElement('option');option.value=String(assigned);option.textContent='#'+assigned+' · Nicht im aktuellen Bestand';select.append(option);}
      select.value=assigned?String(assigned):'';
      // Clearing a mapping must work even if Spoolman is down or the printer is removed.
      if(!current||row.missing)for(const option of select.options)if(option.value&&Number(option.value)!==assigned)option.disabled=true;
      select.disabled=busy;
      button.className='timeline-button';button.type='button';button.textContent=assigned?'Feste Zuordnung ändern':'Fest diesem Slot zuordnen';button.disabled=busy;
      button.addEventListener('click',()=>request({action:'assign',ip:row.ip,slot:row.slot,spool_id:select.value?Number(select.value):null}));
      label.append(select);detail.textContent=assigned?'Fest diesem Slot zugeordnet · folgt einem Spulenwechsel nicht automatisch.':'Ohne eindeutige Kennung kannst du eine Spule fest diesem Slot zuordnen.';
      card.append(label,button,detail);target.append(card);
      const detected=state.detections?.find(d=>d.ip===row.ip&&d.slot===row.slot);
      const age=chosen?.section_age_s?.ace;
      const fresh=chosen?.connection==='online'&&typeof age==='number'&&age>=0&&age<=60;
      const linkedHere=detected?.sku&&(state.sku_links||{})[detected.sku];
      const recognized=detected?.status==='recognized'&&fresh&&current&&state.spools.some(s=>s.id===detected.spool_id);
      if(recognized&&!assigned){
        select.value=String(detected.spool_id);select.disabled=true;button.hidden=true;button.disabled=true;
        label.textContent='Automatisch erkannt · SLOT '+(row.slot+1);label.append(select);
        detail.textContent='Diese Spule folgt ihrer Kennung auch beim Slotwechsel. Keine feste Zuordnung nötig.';
      }else if(linkedHere&&!assigned){
        select.disabled=true;button.hidden=true;button.disabled=true;
        detail.textContent='Kennung bereits verknüpft. Für die Erkennung müssen Drucker und Spulenbestand aktuell und ohne Konflikt sein.';
      }
      if(assigned&&linkedIds.has(assigned)){
        select.value='';for(const option of select.options)if(option.value)option.disabled=true;
        button.textContent='Alte feste Zuordnung lösen';
        detail.textContent='Diese feste Bindung kann die Erkennung nach einem Slotwechsel blockieren. Die Kennungsverknüpfung bleibt beim Lösen erhalten.';
      }
      const messages={stale:'Kennung derzeit nicht aktuell.',empty:'Steckplatz leer.',no_sku:'Keine nutzbare Spulenkennung gemeldet.',unknown:'Kennung noch nicht verknüpft.',duplicate:'Kennung mehrfach erkannt. Keine eindeutige Spule.',conflict:'Kennung und manuelle Zuordnung widersprechen sich. Bitte Zuordnung prüfen.',inventory_unavailable:'Verknüpfter Bestand nicht aktuell oder Spule nicht verfügbar.',recognized:'Spule anhand ihrer Kennung wiedererkannt.'};
      const note=document.createElement('p');note.className='spool-identity';
      const status=!fresh?'stale':(detected?.status==='recognized'&&!current?'inventory_unavailable':detected?.status);
      note.textContent=detected?((detected.sku?'Kennung: '+detected.sku+' · ':'')+(messages[status]||'Kennung prüfen.')):'Spulenkennung wird beim Aktualisieren geprüft.';
      if(detected?.status==='recognized'&&fresh&&current){const spool=state.spools.find(s=>s.id===detected.spool_id);if(spool)note.textContent+=' '+caption(spool);}
      card.append(note);
      if(detected?.status==='unknown'&&fresh&&detected.sku){
        const confirm=document.createElement('label'),check=document.createElement('input'),link=document.createElement('button');
        check.type='checkbox';confirm.append(check,document.createTextNode(' Diese Kennung gehört nur zu dieser Spule, z. B. durch ReSpool. Eine normale Herstellerkennung kann für mehrere Spulen gleich sein.'));
        link.type='button';link.className='timeline-button';link.textContent='Kennung mit ausgewählter Spule verknüpfen';link.disabled=busy||!current;
        link.addEventListener('click',()=>{if(!check.checked||!select.value){$('spools-message').textContent='Bitte eine Spule auswählen und die eindeutige Kennung bestätigen.';return;}request({action:'link_sku',ip:row.ip,slot:row.slot,sku:detected.sku,spool_id:Number(select.value),unique_confirmed:true});});
        card.append(confirm,link);
      }
    }
    for(const [sku,id] of Object.entries(state.sku_links||{})){
      const card=document.createElement('div'),text=document.createElement('p'),remove=document.createElement('button');card.className='spool-assignment';
      text.textContent='Gespeicherte Kennung: '+sku+' → Spule #'+id;
      remove.type='button';remove.className='timeline-button';remove.textContent='Kennung lösen';remove.disabled=busy;
      remove.addEventListener('click',()=>request({action:'link_sku',sku,spool_id:null}));card.append(text,remove);target.append(card);
    }
  }
  async function request(body){
    if(busy)return;busy=true;$('spools-connect').disabled=true;$('spools-refresh').disabled=true;$('spools-message').textContent='Wird geprüft …';draw();
    try{
      state=await window.kobraAuth.spoolRequest(body);$('spools-url').value=state.url;
      $('spools-message').textContent=state.error||(state.configured?(state.limit_reached?'Bis zu 1000 Spulen geladen; der Bestand kann größer sein.':state.spools.length+' Spulen im Bestand. Keine automatische Verbrauchsbuchung.'):'Noch nicht verbunden. Trage deine Spoolman-Adresse ein.');
    }catch(error){$('spools-message').textContent=error.message||'Bitte erneut versuchen.';}
    finally{busy=false;$('spools-connect').disabled=false;draw();}
  }
  $('spools-open').addEventListener('click',()=>{const open=$('spools-content').hidden;$('spools-content').hidden=!open;$('spools-open').setAttribute('aria-expanded',String(open));$('spools-open').textContent=open?'Schließen':'Einrichten';if(open)request();});
  $('spools-form').addEventListener('submit',event=>{event.preventDefault();request({action:'configure',url:$('spools-url').value});});
  $('spools-refresh').addEventListener('click',()=>request({action:'refresh'}));
  function setPrinters(values,ip){
    printers=values;selected=ip;
    // Called only after the authenticated status response. Load the saved link once.
    if(!loaded){loaded=true;request();}
    const fresh=!!(state?.inventory_current&&state.checked_at!==null&&Date.now()/1000-state.checked_at<=60);
    const next=JSON.stringify([ip,fresh,values.map(p=>[p.ip,p.connection,typeof p.section_age_s?.ace==='number'&&p.section_age_s.ace<=60,(p.data?.ace_slots||[]).map(s=>[s.global_index??s.index,s.sku,s.edit_status])])]);
    if(next!==signature||fresh!==shownFresh){signature=next;if(!$('spools-content').hidden){draw();if(state&&!busy)request();}}
  }
  return {setPrinters,caption};
})();
