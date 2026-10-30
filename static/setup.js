'use strict';
window.kobraAuth=(()=>{
  let authenticated=false,csrf='',printers=[],accountConfigured=false,accountName='';
  const $=id=>document.getElementById(id);
  const panel=$('setup-panel');
  function showPanel(show){panel.hidden=!show;for(const node of document.querySelectorAll('main,aside'))node.inert=show;}
  function step(name){
    showPanel(true);for(const part of ['login','account','printers','done'])$('setup-'+part).hidden=part!==name;
    $('setup-heading').textContent={login:'Willkommen bei Kobra Monitor.',account:accountConfigured?'Dein Benutzerkonto.':'Lege dein Benutzerkonto an.',printers:'Verbinde deine Drucker.',done:'Alles bereit.'}[name];
    $('setup-steps').hidden=accountConfigured;
    $('setup-error').textContent='';
    const first=$('setup-'+name).querySelector('input:not([hidden]),textarea,button');if(first)first.focus();
  }
  function controls(){for(const id of ['account-open','logout'])$(id).hidden=!(authenticated&&accountConfigured);}
  function login(){authenticated=false;csrf='';controls();step('login');}
  function account(){
    if(!authenticated){login();return;}
    $('account-name').value=accountName;$('account-password').value='';$('account-confirm').value='';$('account-current').value='';
    $('account-current-row').hidden=!accountConfigured;$('account-current').required=accountConfigured;
    $('account-cancel').hidden=!accountConfigured;$('account-save').textContent=accountConfigured?'Änderungen speichern':'Konto anlegen';
    $('account-intro').textContent=accountConfigured?'Ändere hier deinen Benutzernamen oder dein Passwort. Danach werden andere Browser abgemeldet.':'Mit deinem eigenen Benutzernamen und Passwort meldest du dich künftig an – auch unterwegs über dein VPN. Alles bleibt auf deinem Rechner oder NAS.';
    step('account');
  }
  function configure(){if(!authenticated){login();return;}if(!accountConfigured){account();return;}$('setup-ips').value=printers.join('\n');$('setup-cancel').hidden=!printers.length;step('printers');}
  function accept(result){authenticated=true;csrf=result.csrf;accountConfigured=result.account_configured!==false;accountName=result.username||'';controls();if(!accountConfigured){account();return false;}showPanel(false);return true;}
  async function establish(credentials){
    const response=await fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials),signal:AbortSignal.timeout(10000)});
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Anmeldung fehlgeschlagen.');
    return accept(result);
  }
  async function boot(){
    const fragment=new URLSearchParams(location.hash.slice(1));const code=fragment.get('access');
    if(code)history.replaceState(null,'',location.pathname+location.search);
    try {
      if(code)return await establish({code});
      const response=await fetch('/api/session',{cache:'no-store',signal:AbortSignal.timeout(5000)});
      const result=await response.json();accountConfigured=result.account_configured!==false;
      $('setup-login-credentials').hidden=!accountConfigured;$('setup-initial').hidden=accountConfigured;
      $('login-name').required=accountConfigured;$('login-password').required=accountConfigured;
      if(result.authenticated)return accept(result);
      login();return false;
    } catch(_){login();$('setup-error').textContent='Der Monitor ist gerade nicht erreichbar oder der Einrichtungslink ist ungültig. Bitte erneut versuchen.';return false;}
  }
  $('setup-login-form').addEventListener('submit',async event=>{
    event.preventDefault();$('setup-login-button').disabled=true;$('setup-error').textContent='';
    try{const ready=await establish({username:$('login-name').value,password:$('login-password').value});$('login-password').value='';if(ready)window.dispatchEvent(new Event('kobra-authenticated'));}
    catch(error){$('setup-error').textContent=error.message;}
    finally{$('setup-login-button').disabled=false;}
  });
  $('setup-migrate-form').addEventListener('submit',async event=>{
    event.preventDefault();$('setup-migrate-button').disabled=true;
    try{await establish({code:$('setup-code').value.trim()});$('setup-code').value='';}
    catch(error){$('setup-error').textContent=error.message;}
    finally{$('setup-migrate-button').disabled=false;}
  });
  $('account-form').addEventListener('submit',async event=>{
    event.preventDefault();$('account-save').disabled=true;$('setup-error').textContent='';
    try{
      if($('account-password').value!==$('account-confirm').value)throw new Error('Die beiden Passwörter stimmen nicht überein.');
      const response=await fetch('/api/account',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':csrf},body:JSON.stringify({username:$('account-name').value,password:$('account-password').value,password_confirmation:$('account-confirm').value,current_password:$('account-current').value}),signal:AbortSignal.timeout(15000)});
      const result=await response.json();if(!response.ok)throw new Error(result.error||'Das Konto konnte nicht gespeichert werden.');
      accept(result);for(const id of ['account-password','account-confirm','account-current'])$(id).value='';
      window.dispatchEvent(new Event('kobra-authenticated'));if(!printers.length)configure();
    }catch(error){$('setup-error').textContent=error.message;}
    finally{$('account-save').disabled=false;}
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
  $('logout').addEventListener('click',async()=>{
    try{const response=await fetch('/api/logout',{method:'POST',headers:{'X-Kobra-CSRF':csrf},signal:AbortSignal.timeout(5000)});if(!response.ok&&response.status!==403)throw new Error();location.reload();}
    catch(_){$('setup-error').textContent='Abmelden nicht möglich. Bitte erneut versuchen.';showPanel(true);}
  });
  $('account-open').addEventListener('click',account);
  $('account-cancel').addEventListener('click',()=>{for(const id of ['account-password','account-confirm','account-current'])$(id).value='';showPanel(false);});
  $('setup-open').addEventListener('click',configure);
  $('setup-done-button').addEventListener('click',()=>{showPanel(false);});
  $('setup-cancel').addEventListener('click',()=>{if(printers.length)showPanel(false);});
  return {ready:boot(),get authenticated(){return authenticated&&accountConfigured;},login,configure,
    setPrinters(ips){printers=ips||[];if(authenticated&&accountConfigured&&!printers.length&&panel.hidden)configure();}};
})();
