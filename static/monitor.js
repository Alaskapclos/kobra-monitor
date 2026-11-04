/* Local UI: GET status and stored reports; no device-control routes. */
'use strict';
const $ = id => document.getElementById(id);
const number = x => typeof x === 'number' && Number.isFinite(x);
const value = (x,suffix='') => number(x) ? `${Math.round(x)}${suffix}` : '—';
const duration = seconds => {
  if (!number(seconds) || seconds < 0) return '—';
  const minutes = Math.round(seconds/60);
  return minutes >= 60 ? `${Math.floor(minutes/60)} h ${minutes%60} min` : `${minutes} min`;
};
const ageText = seconds => !number(seconds) ? 'Noch keine Daten' : seconds < 3 ? 'Gerade eben' : seconds < 60 ? `Vor ${Math.floor(seconds)} s` : `Vor ${Math.floor(seconds/60)} min`;
const fileName = name => typeof name === 'string' && name.length ? name.split('/').pop() : 'Keine Datei gemeldet';
let busy = false;
let lastResponse = null;
let lastFetchAt = 0;
let requestFailed = false;
let selectedIp = null;
let historySignature = null;
let timelineJob = null;
let timelineIp = null;
let timelineRequest = 0;
let timelineEnd = null;
let archiveIp = null;
let archivePage = 0;
let archiveRequest = 0;
let archiveDebounce = null;
const printerButtons = new Map();
const stateNames = {standby:'Bereit',printing:'Druckt',paused:'Pausiert',complete:'Abgeschlossen',error:'Störung',preheating:'Heizt auf',auto_leveling:'Vorbereitung',checking:'Vorbereitung',init:'Vorbereitung',preparing:'Vorbereitung',pausing:'Wird pausiert …',resuming:'Wird fortgesetzt …',stopping:'Wird abgebrochen …',cancelled:'Abgebrochen'};

function renderSlots(data, seen, stale) {
  const area = $('slots');
  area.replaceChildren();
  if (!seen || !data || !Array.isArray(data.ace_slots) || !data.ace_slots.length) {
    const empty = document.createElement('div'); empty.className = 'empty-state';
    empty.textContent = seen ? 'Keine ACE-Slots vom Drucker gemeldet.' : 'Warte auf Filamentdaten vom Drucker.';
    area.append(empty); return;
  }
  for (const slot of data.ace_slots) {
    const active = slot.global_index === data.loaded_slot;
    const card = document.createElement('div'); card.className = `slot${active?' active':''}${stale?' stale':''}`;
    const top = document.createElement('div'); top.className = 'slot-top';
    const label = document.createElement('span'); label.className = 'slot-number'; label.textContent = `SLOT ${Number(slot.global_index??slot.index)+1}`; top.append(label);
    if (active) { const tag = document.createElement('span'); tag.className='slot-badge'; tag.textContent=stale?'Zuletzt geladen':'Geladen'; top.append(tag); }
    const spool = document.createElement('div'); spool.className='spool';
    const rgb = Array.isArray(slot.color) && slot.color.length>=3 && slot.color.slice(0,3).every(x=>number(x)&&x>=0&&x<=255) ? slot.color.slice(0,3) : [180,190,166];
    spool.style.borderColor = `rgb(${rgb.join(',')})`;
    const material = document.createElement('div'); material.className='slot-material'; material.textContent = slot.type || 'Nicht zugeordnet';
    const color = document.createElement('div'); color.className='slot-color'; color.textContent = '#'+rgb.map(x=>Math.round(x).toString(16).padStart(2,'0')).join('').toUpperCase();
    const remaining = document.createElement('div'); remaining.className='slot-remaining';
    const amount = document.createElement('strong'); const percent = number(slot.consumables_percent) ? Math.max(0,Math.min(100,slot.consumables_percent)) : null;
    amount.textContent = percent===null?'—':Math.round(percent); const unit = document.createElement('span'); unit.textContent = percent===null?'keine Angabe':'% Restmenge'; remaining.append(amount,unit);
    const track = document.createElement('div'); track.className='slot-bar'; const fill=document.createElement('div'); fill.style.width=`${percent??0}%`; track.append(fill);
    card.append(top,spool,material,color,remaining,track); area.append(card);
  }
}

function renderDeviceStatus(snapshot, extraAge, connection) {
  const readings=snapshot.device_status||{}, limit=number(snapshot.stale_after_s)?snapshot.stale_after_s:90;
  const modes={1:'Silent',2:'Standard',3:'Sport'};
  for(const key of ['fan_speed','aux_fan_speed','box_fan_level','light_on','speed_mode']) {
    const target=$('device-'+key), stamp=$('device-'+key+'-age');if(!target||!stamp)continue;
    const reading=readings[key], valid=reading&&number(reading.age_s)&&reading.age_s>=0&&
      (key==='light_on'?typeof reading.value==='boolean':number(reading.value));
    const track=$('device-'+key+'-track'), fill=$('device-'+key+'-bar');
    if(track){track.hidden=true;if(fill)fill.style.width='0%';}
    const light=key==='light_on'?$('device-light-icon'):null;if(light)light.dataset.state='unknown';
    if(!valid){target.textContent='Nicht gemeldet';stamp.textContent='';target.classList.toggle('device-reading-stale',false);continue;}
    const age=reading.age_s+extraAge, old=connection!=='online'||age>limit||reading.current_session===false;
    const v=reading.value;
    target.textContent=key==='light_on'?(v?'An':'Aus'):key==='speed_mode'?(modes[v]||`Unbekannter Modus (${v})`):key==='box_fan_level'?`Stufe ${v} / 100`:`${v} %`;
    stamp.textContent=(old?'Veraltet · ':'')+ageText(age);target.classList.toggle('device-reading-stale',old);
    if(light)light.dataset.state=old?'stale':v?'on':'off';
    if(track&&fill&&!old&&v>=0&&v<=100){fill.style.width=`${v}%`;track.hidden=false;}
  }
}

