/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
// Chamber light is a direct action. Other future controls retain confirmation.
window.kobraLightControls=(()=>{
  const $=id=>document.getElementById(id);
  const button=$('light-control-switch');
  if(!button)return {render(){}};
  const message=$('light-control-message');
  let selected=null,snapshot=null,intent=null,generation=0,busy=false;
  let lastExtraAge=0,lastConnection=null,lastRenderedAt=0;
  function say(text){message.textContent=text;message.hidden=!text;}
  function requestKey(){
    const bytes=crypto.getRandomValues(new Uint8Array(16));
    bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
    const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }
  async function api(body,{guard=()=>true,dispatch=()=>{}}={}){
    const sessionResponse=await fetch('/api/session',{signal:AbortSignal.timeout(5000)});
    const session=await sessionResponse.json();
    if(!session.authenticated||!session.account_configured)throw Error('Bitte erneut anmelden.');
    if(!guard())throw Error('Druckerauswahl geändert; nicht gesendet.');
    dispatch();
    const response=await fetch('/api/controls',{
      method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':session.csrf},
      body:JSON.stringify(body),signal:AbortSignal.timeout(16000)});
    const result=await response.json();
    if(response.status===401){window.kobraAuth.login();throw Error('Bitte erneut anmelden.');}
    if(!response.ok)throw Error(result.error||'Licht konnte nicht geschaltet werden.');
    return result;
  }
  function close(){
    generation++;
    const old=intent;intent=null;
    if(old)api({action:'cancel',id:old.id}).catch(()=>{});
  }
  function render(data,extraAge=0,connection=data.connection){
    if(selected!==data.ip){close();say('');selected=data.ip;}
    snapshot=data;lastExtraAge=extraAge;lastConnection=connection;lastRenderedAt=Date.now();
    const enabled=data.light_control?.enabled===true;
    button.hidden=!enabled;
    if(!enabled){close();say('');return;}
    const light=data.device_status?.light_on;
    const fresh=data.light_control?.supported===true&&connection==='online'&&light?.current_session===true&&
      typeof light?.value==='boolean'&&Number.isFinite(light?.age_s)&&light.age_s>=0&&
      Number.isFinite(extraAge)&&extraAge>=0&&light.age_s+extraAge<=15;
    button.disabled=busy||!fresh;
    button.setAttribute('aria-checked',fresh?String(light.value):'false');
    button.setAttribute('aria-busy',String(busy));
    if(!fresh){close();say('Frische Lichtdaten fehlen. Schalten ist gesperrt.');}
  }
  button.addEventListener('click',async()=>{
    if(busy||button.disabled||!snapshot)return;
    const data=snapshot,mark=++generation;
    const current=()=>mark===generation&&selected===data.ip;
    let dispatched=false;
    busy=true;button.disabled=true;button.setAttribute('aria-busy','true');
    say('Licht wird geschaltet …');
    try{
      const prepared=await api({action:'prepare',ip:data.ip,
        desired:!data.device_status.light_on.value,request_id:requestKey()},{guard:current});
      if(!current()){
        api({action:'cancel',id:prepared.id}).catch(()=>{});return;
      }
      if(prepared.state!=='prepared'){say(prepared.detail);return;}
      intent=prepared;
      const result=await api({action:'execute',id:prepared.id,token:prepared.token},{guard:current,
        dispatch:()=>{dispatched=true;intent=null;}});
      if(current())say(result.state==='confirmed'?'Bestätigt.':result.detail);
      window.dispatchEvent(new Event('kobra-control-changed'));
    }catch(error){
      const old=intent;intent=null;
      if(old)api({action:'cancel',id:old.id}).catch(()=>{});
      if(current())say(error.message+(dispatched?' Ausgang unklar; kein automatischer Wiederholungsversuch.':''));
    }finally{busy=false;if(snapshot)render(snapshot,lastExtraAge+Math.max(0,(Date.now()-lastRenderedAt)/1000),lastConnection);}
  });
  window.addEventListener('hashchange',()=>{
    if(location.hash&&!['#overview','#printer-switcher'].includes(location.hash))close();
  });
  window.addEventListener('pagehide',close);
  return {render,close};
})();
