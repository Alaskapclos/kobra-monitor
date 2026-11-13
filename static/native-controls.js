'use strict';
(()=>{
  const $=id=>document.getElementById(id);
  let state=null,busy=false,generation=0;
  const area=$('native-controls-settings'),form=$('native-controls-form'),list=$('native-controls-list'),message=$('native-controls-message');
  if(!area)return;
  async function load(show){
    const current=++generation;form.hidden=true;message.textContent='';
    try{
      const result=await window.kobraAuth.nativeControls();
      if(current!==generation||!window.kobraAuth.authenticated)return;
      state=result;area.hidden=!result.available;
      if(!result.available||!show)return;
      list.replaceChildren();
      for(const ip of result.printer_ips){
        const field=document.createElement('fieldset'),legend=document.createElement('legend');legend.textContent=ip;field.dataset.ip=ip;field.append(legend);
        const row=result.grants[ip]||{controls:[],drying_limit:55};
        for(const [scope,title] of Object.entries(result.scopes)){
          const label=document.createElement('label'),input=document.createElement('input'),text=document.createElement('span');
          input.type='checkbox';input.value=scope;input.checked=row.controls.includes(scope);text.textContent=title;label.append(input,text);field.append(label);
        }
        const label=document.createElement('label'),select=document.createElement('select'),text=document.createElement('span');
        text.textContent='Obergrenze der ACE-Trocknung';select.className='native-drying-limit';
        for(const value of [55,65]){const option=document.createElement('option');option.value=String(value);option.textContent=value+' °C'+(value===65?' – nur für einen dafür geeigneten ACE':'');select.append(option);}
        select.value=String(row.drying_limit);label.append(text,select);field.append(label);list.append(field);
      }
      form.hidden=false;
    }catch(error){if(current===generation&&show)message.textContent=error.message;}
  }
  $('native-controls-open').addEventListener('click',()=>load(true));
  window.addEventListener('kobra-setup-opened',()=>load(false));
  window.addEventListener('kobra-authenticated',()=>load(false));
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!state||!window.kobraAuth.authenticated)return;
    const grants={},lines=[];
    for(const field of list.querySelectorAll('fieldset')){
      const controls=Array.from(field.querySelectorAll('input:checked')).map(input=>input.value),drying_limit=Number(field.querySelector('select').value);
      grants[field.dataset.ip]={controls,drying_limit};
      lines.push(field.dataset.ip+': '+(controls.length?controls.map(key=>state.scopes[key]).join(', '):'nur lesen')+(controls.includes('drying')?' (max. '+drying_limit+' °C)':''));
    }
    if(!window.confirm('Diese Steuerungsfreigaben dauerhaft für diesen Kobra Monitor speichern?\n\n'+lines.join('\n')+'\n\nÄnderungen gelten erst nach vollständigem Beenden und erneutem Start. Achsen und Homing nur direkt vor dem Drucker verwenden. Das Speichern sendet keine Druckerbefehle.'))return;
    busy=true;const button=form.querySelector('button');button.disabled=true;
    try{
      const result=await window.kobraAuth.nativeControls({printer_ips:state.printer_ips,revision:state.revision,grants,confirmed:true});
      state=result;form.hidden=true;message.textContent='Gespeichert. Jetzt Kobra Monitor vollständig schließen und erneut starten; bei Docker den Monitor-Container neu starten. Danach gelten diese Freigaben auch bei weiteren Neustarts.';
    }catch(error){message.textContent=error.message;}
    finally{busy=false;button.disabled=false;}
  });
})();