function renderPrinter(snapshot) {
  const extraAge = Math.max(0,(Date.now()-lastFetchAt)/1000);
  const ages = snapshot.section_age_s || {};
  const limit=number(snapshot.stale_after_s)&&snapshot.stale_after_s>=0?snapshot.stale_after_s:90;
  const sectionAge = name => number(ages[name])&&ages[name]>=0 ? ages[name]+extraAge : null;
  const seen = name => number(sectionAge(name));
  const stale = name => connection!=='online' || !seen(name) || sectionAge(name)>limit;
  const data = snapshot.data || {};
  const age = number(snapshot.age_s)?snapshot.age_s+extraAge:null;
  let connection = snapshot.connection;
  if (connection==='online' && number(age) && age>limit) connection='stale';
  if (requestFailed || extraAge>10) connection='offline';
  renderDeviceStatus(snapshot,extraAge,connection);
  window.kobraLightControls?.render(snapshot,extraAge,connection);
  window.kobraFanControls?.render(snapshot,extraAge,connection);
  window.kobraSpeedControls?.render(snapshot,extraAge,connection);
  window.kobraTemperatureControls?.render(snapshot,extraAge,connection);
  window.kobraPrintControls?.render(snapshot,extraAge,connection);
  window.kobraMotionControls?.render(snapshot,extraAge,connection);
  const names = {online:'Verbunden',connecting:'Verbinden',offline:'Offline',stale:'Daten veraltet'};
  const pill=$('connection-pill'); pill.className=`connection-pill ${connection}`; pill.querySelector('span').textContent=names[connection]||'Verbinden';
  $('printer-name').textContent=data.printer_name||data.model_name||'Anycubic Kobra S1';
  $('printer-ip').textContent=`${snapshot.ip} · LAN`;
  const banner=$('connection-banner');
  banner.hidden=connection==='online';
  banner.textContent=requestFailed||extraAge>10 ? 'Der lokale Monitor ist nicht erreichbar. Letzte bekannte Werte werden angezeigt. Starte den Monitor bei Bedarf erneut.' : connection==='stale' ? 'Die Verbindung liefert keine frischen Daten. Angezeigte Werte sind veraltet; die Verbindung wird automatisch erneuert.' : snapshot.message || 'Verbindung zum Drucker wird aufgebaut. Messwerte erscheinen, sobald sie eintreffen.';
  const knownPrint=seen('print');
  const active=knownPrint && ['printing','paused','preheating','auto_leveling','checking','init','preparing','pausing','resuming','stopping'].includes(data.print_state);
  const advancing=!stale('print')&&['printing','paused'].includes(data.print_state);
  $('print-state').textContent=!knownPrint?'Wird verbunden…':stale('print')?'Status veraltet':stateNames[data.print_state]||'Status unbekannt';
  $('print-subtitle').textContent=!knownPrint?'Warte auf den ersten Druckerstatus.':stale('print')?`Letzter bekannter Druckerstatus: ${stateNames[data.print_state]||'unbekannt'}.`:active?'Druckdaten direkt aus deinem lokalen Netzwerk.':data.print_state==='error'?'Der Drucker meldet eine Störung.':data.print_state==='standby'?'Kein aktiver Druck. Dein Drucker ist im Leerlauf.':'Letzter gemeldeter Druckerstatus.';
  $('remaining').textContent=advancing?duration(data.remain_time):'—';
  $('layer').textContent=advancing&&number(data.curr_layer)&&number(data.total_layers)?`${data.curr_layer} / ${data.total_layers}`:'—';
  const progress=advancing&&number(data.progress)&&data.progress>=0&&data.progress<=1?data.progress:null;
  $('progress-value').textContent=progress===null?'—':`${Math.round(progress*100)}%`;
  $('progress-caption').textContent=stale('print')?'Keine aktuellen Druckdaten':advancing?'Fortschritt':['pausing','resuming','stopping'].includes(data.print_state)?'Rückmeldung wird abgewartet':active?'Vorbereitung':knownPrint?'Kein aktiver Druck':'Kein Messwert';
  $('progress-circle').setAttribute('stroke-dashoffset',String(414.69*(1-(progress??0))));
  const previous=snapshot.last_project;
  $('file-label').textContent=active?(stale('print')?'ZULETZT GEMELDETE DRUCKDATEI':'AKTUELLE DRUCKDATEI'):previous?(previous.state==='finished'?'ZULETZT ABGESCHLOSSEN':'LETZTER DRUCK'):'DRUCKDATEI';
  $('filename').textContent=active?fileName(data.filename):previous?fileName(previous.filename):'Kein aktiver Druckauftrag.';
  $('print-freshness').textContent=seen('print')?`${stale('print')?'Veraltet · ':''}${ageText(sectionAge('print'))}`:'Warte auf Druckerstatus';
  for (const [prefix,max] of [['nozzle',320],['bed',120]]) {
    const current=seen('temperature')?data[`${prefix}_temp`]:null;
    const target=seen('temperature')?data[`${prefix}_target`]:null;
    $(prefix+'-temp').textContent=value(current); $(prefix+'-target').textContent=value(target);
    $(prefix+'-mode').textContent=!seen('temperature')?'—':stale('temperature')?'Letzter bekannter Wert':!number(current)||!number(target)?'—':target===0?'Heizung aus':current<target-3?'Heizt auf':'Sollwert aktiv';
    $(prefix+'-bar').style.width=`${number(current)?Math.max(0,Math.min(100,current/max*100)):0}%`;
  }
  $('temp-freshness').textContent=seen('temperature')?`${stale('temperature')?'Veraltet · ':''}${ageText(sectionAge('temperature'))}`:'Warte auf Temperaturen';
  document.querySelector('.temperatures-card').classList.toggle('is-stale',stale('temperature'));
  const aceSeen=seen('ace');
  $('ace-present').textContent=!aceSeen?'Warte auf ACE':data.ace_units?.length?`${data.ace_units.length} ACE · ${data.ace_slots?.length??0} Slots`:'Keine ACE gemeldet';
  $('ace-freshness').textContent=aceSeen?`${stale('ace')?'Veraltet · ':''}${ageText(sectionAge('ace'))}`:'—';
  renderSlots(data,aceSeen,stale('ace'));
  const climate=data.ace_drying||{};
  $('ace-temp').textContent=aceSeen?value(climate.current_temp,' °C'):'—';
  $('ace-humidity').textContent=aceSeen?value(climate.humidity,' %'):'—';
  $('drying-status').textContent=!aceSeen?'—':climate.status===1?'Trocknung aktiv':'Trocknung aus';
  $('drying-remaining').textContent=aceSeen&&climate.status===1?duration(number(climate.remain_time)?climate.remain_time*60:null):'—';
  document.querySelector('.drying-card').classList.toggle('is-stale',stale('ace'));
  $('last-update').textContent=ageText(age);
  $('firmware').textContent=seen('printer')?data.firmware_version||'—':'—';
  document.title=`${names[connection]||'Verbinden'} · Kobra Monitor`;
}

