'use strict';
// Each tile owns only its display/request state. Decoders are shared on the server.
window.KobraCameraFrame=class {
  constructor(ip,image,message,viewer,onUnauthorized,onChange=()=>{}){Object.assign(this,{ip,image,message,viewer,onUnauthorized,onChange,opened:false,epoch:0,objectUrl:'',lastFrameAt:0});}
  clearImage(){if(this.objectUrl)URL.revokeObjectURL(this.objectUrl);this.objectUrl='';this.lastFrameAt=0;this.image.removeAttribute('src');this.image.hidden=true;this.onChange();}
  close(){this.opened=false;this.epoch++;clearTimeout(this.timer);this.request?.abort();this.clearImage();}
  open(){this.opened=true;this.message.textContent='Kamerabild wird geladen …';this.refresh(++this.epoch);}
  async refresh(generation){
    if(!this.opened||generation!==this.epoch||document.hidden)return;
    this.request=new AbortController();let delay=500,nextUrl='';
    try{
      const query=new URLSearchParams({ip:this.ip,viewer:this.viewer});
      const response=await fetch('/api/camera/frame?'+query,{cache:'no-store',signal:AbortSignal.any([this.request.signal,AbortSignal.timeout(10000)])});
      if(response.status===401){this.onUnauthorized();return;}
      if(!response.ok){const result=await response.json();throw new Error(result.error||'Das Kamerabild ist gerade nicht verfügbar.');}
      const frame=await response.blob();if(!this.opened||generation!==this.epoch)return;
      nextUrl=URL.createObjectURL(frame);const nextImage=new Image();nextImage.src=nextUrl;await nextImage.decode();
      if(!this.opened||generation!==this.epoch)return;
      const previousUrl=this.objectUrl;this.image.src=nextUrl;this.objectUrl=nextUrl;nextUrl='';this.image.hidden=false;this.lastFrameAt=Date.now();
      if(previousUrl)URL.revokeObjectURL(previousUrl);
      this.message.textContent='Liveansicht · etwa 2 Bilder pro Sekunde · keine Aufzeichnung';this.onChange();
    }catch(error){
      if(!this.opened||generation!==this.epoch)return;
      if(this.lastFrameAt&&Date.now()-this.lastFrameAt>10000)this.clearImage();
      const detail=error.name==='AbortError'||error.name==='TimeoutError'?'Verbindung verzögert. Neuer Versuch folgt.':error.message;
      this.message.textContent=(this.objectUrl?'Letztes Kamerabild – aktuell keine Live-Aktualisierung. ':'Kein aktuelles Kamerabild. ')+detail;this.onChange();delay=5000;
    }finally{if(nextUrl)URL.revokeObjectURL(nextUrl);if(this.opened&&generation===this.epoch)this.timer=setTimeout(()=>this.refresh(generation),delay);}
  }
};
window.kobraCamera=(()=>{
  const $=id=>document.getElementById(id),button=$('camera-open'),image=$('camera-image'),message=$('camera-message'),mode=$('camera-mode'),size=$('camera-page-size'),grid=$('camera-grid'),pager=$('camera-pagination');
  let ip='',available=false,decoderMessage='',opened=false,printers=[],page=0,views=[],viewer='',epoch=0;
  const dialog=$('camera-dialog'),dialogContent=$('camera-dialog-content'),enlarge=$('camera-enlarge');
  let expanded=null;
  function restoreExpanded(){
    if(!expanded)return;
    const saved=expanded;expanded=null;
    for(const entry of saved.items)entry.marker.replaceWith(entry.node);
    saved.trigger.focus?.();
  }
  function shrink(){if(dialog?.open)dialog.close();restoreExpanded();}
  function expand(targetImage,targetMessage,trigger){
    if(!dialog?.showModal||targetImage.hidden||!targetImage.src)return;
    shrink();
    expanded={trigger,items:[targetImage,targetMessage].map(node=>{const marker=document.createComment('camera-position');node.before(marker);return {node,marker};})};
    dialogContent.append(targetImage,targetMessage);dialog.showModal();
  }
  dialog?.addEventListener('close',restoreExpanded);
  $('camera-shrink')?.addEventListener('click',shrink);
  enlarge?.addEventListener('click',()=>expand(image,message,enlarge));
  function updateEnlarge(){if(enlarge)enlarge.disabled=!opened||mode.value!=='single'||image.hidden;}
  mode.value='single';size.value='4';
  const pages=()=>Math.max(1,Math.ceil(printers.length/Number(size.value)));
  const visible=()=>mode.value==='all'?printers.slice(page*Number(size.value),(page+1)*Number(size.value)):[{ip}];
  function controls(){
    const all=mode.value==='all';page=Math.min(page,pages()-1);size.parentElement.hidden=!all;pager.hidden=!all||pages()<2;grid.hidden=!all;
    $('camera-page-label').textContent=`Seite ${page+1} von ${pages()} · ${printers.length} Kameras`;
    $('camera-prev').disabled=page===0;$('camera-next').disabled=page>=pages()-1;
    button.disabled=!available||(!all&&!ip)||(all&&!printers.length);button.textContent=opened?'Ansicht schließen':all?'Kameras anzeigen':'Kamera anzeigen';button.setAttribute('aria-expanded',String(opened));updateEnlarge();
  }
  function stopViews(){shrink();const oldViewer=viewer;viewer='';for(const view of views)view.close();views=[];grid.replaceChildren();image.hidden=true;updateEnlarge();
    return oldViewer?Promise.resolve(window.kobraAuth?.releaseCameras?.(oldViewer)).catch(()=>{}):Promise.resolve();}
  function close(){opened=false;epoch++;stopViews();controls();message.textContent=available?'Das Kamerabild wird nur beim Öffnen geladen.':decoderMessage||'Die Videoaufbereitung auf dem Monitor-Server wird geprüft. Auf Handy oder Mac als Anzeigegerät ist keine Installation nötig.';}
  async function show(){
    const generation=++epoch;message.textContent='Kameraansicht wird geladen …';await stopViews();
    if(!opened||generation!==epoch||document.hidden)return;
    viewer=Array.from(crypto.getRandomValues(new Uint8Array(16)),byte=>byte.toString(16).padStart(2,'0')).join('');controls();const all=mode.value==='all';
    message.textContent=all?'Nur die Kameras dieser Seite werden geladen. Keine Aufzeichnung.':'Kamerabild wird geladen …';
    for(const printer of visible()){
      let targetImage=image,targetMessage=message,tileEnlarge=null;
      if(all){
        const tile=document.createElement('article');tile.className='camera-tile';const title=document.createElement('h3');title.textContent=printer.data?.printer_name||printer.data?.model_name||'Drucker';
        const address=document.createElement('p');address.className='camera-address';address.textContent=printer.ip;
        targetImage=document.createElement('img');targetImage.className='camera-image';targetImage.hidden=true;targetMessage=document.createElement('p');targetMessage.className='camera-message';
        tileEnlarge=document.createElement('button');tileEnlarge.type='button';tileEnlarge.className='timeline-button camera-enlarge-tile';tileEnlarge.textContent='Vergrößern';tileEnlarge.disabled=true;tileEnlarge.addEventListener('click',()=>expand(targetImage,targetMessage,tileEnlarge));tile.append(title,address,targetImage,targetMessage,tileEnlarge);grid.append(tile);
      }
      targetImage.alt='Livebild des Druckers '+printer.ip;
      const view=new window.KobraCameraFrame(printer.ip,targetImage,targetMessage,viewer,()=>{close();window.kobraAuth?.login();},()=>{updateEnlarge();if(tileEnlarge)tileEnlarge.disabled=targetImage.hidden;});views.push(view);view.open();
    }
  }
  function change(){controls();if(opened)show();}
  button.addEventListener('click',()=>{if(opened){close();return;}if(button.disabled)return;opened=true;controls();show();});
  mode.addEventListener('change',()=>{page=0;change();});size.addEventListener('change',()=>{page=0;change();});
  $('camera-prev').addEventListener('click',()=>{if(page>0){page--;change();}});$('camera-next').addEventListener('click',()=>{if(page<pages()-1){page++;change();}});
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&opened)close();});
  return {close,setPrinters(next){
    const before=visible().map(p=>p.ip).join(',');printers=next||[];controls();
    if(opened&&mode.value==='all'&&before!==visible().map(p=>p.ip).join(','))show();
    if(mode.value==='all')grid.querySelectorAll('.camera-tile').forEach((tile,i)=>{const p=visible()[i];if(p)tile.querySelector('h3').textContent=p.data?.printer_name||p.data?.model_name||'Drucker';});
  },setPrinter(nextIp,decoderAvailable,availabilityMessage){
    decoderMessage=availabilityMessage||'';
    const changed=ip!==(nextIp||'');ip=nextIp||'';const availabilityChanged=available!==!!decoderAvailable;available=!!decoderAvailable;
    if(availabilityChanged||changed&&mode.value==='single')close();controls();image.alt='Livebild des Druckers '+ip;
  }};
})();
