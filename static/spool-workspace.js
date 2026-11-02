/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraSpoolWorkspace=(()=>{
  const $=id=>document.getElementById(id), host=$('spoolman-view-host'), message=$('spoolman-view-message');
  let tab='ace',view='overview',generation=0;
  const ace=[...document.querySelectorAll('section[aria-labelledby="filament-title"],section[aria-labelledby="spools-title"],section.bottom-grid')];
  async function load(){
    const id=++generation;host.replaceChildren();message.textContent='Spoolman wird geladen …';
    try{
      const response=await fetch('/api/spools',{cache:'no-store',signal:AbortSignal.timeout(10000)});
      if(!response.ok)throw new Error(response.status===401?'Bitte im Monitor anmelden.':'Spoolman-Einrichtung gerade nicht verfügbar.');
      const state=await response.json();
      if(id!==generation)return;
      if(!state.configured||new URL(state.url).pathname!=='/spoolman')throw new Error('Die integrierte Ansicht ist noch nicht eingerichtet. Unter ACE & Zuordnung findest du den bisherigen Spoolman-Zugang.');
      const frame=document.createElement('iframe');frame.title='Spoolman Spulenverwaltung';frame.className='spoolman-frame';frame.src='/spoolman/';frame.referrerPolicy='no-referrer';host.append(frame);
      message.textContent='Spoolman bleibt deine zentrale Spulenverwaltung. Eingaben vor einem Bereichswechsel speichern.';
    }catch(error){if(id===generation)message.textContent=error.message||'Spoolman konnte nicht geladen werden.';}
  }
  function render(next){
    view=next;const manage=tab==='manage';
    for(const section of ace)section.classList.toggle('spool-tab-hidden',manage);
    document.querySelector('section[aria-labelledby="spoolman-title"]').classList.toggle('spool-tab-hidden',!manage);
    $('spool-tab-ace').setAttribute('aria-pressed',String(!manage));$('spool-tab-manage').setAttribute('aria-pressed',String(manage));
    if(view==='spools'&&manage){if(!host.children.length)load();}
    else {++generation;host.replaceChildren();}
  }
  $('spool-tab-ace').addEventListener('click',()=>{tab='ace';render(view);});
  $('spool-tab-manage').addEventListener('click',()=>{tab='manage';render(view);});
  $('spoolman-reload').addEventListener('click',()=>{if(view==='spools'&&tab==='manage')load();});
  return {render};
})();