let draggedPrinter=null,dropPrinter=null,orderSaving=false,pendingOrder=null,suppressPickerClickUntil=0;
function reorderedIps(ips,from,to){
  if(from===to||!ips.includes(from)||!ips.includes(to))return [...ips];
  const result=ips.filter(ip=>ip!==from);result.splice(ips.indexOf(to),0,from);return result;
}
function clearPrinterDrag(){
  draggedPrinter=null;dropPrinter=null;
  for(const button of printerButtons.values())button.classList.remove('dragging','drop-target');
}
async function movePrinter(from,to){
  if(orderSaving||!lastResponse)return;
  const ips=pendingOrder||lastResponse.ips||[];const next=reorderedIps(ips,from,to);
  if(next.every((ip,i)=>ip===ips[i]))return;
  orderSaving=true;pendingOrder=next;
  $('printer-order-status').textContent='Reihenfolge wird gespeichert …';
  render(lastResponse);
  try{
    const saved=await window.kobraAuth.reorder(next);
    pendingOrder=saved;
    $('printer-order-status').textContent='Reihenfolge gespeichert.';
  }catch(error){
    pendingOrder=null;$('printer-order-status').textContent=error.message||'Reihenfolge nicht gespeichert. Bitte erneut versuchen.';
  }finally{orderSaving=false;render(lastResponse);}
}
function bindPrinterDrag(button,ip){
  button.draggable=false;button.dataset.ip=ip;
  button.setAttribute('aria-describedby','printer-order-status');
  let pointerStart=null,moved=false;
  button.addEventListener('keydown',event=>{
    if(!event.altKey||!['ArrowLeft','ArrowUp','ArrowRight','ArrowDown'].includes(event.key))return;
    event.preventDefault();const ips=lastResponse?.ips||[],index=ips.indexOf(ip);
    const target=index+(['ArrowLeft','ArrowUp'].includes(event.key)?-1:1);
    if(target>=0&&target<ips.length)movePrinter(ip,ips[target]);
  });
  button.addEventListener('pointerdown',event=>{
    if(event.button!==0||orderSaving||(event.pointerType==='touch'&&!event.target.closest('.picker-grip')))return;
    pointerStart=[event.clientX,event.clientY];moved=false;draggedPrinter=ip;dropPrinter=null;
    button.setPointerCapture(event.pointerId);
  });
  button.addEventListener('pointermove',event=>{
    if(draggedPrinter!==ip||!pointerStart)return;
    if(!moved&&Math.hypot(event.clientX-pointerStart[0],event.clientY-pointerStart[1])<8)return;
    moved=true;button.classList.add('dragging');event.preventDefault();
    const target=document.elementFromPoint(event.clientX,event.clientY)?.closest('.printer-picker');
    dropPrinter=target?.dataset.ip||null;
    for(const item of printerButtons.values())item.classList.toggle('drop-target',item===target&&dropPrinter!==ip);
  });
  button.addEventListener('pointerup',event=>{
    if(draggedPrinter!==ip)return;
    const target=dropPrinter,wasMoved=moved;pointerStart=null;moved=false;clearPrinterDrag();
    if(wasMoved){event.preventDefault();suppressPickerClickUntil=Date.now()+300;if(target)movePrinter(ip,target);}
  });
  button.addEventListener('pointercancel',()=>{pointerStart=null;moved=false;clearPrinterDrag();});
  button.addEventListener('lostpointercapture',()=>{pointerStart=null;moved=false;if(draggedPrinter===ip)clearPrinterDrag();});
}

