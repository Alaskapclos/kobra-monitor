/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraReprints=(()=>{
  const $=id=>document.getElementById(id),panel=$('reprint-panel');
  if(!panel)return {};
  const node=(tag,value)=>{const n=document.createElement(tag);if(value)n.textContent=value;return n;};
  const active=new Set(['prepared','uploading','uploaded','starting','awaiting','unknown']);
  let job=null,info=null,targets=[],operation=null,busy=false,generation=0,timer=null;
  const say=value=>{$('reprint-message').textContent=value;};
  const api=body=>window.kobraAuth.reprintRequest(body);
  function key(){const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;const h=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;}
  // Advisory only: slicer estimates against current, explicitly resolved book weights.
  function stockAssessment(materials,assignments,target,reader){
    const groups=new Map(),unknown=[];
    for(const material of materials){
      const choice=assignments.find(a=>a.paint_index===material.paint_index);
      const slot=target?.slots?.find(s=>s.global_index===choice?.slot);
      if(!slot){unknown.push('Datei-Filament '+(material.paint_index+1)+': ACE-Slot noch auswählen.');continue;}
      const stock=reader(target.ip,slot),need=material.estimated_g;
      if(!stock||!Number.isInteger(stock.id)||stock.id<=0||!Number.isFinite(stock.grams)||stock.grams<0){unknown.push('Slot '+(choice.slot+1)+': Restgewicht oder eindeutige Spulenzuordnung nicht aktuell.');continue;}
      let group=groups.get(stock.id);
      if(!group){group={spool:stock.id,grams:stock.grams,needed:0,slots:[]};groups.set(stock.id,group);}
      group.grams=Math.min(group.grams,stock.grams);
      if(!group.slots.includes(choice.slot+1))group.slots.push(choice.slot+1);
      if(typeof need!=='number'||!Number.isFinite(need)||need<=0){group.unknownNeed=true;unknown.push('Datei-Filament '+(material.paint_index+1)+': kein belastbarer Slicerbedarf.');continue;}
      group.needed+=need;
    }
    const rows=Array.from(groups.values()).map(g=>({...g,status:g.unknownNeed||!Number.isFinite(g.needed)?'unknown':g.grams+1e-6>=g.needed?'enough':'short',missing:Math.max(0,g.needed-g.grams)}));
    return {rows,unknown};
  }
  function refreshStock(){
    const host=$('reprint-stock');if(!host)return;
    if(panel.hidden||!info){host.hidden=true;host.replaceChildren();host.stockSignature='';return;}
    const target=targets.find(t=>t.ip===$('reprint-target')?.value);
    if(!target){host.hidden=true;host.replaceChildren();host.stockSignature='';return;}host.hidden=false;
    const assignments=Array.from($('reprint-choices').querySelectorAll('[data-paint]')).map(s=>({paint_index:Number(s.dataset.paint),slot:s.value===''?null:Number(s.value)}));
    const report=stockAssessment(info.materials,assignments,target,(ip,slot)=>window.kobraSpools?.remainingForSelection?.(ip,slot));
    const signature=JSON.stringify([target.ip,report]);if(host.stockSignature===signature)return;host.stockSignature=signature;host.replaceChildren();
    host.append(node('strong','Materialvorrat · Spoolman-Buchbestand'));
    const grams=n=>n.toLocaleString('de-DE',{maximumFractionDigits:2});
    for(const r of report.rows){
      const line=node('p',`Spule #${r.spool} · Slot ${r.slots.join(', ')}: ${r.status==='unknown'?'Bedarf unvollständig':'ca. '+grams(r.needed)+' g Bedarf'} / ${grams(r.grams)} g Rest — ${r.status==='unknown'?'nicht beurteilbar':r.status==='enough'?'laut Buchbestand ausreichend':'es fehlen ca. '+grams(r.missing)+' g'}`);
      line.className='reprint-stock-'+r.status;host.append(line);
    }
    for(const text of report.unknown)host.append(node('p','Nicht beurteilbar · '+text));
    host.append(node('p','Slicer-Schätzung und gebuchter Restbestand; keine Verbrauchsmessung. Material und tatsächliche Spule vor dem Start prüfen.'));
  }
  function storage(value){try{if(value)sessionStorage.setItem('kobra-reprint-id',value);else sessionStorage.removeItem('kobra-reprint-id');}catch{/* The server receipt remains authoritative without browser storage. */}}
  function reveal(){panel.hidden=false;$('reprint-title').focus();panel.scrollIntoView({behavior:'smooth',block:'start'});}
  function checks(){return ['reprint-bed','reprint-material','reprint-nozzle'].every(id=>$(id).checked);}
  function paint(){
    const state=operation?.state;
    const canChoose=!busy&&(!operation||!active.has(state));
    for(const input of $('reprint-choices').querySelectorAll('select'))input.disabled=!canChoose;
    $('reprint-prepare').hidden=!!operation&&active.has(state);
    $('reprint-prepare').disabled=!canChoose||!info||!$('reprint-target')?.value;
    $('reprint-transfer').hidden=state!=='prepared';$('reprint-transfer').disabled=busy;
    $('reprint-cancel').hidden=!['prepared','uploaded'].includes(state);$('reprint-cancel').disabled=busy;
    $('reprint-start-form').hidden=state!=='uploaded';
    $('reprint-start').disabled=busy||state!=='uploaded'||!checks();
    refreshStock();
    if(operation){
      $('reprint-file').textContent=operation.source_filename+' · Zieldrucker: '+operation.ip;
      const assignments=operation.assignments||[];
      $('reprint-summary').textContent=assignments.map(a=>{
        const s=(operation.selected_slots||[]).find(s=>s.global_index===a.slot);
        return `Datei-Filament ${a.paint_index+1} → ACE-Slot ${a.slot+1}${s?' · '+s.type+(s.sku?' · '+s.sku:''):''}`;
      }).join(' / ');
      $('reprint-nozzle-text').textContent=`Die eingebaute Düse hat ${operation.nozzle_mm.toLocaleString('de-DE')} mm und passt zum geslicten Profil.`;
    }
  }
  function store(result){
    if(result.state==='uploaded'&&operation?.state!=='uploaded')for(const id of ['reprint-bed','reprint-material','reprint-nozzle'])$(id).checked=false;
    operation=result;storage(active.has(result.state)?result.id:null);say(result.detail);paint();
    if(result.state==='confirmed')window.dispatchEvent(new Event('kobra-report-changed'));
    schedule();
  }
  function schedule(){
    clearTimeout(timer);timer=null;
    if(operation&&active.has(operation.state))timer=setTimeout(poll,2000);
  }
  async function poll(){
    if(busy||!operation||!window.kobraAuth.authenticated){schedule();return;}
    const current=generation,id=operation.id;
    try{const result=await api({action:'status',id});if(current===generation&&operation?.id===id)store(result);}
    catch(error){if(current===generation){say(error.message+' Keine Aktion wird automatisch wiederholt.');schedule();}}
  }
  async function run(body){
    if(busy)return;busy=true;paint();const current=generation;
    try{const result=await api(body);if(current===generation)store(result);}
    catch(error){
      if(current===generation){
        say(error.message+(body.action==='transfer'||body.action==='start'?' Ergebnis im Status prüfen; nicht erneut automatisch gesendet.':''));
        if(operation&&(body.action==='transfer'||body.action==='start')){operation={...operation,state:'unknown'};storage(operation.id);schedule();}
      }
    }finally{if(current===generation){busy=false;paint();schedule();}}
  }
  function choices(){
    const host=$('reprint-choices');host.replaceChildren();
    const label=node('label','Zieldrucker'),select=node('select');select.id='reprint-target';select.append(new Option('Drucker ausdrücklich auswählen',''));
    for(const target of targets){const option=new Option(`${target.name} · ${target.ip} · ${target.reason}`,target.ip);option.disabled=!target.enabled;select.append(option);}
    label.append(select);host.append(label);
    if(info.slicer_warnings?.length){
      const names={bed_temperature_too_high_than_filament:'Die gespeicherte Betttemperatur liegt über der Filamentempfehlung.',the_actual_nozzle_hrc_smaller_than_the_required_nozzle_hrc:'Der Slicer meldet eine möglicherweise zu geringe Düsenhärte für das Material.'};
      const list=node('ul');for(const warning of info.slicer_warnings)list.append(node('li',names[warning.message]||warning.message||warning.code));host.append(node('p','Gespeicherte Slicer-Warnungen:'),list);
    }
    const materials=node('div'),stock=node('div');stock.id='reprint-stock';stock.className='reprint-stock';stock.setAttribute('role','status');stock.setAttribute('aria-live','polite');host.append(materials,stock);
    select.addEventListener('change',()=>{
      materials.replaceChildren();const target=targets.find(t=>t.ip===select.value);
      for(const material of info.materials){
        const label=node('label',`Datei-Filament ${material.paint_index+1}: ${material.type} · ${material.color} · ca. ${material.estimated_g.toLocaleString('de-DE')} g`);
        const slot=node('select');slot.dataset.paint=String(material.paint_index);slot.append(new Option('ACE-Slot ausdrücklich auswählen',''));
        for(const value of target?.slots||[]){
          if(value.status!==5||!value.type||value.edit_status===2)continue;
          slot.append(new Option(`Slot ${value.global_index+1} · ${value.type}${value.sku?' · '+value.sku:''}`,String(value.global_index)));
        }
        slot.addEventListener('change',refreshStock);label.append(slot);materials.append(label);
      }
      paint();
    });
    if(!targets.some(t=>t.enabled))host.append(node('p','Für Archiv-Druckstarts ist noch kein Drucker freigegeben. Die vorhandene Beobachtung und Steuerung bleiben unabhängig davon nutzbar.'));
  }
  async function open(source){
    reveal();
    if(busy||operation&&active.has(operation.state)){say('Ein Archivvorgang ist noch offen. Bitte dessen Ergebnis prüfen oder die Vorbereitung verwerfen.');return;}
    const current=++generation;clearTimeout(timer);job=source;info=null;operation=null;busy=true;paint();
    $('reprint-file').textContent=source.filename;say('Originaldatei und Druckdaten werden geprüft …');$('reprint-choices').replaceChildren();
    try{
      const catalog=await api();if(current!==generation)return;targets=catalog.targets;
      const result=await api({action:'check',job:source.id,sha256:source.sha256});if(current!==generation)return;
      info=result;choices();say(`Original geprüft · Düse ${info.nozzle_mm.toLocaleString('de-DE')} mm. ${info.slicer_warning_count?info.slicer_warning_count+' gespeicherte Slicer-Warnung(en); vor Wiederholung beachten.':'Bitte Drucker und ACE-Slots auswählen.'}`);
    }catch(error){if(current===generation)say(error.message);}
    finally{if(current===generation){busy=false;paint();}}
  }
  async function forFile(file){
    try{const catalog=await api();const source=catalog.jobs.find(j=>j.sha256===file.sha256);if(!source){reveal();say('Dieser Originaldatei ist kein erfolgreich abgeschlossener Auftrag zugeordnet.');return;}await open(source);}
    catch(error){reveal();say(error.message);}
  }
  function button(source,isFile=false){const b=node('button','Druck wiederholen');b.type='button';b.className='timeline-button';b.addEventListener('click',()=>isFile?forFile(source):open(source));return b;}
  $('reprint-last').addEventListener('click',async()=>{try{const catalog=await api();if(!catalog.jobs.length){reveal();say('Noch kein erfolgreich abgeschlossener Auftrag mit zugeordnetem Original verfügbar.');return;}await open(catalog.jobs[0]);}catch(error){reveal();say(error.message);}});
  $('reprint-prepare').addEventListener('click',()=>{
    const assignments=Array.from($('reprint-choices').querySelectorAll('[data-paint]')).map(s=>({paint_index:Number(s.dataset.paint),slot:s.value===''?null:Number(s.value)}));
    if(assignments.some(a=>a.slot===null)||!assignments.length){say('Bitte jedem Datei-Filament einen ACE-Slot zuordnen.');return;}
    run({action:'prepare',job:job.id,sha256:job.sha256,ip:$('reprint-target').value,assignments,request_id:key()});
  });
  $('reprint-transfer').addEventListener('click',()=>{if(operation?.state==='prepared')run({action:'transfer',id:operation.id,token:operation.token});});
  $('reprint-cancel').addEventListener('click',()=>{if(operation)run({action:'cancel',id:operation.id});});
  $('reprint-start-form').addEventListener('submit',event=>{event.preventDefault();if(operation?.state==='uploaded'&&checks())run({action:'start',id:operation.id,token:operation.token,bed_clear:true,material_ready:true,nozzle_mm:operation.nozzle_mm});});
  for(const id of ['reprint-bed','reprint-material','reprint-nozzle'])$(id).addEventListener('change',paint);
  $('reprint-close').addEventListener('click',()=>{panel.hidden=true;});
  function resetSession(){generation++;clearTimeout(timer);timer=null;operation=null;info=null;job=null;busy=false;panel.hidden=true;refreshStock();}
  async function resume(){
    if(!window.kobraAuth.authenticated)return;
    let id;try{id=sessionStorage.getItem('kobra-reprint-id');}catch{return;}
    if(!id)return;const current=generation;
    try{const result=await api({action:'status',id});if(current!==generation)return;job={id:result.source_job,sha256:result.sha256,filename:result.source_filename};store(result);reveal();}
    catch(error){if(current===generation){storage(null);reveal();say(error.message+' Bitte den aktuellen Druckerstatus prüfen.');}}
  }
  window.kobraAuth.ready.then(resume);window.addEventListener('kobra-authenticated',resume);
  window.addEventListener('kobra-spools-changed',refreshStock);
  return {open,button,resetSession,refreshStock,stockAssessment};
})();
