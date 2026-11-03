/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraPrintControls=(()=>{
 const $=id=>document.getElementById(id),dialog=$('print-control-dialog');
 if(!dialog)return {render(){}};
 const labels={print_pause:'Druck pausieren',print_resume:'Druck fortsetzen',print_stop:'Druck abbrechen'};
 const messages={print_pause:'Pause vom Drucker bestätigt.',print_resume:'Fortsetzen vom Drucker bestätigt.',print_stop:'Abbruch vom Drucker bestätigt.'};
 let snapshot=null,selected=null,active=null,busy=false,generation=0,extra=0,renderedAt=0,connection=null;
 const say=text=>{$('print-control-message').textContent=text;$('print-control-message').hidden=!text;};
 function age(){return extra+Math.max(0,(Date.now()-renderedAt)/1000);}
 function fresh(data,action,elapsed,link){
  const p=data?.print_control;
  return p?.enabled===true&&p.supported===true&&p.available?.[action]===true&&link==='online'&&
   typeof p.context==='string'&&/^[a-f0-9]{64}$/.test(p.context)&&typeof p.filename==='string'&&p.filename.length>0&&
   Number.isFinite(p.age_s)&&p.age_s>=0&&Number.isFinite(elapsed)&&elapsed>=0&&p.age_s+elapsed<=15;
 }
 function close(){generation++;active=null;if(dialog.open)dialog.close();}
 function render(data,elapsed=0,link=data.connection){
  if(selected!==data.ip){close();say('');selected=data.ip;}
  snapshot=data;extra=elapsed;connection=link;renderedAt=Date.now();
  $('print-controls').hidden=data.print_control?.enabled!==true;
  for(const action of Object.keys(labels)){
   const b=$('control-'+action);b.disabled=busy||!fresh(data,action,elapsed,link);b.setAttribute('aria-busy',String(busy));
   b.hidden=action==='print_resume'?data.print_control?.phase!==2:action==='print_pause'?data.print_control?.phase===2:false;
  }
  if(active&&(!fresh(data,active.action,elapsed,link)||data.print_control.context!==active.context||data.print_control.phase!==active.before)){
   close();say('Druckauftrag oder Zustand geändert. Bitte erneut auswählen.');
  }
 }
 function key(){const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const s=Array.from(b,x=>x.toString(16).padStart(2,'0')).join('');return `${s.slice(0,8)}-${s.slice(8,12)}-${s.slice(12,16)}-${s.slice(16,20)}-${s.slice(20)}`;}
 async function api(body,guard=()=>true,onDispatch=()=>{}){
  const session=await(await fetch('/api/session',{signal:AbortSignal.timeout(5000)})).json();
  if(!session.authenticated||!session.account_configured)throw Error('Bitte erneut anmelden.');
  if(!guard())throw Error('Druckauftrag oder Auswahl geändert; nicht gesendet.');
  onDispatch();const response=await fetch('/api/controls',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':session.csrf},body:JSON.stringify(body),signal:AbortSignal.timeout(16000)});
  const result=await response.json();if(!response.ok)throw Error(result.error||'Druckaktion konnte nicht übernommen werden.');return result;
 }
 for(const action of Object.keys(labels))$('control-'+action).addEventListener('click',()=>{
  if(busy||!fresh(snapshot,action,age(),connection))return;
  close();say('');active={ip:selected,action,context:snapshot.print_control.context,before:snapshot.print_control.phase};
  $('print-control-title').textContent=labels[action]+'?';$('print-control-printer').textContent=snapshot.data?.printer_name||selected;
  $('print-control-file').textContent=snapshot.print_control.filename;
  $('print-control-warning').textContent=action==='print_stop'?'Dieser Druck wird beendet und kann anschließend nicht fortgesetzt werden.':action==='print_pause'?'Der ausgewählte Druck wird pausiert. Erst mit der Bestätigung wird der Befehl gesendet.':'Der pausierte Druck wird fortgesetzt. Der Drucker kann sich dabei wieder bewegen.';
  $('print-control-ok').textContent=labels[action];$('print-control-ok').classList.toggle('print-control-danger',action==='print_stop');dialog.showModal();$('print-control-cancel').focus();
 });
 $('print-control-cancel').addEventListener('click',close);dialog.addEventListener('cancel',close);
 $('print-control-ok').addEventListener('click',async()=>{
  if(!active||busy)return;const chosen={...active},mark=++generation;
  const valid=()=>mark===generation&&selected===chosen.ip&&fresh(snapshot,chosen.action,age(),connection)&&snapshot.print_control.context===chosen.context&&snapshot.print_control.phase===chosen.before;
  active=null;dialog.close();busy=true;render(snapshot,age(),connection);say('Druckaktion wird geprüft …');let intent=null,dispatched=false;
  try{
   intent=await api({action:'prepare_print',ip:chosen.ip,operation:chosen.action,context:chosen.context,request_id:key()},valid);
   if(!valid()||intent.context!==chosen.context||intent.previous!==chosen.before){if(intent.state==='prepared')await api({action:'cancel',id:intent.id});intent=null;throw Error('Druckauftrag oder Zustand geändert; bitte erneut auswählen.');}
   if(intent.state!=='prepared'){if(mark===generation)say(intent.detail);return;}
   const result=await api({action:'execute',id:intent.id,token:intent.token},valid,()=>{dispatched=true;});intent=null;
   if(mark===generation)say(result.state==='confirmed'?messages[chosen.action]:result.detail);window.dispatchEvent(new Event('kobra-control-changed'));
  }catch(error){if(intent&&!dispatched)api({action:'cancel',id:intent.id}).catch(()=>{});if(mark===generation)say(error.message+(dispatched?' Ausgang unklar; kein automatischer Wiederholungsversuch.':''));}
  finally{busy=false;if(snapshot)render(snapshot,age(),connection);}
 });
 window.addEventListener('hashchange',()=>{if(location.hash&&!['#overview','#printer-switcher'].includes(location.hash))close();});window.addEventListener('pagehide',close);
 return {render,close};
})();
