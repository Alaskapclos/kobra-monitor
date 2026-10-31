/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraNotifications=(()=>{
  const $=id=>document.getElementById(id);
  let state=null,busy=false;
  const storageKey='kobra-push-device';
  const ownId=()=>{try{return localStorage.getItem(storageKey)||'';}catch{return '';}};
  function remember(id){try{if(id)localStorage.setItem(storageKey,id);else localStorage.removeItem(storageKey);}catch{}}
  function support(){
    if(!window.isSecureContext)return 'Öffne den Monitor über seine HTTPS-Adresse. Auf der gewöhnlichen LAN-Adresse sind Handy-Benachrichtigungen nicht verfügbar.';
    const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
    if(ios&&!window.matchMedia('(display-mode: standalone)').matches&&!navigator.standalone)return 'Auf dem iPhone oder iPad: Öffne diese HTTPS-Adresse in Safari. Tippe auf Teilen → Zum Home-Bildschirm. Öffne Kobra Monitor anschließend über das neue Symbol und melde dich dort an. Ab iOS/iPadOS 16.4.';
    if(!('serviceWorker' in navigator)||!('PushManager' in window)||!('Notification' in window))return 'Dieser Browser unterstützt keine Push-Meldungen. Verwende einen aktuellen unterstützten Browser; auf iPhone und iPad die Home-Bildschirm-App.';
    if(Notification.permission==='denied')return 'Benachrichtigungen sind für diesen Monitor im Gerät gesperrt. Erlaube sie zuerst in den Browser- oder Systemeinstellungen und lade die Seite neu.';
    return '';
  }
  function prefs(){return {completed:$('notify-completed').checked,errors:$('notify-errors').checked,disconnect:$('notify-disconnect').checked,delay_seconds:Number($('notify-delay').value)};}
  function message(text){$('notify-message').textContent=text;}
  function render(){
    const reason=support();$('notify-help').textContent=reason||'Aktiviere Meldungen auf jedem gewünschten Gerät einmal. Das NAS muss laufen und den Push-Dienst im Internet erreichen können. Zum Öffnen des Monitors von unterwegs brauchst du weiterhin Tailscale oder dein VPN.';
    $('notify-enable').disabled=busy||!!reason||!state;
    $('notify-enable').textContent=state?.devices.some(d=>d.id===ownId())?'Auswahl für dieses Gerät speichern':'Auf diesem Gerät aktivieren';
    const area=$('notify-devices');area.replaceChildren();
    if(!state?.devices.length){const p=document.createElement('p');p.textContent='Noch kein Gerät angemeldet.';area.append(p);return;}
    const labels={ready:'Bereit · noch keine Meldung gesendet',accepted:'Zuletzt an den Push-Dienst übergeben',retrying:'Zustellung wird erneut versucht',failed:'Zustellung fehlgeschlagen · Gerät prüfen'};
    for(const device of state.devices){
      const row=document.createElement('div'),description=document.createElement('div'),name=document.createElement('strong'),status=document.createElement('p'),actions=document.createElement('div');row.className='notify-device';actions.className='notify-actions';
      name.textContent=device.label+(device.id===ownId()?' · dieses Gerät':'');status.textContent=labels[device.last_status]||'Bereit';description.append(name,status);
      for(const [label,action] of [['Testmeldung senden','test'],['Entfernen','remove']]){const button=document.createElement('button');button.type='button';button.className='timeline-button';button.textContent=label;button.disabled=busy;button.addEventListener('click',()=>act(async()=>{
        await window.kobraAuth.notificationRequest({action,id:device.id});
        if(action==='remove'&&device.id===ownId()){
          remember('');const registration=await navigator.serviceWorker?.getRegistration('/');const sub=await registration?.pushManager.getSubscription();if(sub)await sub.unsubscribe();
        }
        await load();message(action==='test'?'Die Testmeldung ist vorgemerkt. Prüfe gleich die Benachrichtigungen auf dem ausgewählten Gerät.':'Das Gerät wurde entfernt. Es erhält keine neuen Meldungen.');
      }));actions.append(button);}
      row.append(description,actions);area.append(row);
    }
  }
  async function load(){
    state=await window.kobraAuth.notificationRequest();
    const device=state.devices.find(d=>d.id===ownId());
    if(device){$('notify-label').value=device.label;for(const k of ['completed','errors','disconnect'])$('notify-'+k).checked=device.preferences[k];$('notify-delay').value=String(device.preferences.delay_seconds);}
    render();
  }
  async function act(fn){if(busy)return;busy=true;render();message('');try{await fn();}catch(error){message(error.message||'Bitte erneut versuchen.');}finally{busy=false;render();}}
  $('notify-open').addEventListener('click',()=>{
    const open=$('notify-settings').hidden;$('notify-settings').hidden=!open;$('notify-open').setAttribute('aria-expanded',String(open));$('notify-open').textContent=open?'Schließen':'Einrichten';
    if(open)act(load);
  });
  $('notify-refresh').addEventListener('click',()=>act(load));
  $('notify-enable').addEventListener('click',()=>{
    if(busy||support())return;
    // Permission must be requested directly from this user gesture, especially on iOS.
    const permission=Notification.requestPermission();
    act(async()=>{
      if(await permission!=='granted')throw new Error('Benachrichtigungen wurden nicht erlaubt. Es wurde kein Gerät angemeldet.');
      const registration=await navigator.serviceWorker.register('/service-worker.js',{scope:'/'});
      await navigator.serviceWorker.ready;
      let sub=await registration.pushManager.getSubscription();let created=false;
      if(!sub){const raw=state.public_key.replace(/-/g,'+').replace(/_/g,'/');const bytes=Uint8Array.from(atob(raw+'='.repeat((4-raw.length%4)%4)),c=>c.charCodeAt(0));sub=await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:bytes});created=true;}
      try{
        const result=await window.kobraAuth.notificationRequest({action:'subscribe',subscription:sub.toJSON(),label:$('notify-label').value.trim(),preferences:prefs()});remember(result.id);
      }catch(error){if(created)await sub.unsubscribe();throw error;}
      await load();message('Dieses Gerät ist angemeldet. Sende jetzt eine Testmeldung, um den Empfang zu prüfen.');
    });
  });
  return {support};
})();
