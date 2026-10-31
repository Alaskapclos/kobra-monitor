'use strict';
window.kobraAuth=(()=>{
  let authenticated=false,csrf='',printers=[],accountConfigured=false,accountName='',printerStates=[],rowCounter=0,setupSaving=false;
  const $=id=>document.getElementById(id);
  const panel=$('setup-panel');
  function showPanel(show){if(show)window.kobraCamera?.close();panel.hidden=!show;for(const node of document.querySelectorAll('main,aside'))node.inert=show;}
  function step(name){
    showPanel(true);for(const part of ['login','account','printers','done'])$('setup-'+part).hidden=part!==name;
    $('setup-heading').textContent={login:'Willkommen bei Kobra Monitor.',account:accountConfigured?'Dein Benutzerkonto.':'Lege dein Benutzerkonto an.',printers:'Verbinde deine Drucker.',done:'Drucker gespeichert.'}[name];
    $('setup-steps').hidden=accountConfigured;
    $('setup-error').textContent='';
    const first=$('setup-'+name).querySelector('input:not([hidden]),textarea,button');if(first)first.focus();
  }
  function controls(){for(const id of ['account-open','logout'])$(id).hidden=!(authenticated&&accountConfigured);}
  function login(){window.kobraCamera?.close();authenticated=false;csrf='';controls();step('login');}
  function account(){
    if(!authenticated){login();return;}
    $('account-name').value=accountName;$('account-password').value='';$('account-confirm').value='';$('account-current').value='';
    $('account-current-row').hidden=!accountConfigured;$('account-current').required=accountConfigured;
    $('account-cancel').hidden=!accountConfigured;$('account-save').textContent=accountConfigured?'Änderungen speichern':'Konto anlegen';
    $('account-intro').textContent=accountConfigured?'Ändere hier deinen Benutzernamen oder dein Passwort. Danach werden andere Browser abgemeldet.':'Mit deinem eigenen Benutzernamen und Passwort meldest du dich künftig an – auch unterwegs über dein VPN. Alles bleibt auf deinem Rechner oder NAS.';
    step('account');
  }
  function printerInputs(){return [...$('setup-printer-list').querySelectorAll('input')];}
  function updateRows(){
    const rows=[...$('setup-printer-list').children];
    rows.forEach((row,index)=>{
      row.querySelector('label').textContent=`Drucker ${index+1} · IP-Adresse`;
      const remove=row.querySelector('button');remove.disabled=setupSaving||rows.length===1;remove.setAttribute('aria-label',`Drucker ${index+1} entfernen`);
    });
    $('setup-add-printer').disabled=setupSaving||rows.length>=16;
    $('setup-printer-limit').textContent=rows.length>=16?'Alle 16 Plätze sind belegt.':'Bis zu 16 Drucker. Die Reihenfolge kannst du später in der Übersicht durch Ziehen ändern.';
    renderConnections();
  }
  function addPrinter(value='',focus=false){
    if(printerInputs().length>=16)return;
    const row=document.createElement('div');row.className='setup-printer-row';
    const label=document.createElement('label'),input=document.createElement('input'),line=document.createElement('div'),remove=document.createElement('button'),status=document.createElement('p');
    input.id=`setup-printer-${++rowCounter}`;label.htmlFor=input.id;input.value=value;input.required=true;input.inputMode='decimal';input.autocomplete='off';input.spellcheck=false;input.placeholder='z. B. 192.168.1.100';input.maxLength=15;
    status.className='setup-printer-status';status.id=input.id+'-status';input.setAttribute('aria-describedby',status.id);
    input.addEventListener('input',()=>{for(const item of printerInputs())item.setCustomValidity('');renderConnections();});
    remove.type='button';remove.className='timeline-button';remove.textContent='Entfernen';
    remove.addEventListener('click',()=>{const rows=[...$('setup-printer-list').children],index=rows.indexOf(row);if(rows.length<2||setupSaving)return;row.remove();for(const input of printerInputs())input.setCustomValidity('');updateRows();printerInputs()[Math.min(index,printerInputs().length-1)]?.focus();});
    line.className='setup-printer-fields';line.append(input,remove);row.append(label,line,status);$('setup-printer-list').append(row);updateRows();if(focus)input.focus();
  }
  function connectionFor(ip){return printerStates.find(item=>item.ip===ip);}
  function connectionText(ip){
    if(!printers.includes(ip))return 'Wird nach dem Speichern verbunden.';
    const item=connectionFor(ip),labels={online:'Verbunden',connecting:'Verbindung wird aufgebaut …',offline:'Noch nicht verbunden',stale:'Letzte Daten sind veraltet'};
    return labels[item?.connection]||'Warte auf Druckerdaten …';
  }
  function renderConnections(){
    for(const row of $('setup-printer-list').children){const ip=row.querySelector('input').value.trim(),item=connectionFor(ip),status=row.querySelector('.setup-printer-status');status.textContent=connectionText(ip);status.classList.toggle('is-online',printers.includes(ip)&&item?.connection==='online');}
    if($('setup-done').hidden)return;
    const area=$('setup-connections');area.replaceChildren();
    for(const ip of printers){const row=document.createElement('div'),name=document.createElement('strong'),status=document.createElement('span'),item=connectionFor(ip);row.className='setup-connection';name.textContent=(item?.data?.printer_name||item?.data?.model_name||'Drucker')+' · '+ip;status.textContent=connectionText(ip);status.className=item?.connection==='online'?'is-online':'';row.append(name,status);area.append(row);}
  }
  function configure(){if(!authenticated){login();return;}if(!accountConfigured){account();return;}$('setup-printer-list').replaceChildren();for(const ip of printers.length?printers:[''])addPrinter(ip);$('setup-cancel').hidden=!printers.length;step('printers');}
  $('setup-add-printer').addEventListener('click',()=>addPrinter('',true));
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
    event.preventDefault();$('setup-error').textContent='';
    const inputs=printerInputs(),ips=inputs.map(input=>input.value.trim());
    for(let i=0;i<ips.length;i++){if(ips.indexOf(ips[i])!==i){inputs[i].setCustomValidity('Dieser Drucker steht bereits in der Liste.');inputs[i].reportValidity();return;}}
    setupSaving=true;for(const control of $('setup-printer-form').querySelectorAll('input,button'))control.disabled=true;
    try{
      const response=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':csrf},body:JSON.stringify({printer_ips:ips}),signal:AbortSignal.timeout(10000)});
      if(response.status===401){login();return;}
      const result=await response.json();if(!response.ok)throw new Error(result.error||'Einrichtung konnte nicht gespeichert werden.');
      printers=result.ips;step('done');renderConnections();window.dispatchEvent(new Event('kobra-configured'));
    }catch(error){$('setup-error').textContent=error.message;}
    finally{setupSaving=false;for(const control of $('setup-printer-form').querySelectorAll('input,button'))control.disabled=false;updateRows();}
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
  async function reorder(ips){
    const response=await fetch('/api/order',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':csrf},body:JSON.stringify({printer_ips:ips}),signal:AbortSignal.timeout(10000)});
    if(response.status===401){login();throw new Error('Bitte erneut anmelden.');}
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Reihenfolge konnte nicht gespeichert werden.');
    printers=result.ips;return result.ips;
  }
  async function releaseCameras(viewer){
    if(!authenticated||!accountConfigured)return;
    const response=await fetch('/api/camera/release',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':csrf},body:JSON.stringify({viewer}),signal:AbortSignal.timeout(5000)});
    if(!response.ok)throw new Error('Die vorige Kameraansicht wird automatisch freigegeben.');
  }
  async function notificationRequest(body){
    const response=await fetch('/api/notifications',{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Kobra-CSRF':csrf}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(15000)});
    if(response.status===401){login();throw new Error('Bitte erneut anmelden.');}
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Benachrichtigungen konnten nicht geladen werden.');return result;
  }
  async function spoolRequest(body){
    const response=await fetch('/api/spools',{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Kobra-CSRF':csrf}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(15000)});
    if(response.status===401){login();throw new Error('Bitte erneut anmelden.');}
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Spulenverwaltung nicht erreichbar.');return result;
  }
  return {reorder,releaseCameras,notificationRequest,spoolRequest,ready:boot(),get authenticated(){return authenticated&&accountConfigured;},login,configure,
    setPrinters(ips,states=[]){printers=ips||[];printerStates=states;renderConnections();if(authenticated&&accountConfigured&&!printers.length&&panel.hidden)configure();}};
})();