// A card only calls values current when that section has fresh observations.
function printerOverview(printer,extraAge=0,unavailable=false){
  const limit=number(printer.stale_after_s)?printer.stale_after_s:90;
  const ages=printer.section_age_s||{},data=printer.data||{};
  let connection=printer.connection;
  if(connection==='online'&&number(printer.age_s)&&printer.age_s+extraAge>limit)connection='stale';
  if(unavailable||extraAge>10)connection='offline';
  const fresh=section=>connection==='online'&&number(ages[section])&&ages[section]>=0&&ages[section]+extraAge<=limit;
  const printFresh=fresh('print'),temperatureFresh=fresh('temperature');
  const phase=data.print_state;
  const advancing=printFresh&&['printing','paused'].includes(phase);
  const progress=advancing&&number(data.progress)&&data.progress>=0&&data.progress<=1?Math.round(data.progress*100):null;
  const remaining=advancing?duration(data.remain_time):'—';
  const nozzle=temperatureFresh?value(data.nozzle_temp,' °C'):'—';
  const bed=temperatureFresh?value(data.bed_temp,' °C'):'—';
  const state=printFresh?(stateNames[phase]||'Status unbekannt'):connection==='connecting'?'Warte auf Druckerdaten':'Keine aktuellen Druckdaten';
  const detail=state+(progress!==null?` · ${progress} %`:'');
  const note=connection==='offline'?'Verbindung unterbrochen · Messwerte ausgeblendet':connection==='connecting'?'Warte auf erste Messwerte':!printFresh?'Druckstatus fehlt oder ist veraltet':!temperatureFresh?'Temperaturwerte fehlen oder sind veraltet':ageText(ages.print+extraAge);
  return {connection,state,detail,progress,remaining,nozzle,bed,note,
    attention:connection!=='online'||!printFresh||!temperatureFresh};
}
function createPickerOverview(button){
  const overview=document.createElement('span');overview.className='picker-overview';
  const track=document.createElement('span'),fill=document.createElement('span');track.className='picker-progress-track';fill.className='picker-progress-fill';track.setAttribute('aria-hidden','true');track.append(fill);
  const metrics=document.createElement('span');metrics.className='picker-metrics';
  for(const [key,label] of [['remaining','Restzeit ca.'],['nozzle','Düse'],['bed','Druckbett']]){
    const item=document.createElement('span'),caption=document.createElement('span'),reading=document.createElement('strong');
    item.className='picker-metric';caption.textContent=label;reading.className='picker-'+key;item.append(caption,reading);metrics.append(item);
  }
  const note=document.createElement('span');note.className='picker-freshness';overview.append(track,metrics,note);button.append(overview);
}
function renderPickerOverview(button,view){
  const fill=button.querySelector('.picker-progress-fill');fill.style.width=`${view.progress??0}%`;
  button.querySelector('.picker-progress-track').hidden=view.progress===null;
  for(const key of ['remaining','nozzle','bed'])button.querySelector('.picker-'+key).textContent=view[key];
  button.querySelector('.picker-freshness').textContent=view.note;
  button.classList.toggle('picker-needs-attention',view.attention);
}

