/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraSpeedControls=(()=>{
  const $=id=>document.getElementById(id),button=$('speed-control-open'),dialog=$('speed-control-dialog');
  if(!button||!dialog)return {render(){}};
  const select=$('speed-control-value'),message=$('speed-control-message'),note=$('speed-control-note');
  const names={1:'Silent',2:'Standard',3:'Sport'};
  let snapshot=null,selected=null,active=null,busy=false,generation=0,age=0,connection=null,renderedAt=0;
  function say(text){message.textContent=text;message.hidden=!text;}
  function extraAge(){return age+Math.max(0,(Date.now()-renderedAt)/1000);}
  function fresh(data,extra,link){
    const mode=data?.device_status?.speed_mode,control=data?.speed_control;
    return control?.enabled===true&&control.supported===true&&control.available===true&&
      typeof control.context==='string'&&/^[a-f0-9]{64}$/.test(control.context)&&link==='online'&&
      mode?.current_session===true&&Number.isInteger(mode.value)&&[1,2,3].includes(mode.value)&&
      Number.isFinite(mode.age_s)&&mode.age_s>=0&&Number.isFinite(extra)&&extra>=0&&mode.age_s+extra<=15;
  }
  function close(){generation++;active=null;if(dialog.open)dialog.close();}
  function render(data,extra=0,link=data.connection){
    if(selected!==data.ip){close();say('');selected=data.ip;}
    snapshot=data;age=extra;connection=link;renderedAt=Date.now();
    const enabled=data.speed_control?.enabled===true,ready=fresh(data,extra,link);
    button.hidden=!enabled;button.disabled=busy||!ready;button.setAttribute('aria-busy',String(busy));
    note.hidden=!enabled||ready;
    note.textContent=data.data?.print_state==='printing'?'Aktuelle Auftrags- und Modusdaten fehlen.':'Nur während eines laufenden Drucks verfügbar.';
    if(active&&(!ready||data.speed_control.context!==active.context||data.device_status.speed_mode.value!==active.before)){
      close();say('Druckauftrag oder Modus geändert. Bitte erneut öffnen.');
    }
  }
  function requestKey(){
    const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
    const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }
  async function api(body,guard=()=>true,onDispatch=()=>{}){
    const session=await (await fetch('/api/session',{signal:AbortSignal.timeout(5000)})).json();
    if(!session.authenticated||!session.account_configured)throw Error('Bitte erneut anmelden.');
    if(!guard())throw Error('Druckauftrag oder Auswahl geändert; nicht gesendet.');
    onDispatch();
    const response=await fetch('/api/controls',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':session.csrf},body:JSON.stringify(body),signal:AbortSignal.timeout(16000)});
    const result=await response.json();if(!response.ok)throw Error(result.error||'Speed Mode konnte nicht übernommen werden.');return result;
  }
  button.addEventListener('click',()=>{
    if(busy||!fresh(snapshot,extraAge(),connection))return;
    close();say('');active={ip:selected,context:snapshot.speed_control.context,before:snapshot.device_status.speed_mode.value};
    $('speed-control-printer').textContent=snapshot.data?.printer_name||selected;
    $('speed-control-file').textContent=snapshot.data?.filename||'Aktueller Druck';
    select.value=String(active.before);dialog.showModal();select.focus();
  });
  $('speed-control-cancel').addEventListener('click',close);dialog.addEventListener('cancel',close);
  $('speed-control-ok').addEventListener('click',async()=>{
    if(busy||!active)return;
    const desired=Number(select.value);if(!Number.isInteger(desired)||![1,2,3].includes(desired))return;
    const chosen={...active,desired},mark=++generation;
    const valid=()=>mark===generation&&selected===chosen.ip&&fresh(snapshot,extraAge(),connection)&&snapshot.speed_control.context===chosen.context&&snapshot.device_status.speed_mode.value===chosen.before;
    active=null;dialog.close();busy=true;render(snapshot,extraAge(),connection);say('Speed Mode wird geprüft …');
    let intent=null,dispatched=false;
    try{
      intent=await api({action:'prepare_speed',ip:chosen.ip,desired,context:chosen.context,request_id:requestKey()},valid);
      if(!valid()||intent.context!==chosen.context||intent.previous!==chosen.before){
        if(intent.state==='prepared')await api({action:'cancel',id:intent.id});intent=null;throw Error('Druckauftrag oder Modus geändert; bitte erneut auswählen.');
      }
      if(intent.state!=='prepared'){if(mark===generation)say(intent.detail);return;}
      const result=await api({action:'execute',id:intent.id,token:intent.token},valid,()=>{dispatched=true;});intent=null;
      if(mark===generation)say(result.state==='confirmed'?'Speed Mode '+names[desired]+' bestätigt.':result.detail);
      window.dispatchEvent(new Event('kobra-control-changed'));
    }catch(error){
      if(intent&&!dispatched)api({action:'cancel',id:intent.id}).catch(()=>{});
      if(mark===generation)say(error.message+(dispatched?' Ausgang unklar; kein automatischer Wiederholungsversuch.':''));
    }finally{busy=false;if(snapshot)render(snapshot,extraAge(),connection);}
  });
  window.addEventListener('hashchange',()=>{if(location.hash&&!['#overview','#printer-switcher'].includes(location.hash))close();});
  window.addEventListener('pagehide',close);
  return {render,close};
})();
