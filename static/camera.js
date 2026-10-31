'use strict';
window.kobraCamera=(()=>{
  const $=id=>document.getElementById(id),button=$('camera-open'),image=$('camera-image'),message=$('camera-message');
  let ip='',available=false,opened=false,timer=null,request=null,epoch=0,objectUrl='',lastFrameAt=0;
  function clearImage(){if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl='';lastFrameAt=0;image.removeAttribute('src');image.hidden=true;}
  function close(){opened=false;epoch++;clearTimeout(timer);request?.abort();request=null;clearImage();button.textContent='Kamera anzeigen';button.setAttribute('aria-expanded','false');message.textContent=available?'Das Kamerabild wird nur beim Öffnen geladen.':'Die Kamera benötigt aktuelles FFmpeg auf dem Monitor-Rechner. Im NAS-Paket ist es enthalten.';}
  async function refresh(generation){
    if(!opened||generation!==epoch||document.hidden)return;
    request=new AbortController();let delay=500,nextUrl='';
    try{
      const response=await fetch('/api/camera/frame?ip='+encodeURIComponent(ip),{cache:'no-store',signal:AbortSignal.any([request.signal,AbortSignal.timeout(10000)])});
      if(response.status===401){close();window.kobraAuth?.login();return;}
      if(!response.ok){const result=await response.json();throw new Error(result.error||'Das Kamerabild ist gerade nicht verfügbar.');}
      const frame=await response.blob();
      if(!opened||generation!==epoch)return;
      nextUrl=URL.createObjectURL(frame);
      const nextImage=new Image();nextImage.src=nextUrl;await nextImage.decode();
      if(!opened||generation!==epoch)return;
      // Keep the displayed frame intact until its replacement is decoded.
      const previousUrl=objectUrl;image.src=nextUrl;objectUrl=nextUrl;nextUrl='';image.hidden=false;lastFrameAt=Date.now();
      if(previousUrl)URL.revokeObjectURL(previousUrl);
      message.textContent='Liveansicht · etwa 2 Bilder pro Sekunde · keine Aufzeichnung';
    }catch(error){
      if(!opened||generation!==epoch)return;
      if(lastFrameAt&&Date.now()-lastFrameAt>10000)clearImage();
      const detail=error.name==='AbortError'||error.name==='TimeoutError'?'Verbindung verzögert. Neuer Versuch folgt.':error.message;
      message.textContent=(objectUrl?'Letztes Kamerabild – aktuell keine Live-Aktualisierung. ':'Kein aktuelles Kamerabild. ')+detail;delay=5000;
    }finally{if(nextUrl)URL.revokeObjectURL(nextUrl);if(opened&&generation===epoch)timer=setTimeout(()=>refresh(generation),delay);}
  }
  button.addEventListener('click',()=>{if(opened){close();return;}if(!ip||!available)return;opened=true;const generation=++epoch;button.textContent='Ansicht schließen';button.setAttribute('aria-expanded','true');message.textContent='Kamerabild wird geladen …';refresh(generation);});
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&opened)close();});
  return {close,setPrinter(nextIp,decoderAvailable){if(nextIp!==ip||available!==!!decoderAvailable){ip=nextIp||'';available=!!decoderAvailable;close();}button.disabled=!ip||!available;image.alt='Livebild des Druckers '+ip;}};
})();
