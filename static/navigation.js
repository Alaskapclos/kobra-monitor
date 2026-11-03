/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
(()=>{
  const links=[...document.querySelectorAll('[data-view]')], main=document.querySelector('main');
  const groups={overview:[],orders:[],spools:[],settings:[]};
  for(const section of main.querySelectorAll(':scope > section')){
    if(section.classList.contains('page-heading'))continue;
    const label=section.getAttribute('aria-labelledby');
    const view=['history-title','order-title','timeline-title','files-title'].includes(label)?'orders':
      ['filament-title','spools-title','spooltabs-title','spoolman-title'].includes(label)||section.classList.contains('bottom-grid')?'spools':
      ['notify-title','check-title','help-title'].includes(label)?'settings':'overview';
    groups[view].push(section);
  }
  let current='overview';
  function navigate(){
    const hash=location.hash.slice(1), view=hash==='help'?'settings':hash==='printer-switcher'?'overview':Object.hasOwn(groups,hash)?hash:'overview';
    if(current==='overview'&&view!=='overview')window.kobraCamera?.close();
    current=view;
    for(const [name,sections] of Object.entries(groups))for(const section of sections)section.classList.toggle('workspace-hidden',name!==view);
    window.kobraSpoolWorkspace?.render(view);
    const picker=document.getElementById('printer-switcher');if(picker)picker.classList.toggle('workspace-hidden',view==='settings');
    for(const a of links){if(a.dataset.view===view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');}
    const titles={overview:['Deine Druckerübersicht.','Live-Status und Kameras im Blick.'],orders:['Druckaufträge & Berichte.','Kundenaufträge zuordnen, Qualität abnehmen und feste Berichte ablegen.'],spools:['Deine Spulen.','ACE-Daten und Spoolman-Bestand mit klarer Zuordnung.'],settings:['Betrieb & Hilfe.','Benachrichtigungen, Verbindungen und Bedienung.']};
    const heading=main.querySelector('.page-heading');heading.querySelector('h1').textContent=titles[view][0];heading.querySelector('p').textContent=titles[view][1];
    const crumb=main.querySelector('.breadcrumb');if(crumb)crumb.textContent='Werkstatt / '+({overview:'Übersicht',orders:'Druckaufträge',spools:'Spulen',settings:'Betrieb & Hilfe'}[view]);
    if(hash==='help')document.getElementById('help').scrollIntoView({block:'start'});else main.scrollIntoView({block:'start'});
  }
  window.addEventListener('hashchange',navigate);navigate();
})();
