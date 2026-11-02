/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
// Narrow chamber-light control; explicitly enabled printers only.
window.kobraLightControls=(()=>{
  const $=id=>document.getElementById(id);
  if(!$('light-control-card'))return {render(){}};
  let selected=null, snapshot=null, intent=null, generation=0, busy=false;
  const button=$('light-control-switch'), dialog=$('light-control-dialog');
  const message=$('light-control-message');
  function requestKey(){
    // getRandomValues also works on the private HTTP/LAN origin.
    const bytes=crypto.getRandomValues(new Uint8Array(16));
    bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
    const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }
  async function api(body){
    const sessionResponse=await fetch('/api/session',{signal:AbortSignal.timeout(5000)});
    const session=await sessionResponse.json();
    if(!session.authenticated||!session.account_configured)throw Error('Bitte erneut anmelden.');
    const response=await fetch('/api/controls',{
      method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':session.csrf},
      body:JSON.stringify(body),signal:AbortSignal.timeout(16000)});
    const result=await response.json();
    if(response.status===401){window.kobraAuth.login();throw Error('Bitte erneut anmelden.');}
    if(!response.ok)throw Error(result.error||'Steuervorgang konnte nicht ausgeführt werden.');
    return result;
  }
  function close(){
    generation++;
    const old=intent;intent=null;
    if(dialog.open)dialog.close();
    if(old)api({action:'cancel',id:old.id}).catch(()=>{});
  }
  function render(data,extraAge=0,connection=data.connection){
    if(selected!==data.ip){close();message.textContent='';selected=data.ip;}
    snapshot=data;
    const enabled=data.light_control?.enabled===true;
    $('light-control-card').hidden=!enabled;
    if(!enabled){close();return;}
    const light=data.device_status?.light_on;
    const fresh=data.light_control?.supported===true&&connection==='online'&&light?.current_session===true&&
      typeof light?.value==='boolean'&&Number.isFinite(light?.age_s)&&light.age_s>=0&&light.age_s+extraAge<=15;
    $('light-control-target').textContent=`${data.data?.printer_name||'Drucker'} · ${data.ip}`;
    button.disabled=busy||!fresh;
    button.setAttribute('aria-checked',fresh?String(light.value):'false');
    button.textContent=fresh?(light.value?'An':'Aus'):'Nicht verfügbar';
    if(!fresh){close();message.textContent='Frische Lichtdaten fehlen. Schalten ist gesperrt.';}
  }
  button.addEventListener('click',async()=>{
    if(busy||!snapshot)return;
    const data=snapshot, mark=++generation;busy=true;button.disabled=true;
    message.textContent='Änderung wird vorbereitet …';
    try{
      const prepared=await api({action:'prepare',ip:data.ip,
        desired:!data.device_status.light_on.value,request_id:requestKey()});
      if(mark!==generation||selected!==data.ip){
        api({action:'cancel',id:prepared.id}).catch(()=>{});return;
      }
      if(prepared.state!=='prepared'){message.textContent=prepared.detail;return;}
      intent=prepared;
      $('light-control-confirm-target').textContent=
        `${data.data?.printer_name||'Drucker'} · ${prepared.ip}`;
      $('light-control-confirm-action').textContent=prepared.desired?'Licht einschalten':'Licht ausschalten';
      message.textContent='Noch kein Befehl gesendet.';
      dialog.showModal();
    }catch(error){message.textContent=error.message;}
    finally{busy=false;if(snapshot)render(snapshot);}
  });
  $('light-control-cancel').addEventListener('click',close);
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  $('light-control-apply').addEventListener('click',async()=>{
    if(!intent||busy)return;
    const command=intent, target=selected;intent=null;dialog.close();busy=true;
    button.disabled=true;message.textContent='Warte auf die Rückmeldung des Druckers …';
    try{
      const result=await api({action:'execute',id:command.id,token:command.token});
      if(selected===target)message.textContent=result.detail;
      window.dispatchEvent(new Event('kobra-control-changed')); 
    }catch(error){
      if(selected===target)message.textContent=error.message+
        ' Ausgang unklar; kein automatischer Wiederholungsversuch.';
    }finally{busy=false;if(snapshot)render(snapshot);}
  });
  window.addEventListener('hashchange',()=>{
    if(location.hash&&!['#overview','#printer-switcher'].includes(location.hash))close();
  });
  window.addEventListener('pagehide',close);
  return {render,close};
})();
