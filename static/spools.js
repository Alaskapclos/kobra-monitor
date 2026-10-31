/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraSpools=(()=>{
  const $=id=>document.getElementById(id);
  let state=null,printers=[],selected=null,busy=false,signature='',shownFresh=null;
  function caption(spool){
    const weight=typeof spool.remaining_weight==='number'&&Number.isFinite(spool.remaining_weight)?Math.round(spool.remaining_weight)+' g Rest in Spoolman':'Restgewicht unbekannt';
    return '#'+spool.id+' · '+[spool.vendor,spool.name,spool.material].filter(Boolean).join(' · ')+' · '+weight;
  }
  function draw(){
    const target=$('spools-assignments');target.replaceChildren();if(!state)return;
    $('spools-refresh').disabled=busy||!state.configured;
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
      const empty=document.createElement('option');empty.value='';empty.textContent='Keine Spule zugeordnet';select.append(empty);
      const assigned=mappings[row.ip]?.[String(row.slot)];
      for(const spool of state.spools){const option=document.createElement('option');option.value=String(spool.id);option.textContent=caption(spool);select.append(option);}
      if(assigned&&!state.spools.some(s=>s.id===assigned)){const option=document.createElement('option');option.value=String(assigned);option.textContent='#'+assigned+' · Nicht im aktuellen Bestand';select.append(option);}
      select.value=assigned?String(assigned):'';
      // Clearing a mapping must work even if Spoolman is down or the printer is removed.
      if(!current||row.missing)for(const option of select.options)if(option.value&&Number(option.value)!==assigned)option.disabled=true;
      select.disabled=busy;
      button.className='timeline-button';button.type='button';button.textContent='Zuordnen';button.disabled=busy;
      button.addEventListener('click',()=>request({action:'assign',ip:row.ip,slot:row.slot,spool_id:select.value?Number(select.value):null}));
      label.append(select);detail.textContent=assigned?(state.spools.find(s=>s.id===assigned)?caption(state.spools.find(s=>s.id===assigned)):'Zugeordnete Spule #'+assigned+' derzeit nicht verfügbar.'):'Zuordnung wird nur im Monitor gespeichert.';
      card.append(label,button,detail);target.append(card);
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
    const fresh=!!(state?.inventory_current&&state.checked_at!==null&&Date.now()/1000-state.checked_at<=60);
    const next=JSON.stringify([ip,fresh,values.map(p=>[p.ip,(p.data?.ace_slots||[]).map(s=>s.global_index??s.index)])]);
    if(next!==signature||fresh!==shownFresh){signature=next;if(!$('spools-content').hidden)draw();}
  }
  return {setPrinters,caption};
})();
