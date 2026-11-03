/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraMotionControls=(()=>{
 const $=id=>document.getElementById(id),dialog=$('motion-dialog');
 if(!dialog)return {render(){}};
 let snapshot=null,selected=null,active=null,busy=false,generation=0,extra=0,renderedAt=0,connection=null;
 const buttons=[...document.querySelectorAll('[data-motion]')];
 const age=()=>extra+Math.max(0,(Date.now()-renderedAt)/1000);
 const say=text=>{$('motion-message').textContent=text;};
 const fresh=(data,elapsed,link)=>data?.motion_control?.enabled===true&&data.motion_control.supported===true&&
  data.motion_control.available===true&&link==='online'&&/^[a-f0-9]{64}$/.test(data.motion_control.context||'')&&
  Number.isFinite(data.motion_control.age_s)&&data.motion_control.age_s>=0&&Number.isFinite(elapsed)&&elapsed>=0&&data.motion_control.age_s+elapsed<=15;
 function confirmed(data){return !!data?.motion_control?.print_cycle&&data.motion_control.confirmed===true;}
 function close(){generation++;active=null;if(dialog.open)dialog.close();$('motion-present').checked=false;}
 function render(data,elapsed=0,link=data.connection){
  if(selected!==data.ip){close();say('');selected=data.ip;}
  snapshot=data;extra=elapsed;connection=link;renderedAt=Date.now();
  $('motion-controls').hidden=data.motion_control?.enabled!==true;
  for(const b of buttons)b.disabled=busy||!fresh(data,elapsed,link);
  $('motion-consent-state').textContent=confirmed(data)?'X/Y/Z freigegeben: Bis zum nächsten regulären Druck kommt keine weitere Bestätigungsfrage. Homing wird weiterhin einzeln bestätigt.':'Vor der ersten X/Y/Z-Fahrt nach einem Druck ist eine Bestätigung erforderlich.';
  $('motion-availability').textContent=data.motion_control?.wait_s>0?`Wartezeit: ${data.motion_control.wait_s} s. Stillstand vor Ort prüfen.`:fresh(data,elapsed,link)?'Bereit für einzelne manuelle Fahrten.':'Nur bei aktuellem Leerlauf verfügbar; während Druck, Pause und Vorbereitung gesperrt.';
  if(active&&(!fresh(data,elapsed,link)||data.motion_control.context!==active.context)){close();say('Druckerzustand oder Verbindung geändert. Bitte erneut auswählen.');}
 }
 function key(){const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const s=Array.from(b,x=>x.toString(16).padStart(2,'0')).join('');return `${s.slice(0,8)}-${s.slice(8,12)}-${s.slice(12,16)}-${s.slice(16,20)}-${s.slice(20)}`;}
 async function api(body,guard=()=>true,onDispatch=()=>{}){
  const session=await(await fetch('/api/session',{signal:AbortSignal.timeout(5000)})).json();
  if(!session.authenticated||!session.account_configured)throw Error('Bitte erneut anmelden.');
  if(!guard())throw Error('Druckerzustand oder Auswahl geändert; nicht gesendet.');
  onDispatch();const response=await fetch('/api/controls',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':session.csrf},body:JSON.stringify(body),signal:AbortSignal.timeout(16000)});
  const result=await response.json();if(!response.ok)throw Error(result.error||'Bewegung konnte nicht angefordert werden.');return result;
 }
 for(const b of buttons)b.addEventListener('click',()=>{
  if(busy||!fresh(snapshot,age(),connection))return;
  const step=Number($('motion-step').value),action=b.dataset.motion;
  if(![1,15,50].includes(step))return;
  const desired=action.startsWith('home_')?1:Number(b.dataset.direction)*step;
  close();say('');active={ip:selected,action,desired,context:snapshot.motion_control.context};
  if(action.startsWith('axis_')&&confirmed(snapshot)){const chosen={...active};active=null;return run(chosen,false);}
  $('motion-confirmation-note').hidden=action.startsWith('home_');
  $('motion-printer').textContent=snapshot.data?.printer_name||selected;
  $('motion-action').textContent=action==='home_xy'?'Homing Druckkopf (X/Y)':action==='home_z'?'Homing Druckbett (Z)':`${action.slice(-1).toUpperCase()} ${desired>0?'+':''}${desired} mm`;
  $('motion-present').checked=false;$('motion-ok').disabled=true;dialog.showModal();$('motion-cancel').focus();
 });
 $('motion-present').addEventListener('change',()=>{$('motion-ok').disabled=!$('motion-present').checked;});
 $('motion-cancel').addEventListener('click',close);dialog.addEventListener('cancel',close);
 $('motion-ok').addEventListener('click',()=>{
  if(!active||busy||!$('motion-present').checked)return;return run({...active},true);
 });
 async function run(chosen,present){
  const mark=++generation;
  const valid=()=>mark===generation&&selected===chosen.ip&&fresh(snapshot,age(),connection)&&snapshot.motion_control.context===chosen.context;
  active=null;dialog.close();busy=true;render(snapshot,age(),connection);say('Bewegungsauftrag wird geprüft …');let intent=null,dispatched=false;
  try{
   intent=await api({action:'prepare_motion',ip:chosen.ip,operation:chosen.action,desired:chosen.desired,present,context:chosen.context,request_id:key()},valid);
   if(!valid()||intent.context!==chosen.context){if(intent.state==='prepared')await api({action:'cancel',id:intent.id});intent=null;throw Error('Druckerzustand geändert; bitte erneut auswählen.');}
   if(intent.state!=='prepared'){if(mark===generation)say(intent.detail);return;}
   const result=await api({action:'execute',id:intent.id,token:intent.token},valid,()=>{dispatched=true;});intent=null;
   if(result.motion_confirmed===true&&result.print_cycle===snapshot?.motion_control?.print_cycle)snapshot.motion_control.confirmed=true;
   if(mark===generation)say(result.detail);window.dispatchEvent(new Event('kobra-control-changed'));
  }catch(error){if(intent&&!dispatched)api({action:'cancel',id:intent.id}).catch(()=>{});if(mark===generation)say(error.message+(dispatched?' Ausgang unklar; kein automatischer Wiederholungsversuch.':''));}
  finally{busy=false;if(snapshot)render(snapshot,age(),connection);}
 }
 window.addEventListener('hashchange',()=>{if(location.hash&&!['#overview','#printer-switcher'].includes(location.hash))close();});window.addEventListener('pagehide',close);
 return {render,close};
})();
