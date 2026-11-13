/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraAceControls=(()=>{
  const $=id=>document.getElementById(id),dialog=$('ace-drying-dialog');
  const printers=new Map();let active=null,generation=0,busyIp=null,renderedAt=Date.now();
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  function fresh(unit,key,p,extra=0,limit=60){return p.connection==='online'&&!p.unavailable&&extra<=10&&unit.current?.[key]===true&&finite(unit.ages?.[key])&&unit.ages[key]>=0&&unit.ages[key]+extra<=limit&&finite(unit[key]);}
  function current(ip,box){const p=printers.get(ip),u=p?.ace_climate?.find(u=>u.id===box),extra=p? p.extra+(Date.now()-p.renderedAt)/1000:999;return {p,u,extra};}
  function controllable(p,u,extra){return p?.drying_control?.enabled===true&&p.drying_control.supported===true&&u&&[0,1].includes(u.status)&&fresh(u,'status',p,extra,15);}
  function say(text){const p=$('ace-drying-message');if(p){p.textContent=text;p.hidden=!text;}}
  function close(){generation++;active=null;if(dialog?.open)dialog.close();}
  function renderTile(tile,printer,extra=0,unavailable=false){
    const p={...printer,extra,unavailable,renderedAt:Date.now()};printers.set(p.ip,p);
    let area=tile.querySelector('.picker-ace-climate');
    if(!area){area=document.createElement('div');area.className='picker-ace-climate';tile.append(area);area.units=new Map();}
    const units=Array.isArray(p.ace_climate)?p.ace_climate:[],ids=new Set(units.map(u=>u.id));
    for(const [id,row] of area.units)if(!ids.has(id)){row.remove();area.units.delete(id);}
    area.hidden=units.length===0;
    for(const u of units){
      let row=area.units.get(u.id);
      if(!row){
        row=document.createElement('div');row.className='picker-climate-unit';
        for(const cls of ['title','temp','humidity','state','remaining']){const s=document.createElement('span');s.className='ace-climate-'+cls;row.append(s);}
        const toggle=document.createElement('button');toggle.type='button';toggle.className='ace-drying-switch';toggle.setAttribute('role','switch');toggle.setAttribute('aria-haspopup','dialog');
        toggle.addEventListener('click',()=>open(p.ip,u.id));row.append(toggle);row.toggle=toggle;area.units.set(u.id,row);area.append(row);
      }
      const text=(key,value)=>{row.querySelector('.ace-climate-'+key).textContent=value;};
      text('title',units.length>1?'ACE '+(u.id+1):'ACE-Klima');
      text('temp',fresh(u,'current_temp',p,extra)?Math.round(u.current_temp)+' °C':'Temperatur —');
      text('humidity',fresh(u,'humidity',p,extra)?Math.round(u.humidity)+' % rF':'Luftfeuchte —');
      const known=fresh(u,'status',p,extra)&&[0,1].includes(u.status);
      text('state',known?(u.status===1?'Trocknung an':'Trocknung aus'):'Trocknung unbekannt');
      const minutes=fresh(u,'remain_time',p,extra)?u.remain_time:null;
      text('remaining',known&&u.status===1&&minutes!==null?'Noch '+Math.floor(minutes/60)+' h '+minutes%60+' min':'');
      row.toggle.textContent=known&&u.status===1?'Ausschalten':'Einschalten';row.toggle.dataset.on=String(known&&u.status===1);
      row.toggle.setAttribute('aria-checked',String(known&&u.status===1));
      row.toggle.setAttribute('aria-label',`${p.data?.printer_name||p.ip}, ACE ${u.id+1}: Trocknung ${known?(u.status?'ausschalten':'einschalten'):'unbekannt'}`);
      row.toggle.disabled=busyIp===p.ip||!controllable(p,u,extra);
      row.toggle.hidden=p.drying_control?.enabled!==true;
    }
    if(active?.ip===p.ip){const {u,extra:age}=current(active.ip,active.box);if(!controllable(p,u,age)||u.configuration!==active.configuration){close();say('ACE-Zustand geändert oder veraltet; bitte erneut öffnen.');}}
  }
  function open(ip,box){
    const {p,u,extra}=current(ip,box);if(!dialog||busyIp||!controllable(p,u,extra))return;
    close();say('');active={ip,box,on:u.status===0,configuration:u.configuration,before:u.status,maximum:p.drying_control.max_temperature===65?65:55};
    $('ace-drying-title').textContent=active.on?'Trocknung einschalten':'Trocknung ausschalten';
    $('ace-drying-target').textContent=(p.data?.printer_name||ip)+' · '+ip+' · ACE '+(box+1);
    $('ace-drying-settings').hidden=!active.on;
    $('ace-drying-temperature').max=String(active.maximum);$('ace-drying-temperature-label').textContent='Temperatur (30–'+active.maximum+' °C)';
    $('ace-drying-temperature').value=fresh(u,'target_temp',p,extra,15)&&u.target_temp>=30&&u.target_temp<=active.maximum?String(u.target_temp):'';
    $('ace-drying-duration').value=fresh(u,'duration',p,extra,15)&&u.duration>=10&&u.duration<=1440?String(u.duration):'';
    $('ace-drying-note').textContent=active.on?'Der ACE heizt alle eingelegten Spulen. Temperatur und Dauer passend zu Filament und Spulenkörper wählen.':'Die Heizung dieses ACE wird ausgeschaltet. Der Druck wird dadurch nicht abgebrochen.';
    validate();dialog.showModal();(active.on?$('ace-drying-temperature'):$('ace-drying-ok')).focus();
  }
  function validate(){
    const t=$('ace-drying-temperature'),d=$('ace-drying-duration');
    $('ace-drying-ok').disabled=!active||(active.on&&(!t.value.trim()||!d.value.trim()||!Number.isInteger(Number(t.value))||Number(t.value)<30||Number(t.value)>active.maximum||!Number.isInteger(Number(d.value))||Number(d.value)<10||Number(d.value)>1440));
  }
  async function api(body,guard=()=>true,dispatch=()=>{}){
    const session=await (await fetch('/api/session',{signal:AbortSignal.timeout(5000)})).json();
    if(!session.authenticated||!session.account_configured)throw Error('Bitte erneut anmelden.');
    if(!guard())throw Error('ACE oder Zustand geändert; nicht gesendet.');dispatch();
    const r=await fetch('/api/drying',{method:'POST',headers:{'Content-Type':'application/json','X-Kobra-CSRF':session.csrf},body:JSON.stringify(body),signal:AbortSignal.timeout(22000)}),data=await r.json();
    if(!r.ok)throw Error(data.error||'Trocknungsauftrag nicht bestätigt.');return data;
  }
  if(dialog){
    for(const id of ['ace-drying-temperature','ace-drying-duration'])$(id).addEventListener('input',validate);
    $('ace-drying-cancel').addEventListener('click',close);dialog.addEventListener('cancel',close);
    $('ace-drying-ok').addEventListener('click',async()=>{
      if(!active||busyIp||$('ace-drying-ok').disabled)return;
      const chosen={...active},mark=++generation;active=null;dialog.close();busyIp=chosen.ip;
      const valid=()=>{const {p,u,extra}=current(chosen.ip,chosen.box);return mark===generation&&controllable(p,u,extra)&&u.configuration===chosen.configuration&&u.status===chosen.before;};
      const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
      const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
      const key=`${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
      let intent=null,dispatched=false;say('Trocknung: Übernahme wird geprüft …');
      try{
        intent=await api({action:'prepare',ip:chosen.ip,box:chosen.box,on:chosen.on,temperature:chosen.on?Number($('ace-drying-temperature').value):null,duration:chosen.on?Number($('ace-drying-duration').value):null,request_id:key},valid);
        if(intent.state!=='prepared'){say(intent.detail);return;}
        const result=await api({action:'execute',id:intent.id,token:intent.token},valid,()=>{dispatched=true;});intent=null;say(result.detail);
      }catch(e){if(intent&&!dispatched)api({action:'cancel',id:intent.id}).catch(()=>{});say(e.message+(dispatched?' Ausgang unklar; kein automatischer Neuversuch.':''));}
      finally{busyIp=null;window.dispatchEvent(new Event('kobra-control-changed'));}
    });
    window.addEventListener('hashchange',()=>{if(location.hash!=='#overview')close();});window.addEventListener('pagehide',close);
    window.addEventListener('kobra-auth-changed',()=>{close();printers.clear();});
  }
  return {renderTile,close,fresh,resetSession(){close();printers.clear();say('');}};
})();
