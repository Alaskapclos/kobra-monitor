'use strict';
window.kobraAuth=(()=>{
  let authenticated=false,csrf='',printers=[];
  const $=id=>document.getElementById(id);
  const panel=$('setup-panel');
  function showPanel(show){panel.hidden=!show;for(const node of document.querySelectorAll('main,aside'))node.inert=show;}
  function step(name){showPanel(true);for(const part of ['login','printers','done'])$('setup-'+part).hidden=part!==name;$('setup-error').textContent='';}
  function login(){authenticated=false;step('login');}
  function configure(){if(!authenticated){login();return;}$('setup-ips').value=printers.join('\n');$('setup-cancel').hidden=!printers.length;step('printers');}
  async function establish(code){
    const response=await fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code}),signal:AbortSignal.timeout(5000)});
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Anmeldung fehlgeschlagen.');
    authenticated=true;csrf=result.csrf;showPanel(false);return true;
  }
  async function boot(){
    const fragment=new URLSearchParams(location.hash.slice(1));const code=fragment.get('access');
    if(code)history.replaceState(null,'',location.pathname+location.search);
    try {
      if(code)return await establish(code);
      const response=await fetch('/api/session',{cache:'no-store',signal:AbortSignal.timeout(5000)});
      const result=await response.json();authenticated=result.authenticated===true;csrf=result.csrf||'';
      if(!authenticated)login();return authenticated;
    } catch(_){login();$('setup-error').textContent='Monitor nicht erreichbar oder Zugang ungültig. Bitte Zugangscode eingeben.';return false;}
  }
  $('setup-login-form').addEventListener('submit',async event=>{
    event.preventDefault();$('setup-login-button').disabled=true;
    try{await establish($('setup-code').value.trim());$('setup-code').value='';window.dispatchEvent(new Event('kobra-authenticated'));}
    catch(error){$('setup-error').textContent=error.message;}
    finally{$('setup-login-button').disabled=false;}
  });
  $('setup-printer-form').addEventListener('submit',async event=>{
    event.preventDefault();$('setup-save').disabled=true;$('setup-error').textContent='';
    const ips=$('setup-ips').value.split(/[\n,;]+/).map(v=>v.trim()).filter(Boolean);
    try{
      const response=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':csrf},body:JSON.stringify({printer_ips:ips}),signal:AbortSignal.timeout(10000)});
      if(response.status===401){login();return;}
      const result=await response.json();if(!response.ok)throw new Error(result.error||'Einrichtung konnte nicht gespeichert werden.');
      printers=result.ips;step('done');window.dispatchEvent(new Event('kobra-configured'));
    }catch(error){$('setup-error').textContent=error.message;}
    finally{$('setup-save').disabled=false;}
  });
  $('setup-open').addEventListener('click',configure);
  $('setup-done-button').addEventListener('click',()=>{showPanel(false);});
  $('setup-cancel').addEventListener('click',()=>{if(printers.length)showPanel(false);});
  return {ready:boot(),get authenticated(){return authenticated;},login,configure,
    setPrinters(ips){printers=ips||[];if(authenticated&&!printers.length&&panel.hidden)configure();}};
})();