function render(snapshot) {
  const lightEnabled=snapshot.controls?.chamber_light===true;
  const fanEnabled=snapshot.controls?.fans===true;
  const motionEnabled=snapshot.controls?.motion===true;
  const printEnabled=snapshot.controls?.print_job===true;
  const temperatureEnabled=snapshot.controls?.temperature===true;
  const speedEnabled=snapshot.controls?.speed_mode===true;
  if($('installation-mode'))$('installation-mode').textContent=motionEnabled?'Manuelle Druckersteuerung freigegeben':printEnabled?'Druckersteuerung freigegeben':temperatureEnabled?'Druckersteuerung freigegeben':speedEnabled?'Druckersteuerung freigegeben':fanEnabled?'Licht-/Lüftersteuerung freigegeben':lightEnabled?'Lichtsteuerung freigegeben':'Drucker nur lesen';
  if($('footer-mode'))$('footer-mode').textContent=motionEnabled?'Manuelle Druckersteuerung freigegeben':printEnabled?'Status und Druckersteuerung':temperatureEnabled?'Status und Druckersteuerung':speedEnabled?'Status und Druckersteuerung':fanEnabled?'Status, Licht und Lüfter':lightEnabled?'Status und Kammerlicht':'Status ohne Eingriff';
  if($('sidebar-mode'))$('sidebar-mode').textContent=motionEnabled?'Manuelle Fahrten und weitere Druckersteuerungen einstellbar.':printEnabled?'Druckaktionen, Licht, Lüfter, Speed Mode und Solltemperaturen einstellbar.':temperatureEnabled?'Licht, Lüfter, Speed Mode und Solltemperaturen einstellbar.':speedEnabled?'Licht, Lüfter und Speed Mode einstellbar.':fanEnabled?'Licht und Lüfter gezielt einstellbar.':lightEnabled?'Kammerlicht direkt schaltbar.':'Ausschließlich lesend.';
  if(!orderSaving&&pendingOrder&&snapshot.ips?.length===pendingOrder.length&&snapshot.ips.every((ip,i)=>ip===pendingOrder[i]))pendingOrder=null;
  window.kobraAuth?.setPrinters(snapshot.ips||[],(snapshot.printers||[]).map(p=>({...p,connection:requestFailed?'offline':p.connection})));
  const source=Array.isArray(snapshot.printers)?snapshot.printers:[snapshot];
  const order=pendingOrder||snapshot.ips||source.map(p=>p.ip);
  const printers=[...source].sort((a,b)=>order.indexOf(a.ip)-order.indexOf(b.ip));
  if (!printers.some(p=>p.ip===selectedIp)) selectedIp=printers[0]?.ip;
  const area=$('printer-switcher');
  const navCount=document.querySelector('.nav-count');
  if(navCount)navCount.textContent=String(printers.length);
  for(const printer of printers) {
    let button=printerButtons.get(printer.ip);
    if(!button) {
      button=document.createElement('button');button.type='button';button.className='printer-picker';
      const grip=document.createElement('span');grip.className='picker-grip';grip.textContent='⠿';grip.setAttribute('aria-hidden','true');
      const identity=document.createElement('span');identity.className='picker-identity';
      const name=document.createElement('strong');name.className='picker-name';
      const address=document.createElement('span');address.className='picker-ip';
      identity.append(name,address);
      const info=document.createElement('span');info.className='picker-info';
      const state=document.createElement('span');state.className='picker-state';
      const detail=document.createElement('span');detail.className='picker-detail';
      info.append(state,detail);button.append(grip,identity,info);createPickerOverview(button);
      bindPrinterDrag(button,printer.ip);
      button.addEventListener('click',()=>{if(Date.now()<suppressPickerClickUntil)return;selectedIp=printer.ip;if(lastResponse)render(lastResponse);});
      printerButtons.set(printer.ip,button);area.append(button);
    }
    const extraAge=Math.max(0,(Date.now()-lastFetchAt)/1000);
    const view=printerOverview(printer,extraAge,requestFailed);
    const labels={online:'Verbunden',connecting:'Verbinden',offline:'Offline',stale:'Veraltet'};
    const name=printer.data?.printer_name||printer.data?.model_name||'Drucker';
    button.classList.toggle('selected',printer.ip===selectedIp);
    button.setAttribute('aria-pressed',String(printer.ip===selectedIp));
    button.querySelector('.picker-name').textContent=name;
    button.querySelector('.picker-ip').textContent=printer.ip;
    const status=button.querySelector('.picker-state');status.className=`picker-state ${view.connection}`;status.textContent=labels[view.connection]||'Verbinden';
    button.querySelector('.picker-detail').textContent=view.detail;
    renderPickerOverview(button,view);
    button.setAttribute('aria-label',`${name}, ${labels[view.connection]||'Verbinden'}, ${view.detail}, Restzeit circa ${view.remaining}, Düse ${view.nozzle}, Druckbett ${view.bed}. Details anzeigen.`);
  }
  for(const [ip,button] of printerButtons) {
    if(!printers.some(p=>p.ip===ip)){button.remove();printerButtons.delete(ip);}
  }
  if(!draggedPrinter){
    const focused=document.activeElement;
    printers.forEach((printer,index)=>{const button=printerButtons.get(printer.ip);if(area.children[index]!==button)area.insertBefore(button,area.children[index]||null);});
    if([...printerButtons.values()].includes(focused)&&document.activeElement!==focused)focused.focus({preventScroll:true});
  }
  area.setAttribute('aria-busy',String(orderSaving));
  $('printer-order-status').hidden=printers.length<2;
  const chosen=printers.find(p=>p.ip===selectedIp);
  if(chosen)renderPrinter(chosen);
  // Cached status keeps aging even while no new response arrives.
  const extraAge=Math.max(0,(Date.now()-lastFetchAt)/1000);
  const spoolPrinters=printers.map(p=>({...p,
    connection:requestFailed||extraAge>10?'offline':p.connection,
    section_age_s:Object.fromEntries(Object.entries(p.section_age_s||{}).map(([key,age])=>[key,number(age)?age+extraAge:age]))}));
  window.kobraSpools?.setPrinters(spoolPrinters,chosen?.ip);
  window.kobraCamera?.setPrinters?.(printers);
  window.kobraCamera?.setPrinter(chosen?.ip,snapshot.camera_available,snapshot.camera_message);
  if(timelineJob && timelineIp!==selectedIp) closeTimeline();
  if(archiveIp!==selectedIp) {
    archiveIp=selectedIp;archivePage=0;historySignature=null;
    $('history-content').replaceChildren();
    for(const key of ['total','completed','active','cancelled'])$('archive-'+key).textContent='—';
    $('history-page').textContent='—';
    refreshArchive();
  }
}

