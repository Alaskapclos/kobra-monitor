/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraFanControls=(()=>{
  const $=id=>document.getElementById(id);
  const dialog=$('fan-control-dialog');
  if(!dialog)return {render(){}};
  const labels={part_fan:'Bauteillüfter',aux_fan:'Zusatzlüfter',chamber_fan:'Kammerlüfter'};
  const fields={part_fan:'fan_speed',aux_fan:'aux_fan_speed',chamber_fan:'box_fan_level'};
  const range=$('fan-control-range'),number=$('fan-control-value'),ok=$('fan-control-ok');
  const message=$('fan-control-message');
  let snapshot=null,selected=null,active=null,generation=0,busy=false;
  let extra=0,connection=null,renderedAt=0;
  function say(text){message.textContent=text;message.hidden=!text;}
  function currentAge(){return extra+Math.max(0,(Date.now()-renderedAt)/1000);}
  function fresh(data,fan,age,link){
    const item=data?.device_status?.[fields[fan]];
    return data?.fan_control?.enabled===true&&data.fan_control.supported===true&&link==='online'&&
      item?.current_session===true&&Number.isInteger(item.value)&&item.value>=0&&item.value<=100&&
      Number.isFinite(item.age_s)&&item.age_s>=0&&Number.isFinite(age)&&age>=0&&item.age_s+age<=15;
  }
  function close(){generation++;active=null;if(dialog.open)dialog.close();}
  function render(data,age=0,link=data.connection){
    if(selected!==data.ip){close();say('');selected=data.ip;}
    snapshot=data;extra=age;connection=link;renderedAt=Date.now();
    for(const fan of Object.keys(labels)){
      const button=$('control-'+fan);
      button.hidden=data.fan_control?.enabled!==true;
      button.disabled=busy||!fresh(data,fan,age,link);
      button.setAttribute('aria-busy',String(busy));
    }
    if(active&&(!fresh(data,active.fan,age,link)||data.device_status[fields[active.fan]].value!==active.before)){
      close();say('Lüfterzustand geändert oder veraltet. Bitte erneut öffnen.');
    }
  }
  function requestKey(){
    const bytes=crypto.getRandomValues(new Uint8Array(16));
    bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
    const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }
  async function api(body,guard=()=>true,onDispatch=()=>{}){
    const response=await fetch('/api/session',{signal:AbortSignal.timeout(5000)});
    const session=await response.json();
    if(!session.authenticated||!session.account_configured)throw Error('Bitte erneut anmelden.');
    if(!guard())throw Error('Auswahl oder Zustand geändert; nicht gesendet.');
    onDispatch();
    const result=await fetch('/api/controls',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':session.csrf},body:JSON.stringify(body),signal:AbortSignal.timeout(16000)});
    const value=await result.json();
    if(!result.ok)throw Error(value.error||'Lüfterstufe konnte nicht übernommen werden.');
    return value;
  }
  for(const fan of Object.keys(labels))$('control-'+fan).addEventListener('click',()=>{
    if(busy||!fresh(snapshot,fan,currentAge(),connection))return;
    close();say('');
    active={fan,ip:selected,before:snapshot.device_status[fields[fan]].value};
    $('fan-control-title').textContent=labels[fan]+' einstellen';
    $('fan-control-printer').textContent=snapshot.data?.printer_name||snapshot.ip;
    $('fan-control-unit').textContent=fan==='chamber_fan'?'Stufe (0–100)':'Leistung (%)';
    range.value=number.value=String(active.before);ok.disabled=false;
    dialog.showModal();number.focus();
  });
  function sync(source,target){
    target.value=source.value;
    ok.disabled=!Number.isInteger(Number(number.value))||number.value.trim()===''||Number(number.value)<0||Number(number.value)>100;
  }
  range.addEventListener('input',()=>sync(range,number));
  number.addEventListener('input',()=>sync(number,range));
  $('fan-control-cancel').addEventListener('click',close);
  dialog.addEventListener('cancel',close);
  ok.addEventListener('click',async()=>{
    if(!active||busy||ok.disabled)return;
    const chosen={...active,desired:Number(number.value)},mark=++generation;
    if(!Number.isInteger(chosen.desired)||chosen.desired<0||chosen.desired>100)return;
    const valid=()=>mark===generation&&selected===chosen.ip&&fresh(snapshot,chosen.fan,currentAge(),connection)&&snapshot.device_status[fields[chosen.fan]].value===chosen.before;
    active=null;dialog.close();busy=true;
    render(snapshot,currentAge(),connection);say(labels[chosen.fan]+': Übernahme wird geprüft …');
    let intent=null,dispatched=false;
    try{
      intent=await api({action:'prepare_fan',ip:chosen.ip,fan:chosen.fan,desired:chosen.desired,request_id:requestKey()},valid);
      if(!valid()||intent.previous!==chosen.before){
        if(intent.state==='prepared')await api({action:'cancel',id:intent.id});
        intent=null;throw Error('Zustand geändert; bitte erneut auswählen.');
      }
      if(intent.state!=='prepared'){if(mark===generation)say(intent.detail);return;}
      const result=await api({action:'execute',id:intent.id,token:intent.token},valid,()=>{dispatched=true;});
      intent=null;
      if(mark===generation)say(labels[chosen.fan]+': '+(result.state==='confirmed'?'Stufe '+chosen.desired+' bestätigt.':result.detail));
      window.dispatchEvent(new Event('kobra-control-changed'));
    }catch(error){
      if(intent&&!dispatched)api({action:'cancel',id:intent.id}).catch(()=>{});
      if(mark===generation)say(error.message+(dispatched?' Ausgang unklar; kein automatischer Wiederholungsversuch.':''));
    }finally{busy=false;if(snapshot)render(snapshot,currentAge(),connection);}
  });
  window.addEventListener('hashchange',()=>{if(location.hash&&!['#overview','#printer-switcher'].includes(location.hash))close();});
  window.addEventListener('pagehide',close);
  return {render,close};
})();