function renderHistory(jobs,ip) {
  window.kobraOrders?.setScope(ip);
  const container=$('history-content');if(!container)return;
  const selected=jobs.filter(job=>job.ip===ip);
  const signature=JSON.stringify([ip,selected.map(({id,filename,state,progress,observed_start,first_seen,ended_at,annotation,report_version})=>({id,filename,state,progress,observed_start,first_seen,ended_at,annotation,report_version}))]);
  if(signature===historySignature)return;
  historySignature=signature;
  container.replaceChildren();
  if(!selected.length) {
    const empty=document.createElement('p');empty.className='empty-state';
    empty.textContent=$('history-search').value.trim() || $('history-filter').value!=='all' ? 'Keine passenden Aufträge. Passe die Suche oder den Statusfilter an.' : 'Noch keine aufgezeichneten Drucke für dieses Gerät.';
    container.append(empty);return;
  }
  const when=seconds=>new Date(seconds*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
  for(const job of selected) {
    const row=document.createElement('div');row.className='history-job';
    const file=document.createElement('div');file.className='history-file';
    const title=document.createElement('strong');title.textContent=fileName(job.filename);
    const coverage=document.createElement('span');coverage.textContent=job.observed_start?'Beginn beobachtet':'Laufenden Druck erkannt';
    file.append(title,coverage);
    const dates=document.createElement('div');dates.className='history-dates';
    dates.textContent=`Erkannt ${when(job.first_seen)}`;
    if(job.ended_at){const end=document.createElement('span');end.textContent=`Ende ${when(job.ended_at)}`;dates.append(end);}
    const state=document.createElement('span');state.className='subtle-pill';
    const labels={completed:'Abgeschlossen',cancelled:'Abgebrochen',unknown_end:'Ende nicht beobachtet'};
    state.textContent=labels[job.state]||stateNames[job.state]||job.state;
    if(!job.ended_at&&number(job.progress))state.textContent+=` · ${Math.round(job.progress)} %`;
    const actions=document.createElement('div');actions.className='history-actions';
    const report=document.createElement('a');report.className='report-link';
    report.textContent='Aufzeichnung als Text';report.href='/api/report?job='+encodeURIComponent(job.id);
    report.setAttribute('download','');
    report.setAttribute('aria-label','Aufzeichnung als Text: '+fileName(job.filename));
    const view=document.createElement('button');view.type='button';view.className='timeline-button';
    view.textContent='Verlauf ansehen';view.dataset.job=job.id;
    view.setAttribute('aria-controls','timeline-card');view.setAttribute('aria-expanded',String(timelineJob===job.id));
    view.addEventListener('click',()=>openTimeline(job));
    window.kobraOrders?.decorate(job,file,actions);
    actions.append(state,view,report);
    row.append(file,dates,actions);container.append(row);
  }
}

async function refresh() {
  if (busy || (window.kobraAuth && !window.kobraAuth.authenticated)) return;
  busy=true; $('refresh').disabled=true;
  try {
    const response=await fetch('/api/status',{cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(response.status===401){window.kobraAuth?.login();return;}
    if (!response.ok) throw new Error('Keine Statusdaten');
    const result=await response.json();
    if (result.read_only!==true && !(result.read_only===false&&(result.controls?.chamber_light===true||result.controls?.fans===true||result.controls?.speed_mode===true||result.controls?.temperature===true||result.controls?.print_job===true||result.controls?.motion===true))) throw new Error('Unbekannter Betriebsmodus');
    lastResponse=result;lastFetchAt=Date.now();requestFailed=false;render(result);
    if(result.report_archive_error)$('reports-message').textContent=result.report_archive_error;
  } catch (_) {
    requestFailed=true;
    if (lastResponse) render(lastResponse);
    else { const banner=$('connection-banner');banner.hidden=false;banner.textContent='Der lokale Monitor ist nicht erreichbar. Die Verbindung wird automatisch erneut geprüft.'; }
  } finally { busy=false;$('refresh').disabled=false; }
}
$('refresh').addEventListener('click',refresh);
if(window.kobraAuth)window.kobraAuth.ready.then(refresh);else refresh();
window.addEventListener('kobra-authenticated',refresh);
window.addEventListener('kobra-configured',()=>{archiveIp=null;refresh();});
setInterval(refresh,2000);
setInterval(()=>{if(lastResponse)render(lastResponse);},1000);

function closeTimeline() {
  timelineJob=null;timelineIp=null;timelineEnd=null;timelineRequest++;
  $('timeline-card').hidden=true;
  document.querySelectorAll('[data-job]').forEach(button=>button.setAttribute('aria-expanded','false'));
}

async function openTimeline(job, scroll=true) {
  timelineJob=job.id;timelineIp=job.ip;
  const request=++timelineRequest;
  $('timeline-card').hidden=false;
  $('timeline-file').textContent=fileName(job.filename);
  document.querySelectorAll('[data-job]').forEach(button=>button.setAttribute('aria-expanded',String(button.dataset.job===job.id)));
  $('timeline-content').textContent='Verlauf wird aus der lokalen Aufzeichnung geladen…';
  if(scroll)$('timeline-card').scrollIntoView({behavior:'smooth',block:'start'});
  try {
    const response=await fetch('/api/timeline?job='+encodeURIComponent(job.id),{cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(!response.ok)throw new Error();
    const result=await response.json();
    if(request!==timelineRequest)return;
    if(result.read_only!==true || result.job.id!==job.id || result.job.ip!==selectedIp)throw new Error();
    renderTimeline(result);
  } catch (_) {
    if(request===timelineRequest)$('timeline-content').textContent='Der Verlauf konnte nicht geladen werden. Bitte erneut „Verlauf ansehen“ wählen.';
  }
}

function renderTimeline(result) {
  const area=$('timeline-content');area.replaceChildren();
  const {job,points,events}=result;
  timelineEnd=job.ended_at;
  const time=at=>new Date(at*1000).toLocaleTimeString('de-DE',{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit'});
  const description=document.createElement('p');description.className='timeline-summary';
  description.textContent=`${job.ended_at?'Aufgezeichneter Auftrag':'Laufender Auftrag · vorläufig'} · ${time(job.first_seen)}–${time(job.ended_at??job.last_seen)} · ${points.length} Stichproben`;
  area.append(description);
  if(!points.length) {
    const empty=document.createElement('p');empty.textContent='Für diesen Auftrag sind noch keine Temperaturmesswerte gespeichert.';
    area.append(empty);return;
  }
  const start=job.first_seen, end=Math.max(start+1,job.ended_at??job.last_seen,points[points.length-1].at);
  const keys=['nozzle_temp','bed_temp','nozzle_target','bed_target'];
  const values=points.flatMap(p=>keys.map(key=>p[key])).filter(number);
  const max=Math.max(100,Math.ceil(values.reduce((highest,v)=>Math.max(highest,v),0)/50)*50);
  const x=at=>52+(at-start)/(end-start)*680;
  const y=temp=>214-temp/max*180;
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 760 252');svg.setAttribute('class','temperature-chart');
  svg.setAttribute('role','img');svg.setAttribute('tabindex','0');
  svg.setAttribute('aria-label','Temperaturverlauf. Grün: Düse, Braun: Druckbett. Sollwerte gestrichelt. Mit Pfeiltasten einzelne Messwerte erkunden.');
  function element(tag,attributes,text) {
    const node=document.createElementNS(ns,tag);
    for(const [k,v] of Object.entries(attributes))node.setAttribute(k,String(v));
    if(text!==undefined)node.textContent=text;
    svg.append(node);return node;
  }
  for(let i=0;i<=4;i++) {
    const temp=max*i/4;
    element('line',{x1:52,x2:732,y1:y(temp),y2:y(temp),class:'chart-grid'});
    element('text',{x:42,y:y(temp)+4,'text-anchor':'end',class:'chart-axis'},`${Math.round(temp)}°`);
  }
  for(let i=0;i<=4;i++)element('text',{x:x(start+(end-start)*i/4),y:240,'text-anchor':'middle',class:'chart-axis'},time(start+(end-start)*i/4));
  let gaps=0;
  for(let i=1;i<points.length;i++) {
    if(points[i].at-points[i-1].at>90) {
      gaps++;
      element('rect',{x:x(points[i-1].at),y:34,width:x(points[i].at)-x(points[i-1].at),height:180,class:'chart-gap'});
    }
  }
  for(const [index,key] of keys.entries()) {
    let path='',previous=null;
    for(const point of points) {
      const crossed=previous && events.some(e=>e.kind==='disconnected' && e.at>previous.at && e.at<=point.at);
      if(!number(point[key])){previous=null;continue;}
      const move=!previous || point.at-previous.at>90 || crossed;
      path+=`${move?'M':'L'}${x(point.at).toFixed(2)},${y(point[key]).toFixed(2)} `;
      previous=point;
    }
    element('path',{d:path,fill:'none',class:`chart-series ${index%2===0?'chart-nozzle':'chart-bed'}${index>=2?' chart-target':''}`});
  }
  for(const event of events.filter(e=>['disconnected','printer_error'].includes(e.kind))) {
    const node=element('line',{x1:x(event.at),x2:x(event.at),y1:34,y2:214,class:'chart-event'});
    const title=document.createElementNS(ns,'title');title.textContent=time(event.at)+(event.kind==='disconnected'?' · Verbindung unterbrochen':' · Druckermeldung');node.append(title);
  }
  const marker=element('line',{x1:52,x2:52,y1:34,y2:214,class:'chart-cursor',visibility:'hidden'});
  const reading=document.createElement('p');reading.className='chart-reading';
  reading.textContent='Maus oder Finger über den Verlauf bewegen; mit Pfeiltasten Messwerte auswählen.';
  let selected=0;
  function show(index) {
    selected=Math.max(0,Math.min(points.length-1,index));const point=points[selected];
    marker.setAttribute('x1',x(point.at));marker.setAttribute('x2',x(point.at));marker.setAttribute('visibility','visible');
    reading.textContent=`${time(point.at)} · Düse ${number(point.nozzle_temp)?point.nozzle_temp+' °C':'kein frischer Messwert'} · Druckbett ${number(point.bed_temp)?point.bed_temp+' °C':'kein frischer Messwert'}`;
  }
  svg.addEventListener('pointermove',event=>{
    const bounds=svg.getBoundingClientRect();
    // Account for the centered SVG viewBox when the container is wider.
    const scale=Math.min(bounds.width/760,bounds.height/252);
    const left=bounds.left+(bounds.width-760*scale)/2;
    const at=start+((event.clientX-left)/scale-52)/680*(end-start);
    let closest=0;
    for(let i=1;i<points.length;i++)if(Math.abs(points[i].at-at)<Math.abs(points[closest].at-at))closest=i;
    show(closest);
  });
  svg.addEventListener('keydown',event=>{
    if(event.key==='ArrowRight'||event.key==='ArrowLeft'){event.preventDefault();show(selected+(event.key==='ArrowRight'?1:-1));}
  });
  const legend=document.createElement('div');legend.className='chart-legend';
  for(const [name,cls] of [['Düse','nozzle'],['Druckbett','bed'],['Sollwerte gestrichelt','target']]) {
    const item=document.createElement('span');item.className='legend-'+cls;item.textContent=name;legend.append(item);
  }
  area.append(legend,svg,reading);
  const note=document.createElement('p');note.className='timeline-summary';
  note.textContent=`Aufzeichnung in Stichproben. ${gaps?gaps+' Abstand/Abstände über 90 Sekunden sind schattiert.':'Längere Datenlücken werden als Unterbrechung dargestellt.'} Veraltete Messwerte werden nicht verbunden.`;
  area.append(note);
  const list=document.createElement('ul');list.className='timeline-events';
  const labels={connected:'Verbindung hergestellt',disconnected:'Verbindung unterbrochen',completed:'Druck abgeschlossen',cancelled:'Druck abgebrochen',printer_error:'Druckermeldung',unobserved_end:'Ende nicht beobachtet'};
  for(const event of events) {
    const item=document.createElement('li');
    const label=event.kind==='state'?`${stateNames[event.from]||event.from} → ${stateNames[event.to]||event.to}`:labels[event.kind]||`Auftrag erkannt: ${stateNames[event.state]||event.state||event.kind}`;
    item.textContent=`${time(event.at)} · ${label}`;
    if(['printer_error','disconnected'].includes(event.kind))item.className='timeline-warning';
    list.append(item);
  }
  area.append(list);
}
$('timeline-close').addEventListener('click',closeTimeline);
setInterval(()=>{
  const job=lastResponse?.history?.find(j=>j.id===timelineJob);
  if(job && (!job.ended_at || timelineEnd!==job.ended_at) && !requestFailed)openTimeline(job,false);
},30000);


async function refreshArchive() {
  if(!archiveIp)return;
  const request=++archiveRequest;
  const ip=archiveIp;
  const query=new URLSearchParams({ip,page:String(archivePage),search:$('history-search').value.trim(),state:$('history-filter').value});
  $('history-message').textContent='Historie wird geladen…';
  $('history-content').setAttribute('aria-busy','true');
  $('history-prev').disabled=true;$('history-next').disabled=true;
  try {
    const response=await fetch('/api/jobs?'+query,{cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(!response.ok)throw new Error();
    const result=await response.json();
    if(request!==archiveRequest || ip!==selectedIp)return;
    if(result.read_only!==true || result.ip!==ip)throw new Error();
    archivePage=result.page;
    for(const key of ['total','completed','active','cancelled'])$('archive-'+key).textContent=String(result.summary[key]);
    $('history-message').textContent=result.total===1?'1 passender Auftrag':`${result.total} passende Aufträge`;
    $('history-page').textContent=`Seite ${result.page+1} von ${result.pages}`;
    $('history-prev').disabled=result.page<=0;
    $('history-next').disabled=result.page+1>=result.pages;
    renderHistory(result.jobs,ip);
  } catch (_) {
    if(request===archiveRequest)$('history-message').textContent='Historie nicht erreichbar. Automatischer Neuversuch folgt.';
  } finally {
    if(request===archiveRequest)$('history-content').setAttribute('aria-busy','false');
  }
}
function filterArchive() {
  archiveRequest++;archivePage=0;historySignature=null;
  $('history-content').replaceChildren();
  $('history-message').textContent='Suche wird aktualisiert…';
  $('history-prev').disabled=true;$('history-next').disabled=true;
  clearTimeout(archiveDebounce);
  archiveDebounce=setTimeout(refreshArchive,250);
}
$('history-search').addEventListener('input',filterArchive);
$('history-filter').addEventListener('change',filterArchive);
$('history-prev').addEventListener('click',()=>{archivePage=Math.max(0,archivePage-1);refreshArchive();});
$('history-next').addEventListener('click',()=>{archivePage++;refreshArchive();});
setInterval(()=>{if(!requestFailed && !document.hidden)refreshArchive();},10000);

window.addEventListener('kobra-report-changed',()=>{historySignature=null;refreshArchive();});

window.addEventListener('kobra-control-changed',refresh);
