/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
window.kobraOrders=(()=>{
  const $=id=>document.getElementById(id), selected=new Set();
  let scope=null, detail=null, request=0, saving=false;
  const keys=['customer_order','position','part','approval','approver','note'];
  const message=text=>{$('order-message').textContent=text;};
  function versions(){
    const target=$('order-versions');target.replaceChildren();
    if(!detail.versions.length){target.textContent=detail.job.ended_at?'Noch keine Archivversion. „Bericht archivieren“ legt die erste Version ab.':'Der Druck läuft noch. Die erste Version wird nach bestätigtem Ende abgelegt.';return;}
    for(const v of detail.versions){
      const row=document.createElement('div');row.className='report-version';
      const label=document.createElement('p');label.textContent=`Version ${v.version} · ${new Date(v.created_at*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin'})} · ${v.reason}`;
      row.append(label);
      for(const format of ['pdf','json','md']){
        const a=document.createElement('a');a.className='timeline-button';a.textContent=format==='md'?'Markdown':format.toUpperCase();
        a.href='/api/report-export?'+new URLSearchParams({job:detail.job.id,version:String(v.version),format});a.setAttribute('download','');a.setAttribute('aria-label',`${a.textContent} Version ${v.version}`);row.append(a);
      }
      const hash=document.createElement('small');hash.textContent='Archiv-Prüfsumme: '+v.sha256;row.append(hash);target.append(row);
    }
  }
  async function open(job){
    if(saving)return;
    const generation=++request;detail=null;$('order-detail').hidden=false;$('order-form').hidden=true;$('order-versions').replaceChildren();
    $('order-file').textContent=job.filename;message('Auftragsangaben werden geladen …');
    try{
      const result=await window.kobraAuth.orderReport(null,job.id);if(generation!==request)return;
      detail=result;$('order-form').hidden=false;
      for(const key of keys)$('order-'+key).value=detail.annotation[key]||'';
      $('order-archive').disabled=!detail.job.ended_at;
      window.kobraFiles?.forJob(detail);
      message('Änderungen erzeugen bei abgeschlossenen Aufträgen eine neue feste Berichtsversion.');versions();
      $('order-detail').scrollIntoView({behavior:'smooth',block:'start'});
    }catch(e){if(generation===request)message(e.message);}
  }
  async function mutate(body){
    if(saving||!detail)return;saving=true;$('order-save').disabled=true;$('order-archive').disabled=true;message('Wird gespeichert …');
    const job=detail.job.id, generation=request;
    try{
      const result=await window.kobraAuth.orderReport({...body,job});if(generation!==request)return;
      detail=result;versions();message('Gespeichert. Frühere Archivversionen bleiben unverändert.');
      window.dispatchEvent(new Event('kobra-report-changed'));
    }catch(e){if(generation===request)message(e.message);}
    finally{saving=false;$('order-save').disabled=false;$('order-archive').disabled=!detail?.job.ended_at;}
  }
  $('order-form').addEventListener('submit',event=>{
    event.preventDefault();if(!detail)return;
    const annotation={expected_revision:detail.annotation.revision};for(const key of keys)annotation[key]=$('order-'+key).value;
    mutate({action:'save',annotation});
  });
  $('order-archive').addEventListener('click',()=>mutate({action:'archive'}));
  $('order-close').addEventListener('click',()=>{if(saving)return;request++;detail=null;$('order-detail').hidden=true;});
  $('reports-backfill').addEventListener('click',async()=>{
    const button=$('reports-backfill');button.disabled=true;$('reports-message').textContent='Bestehende Abschlüsse werden archiviert …';
    try{const result=await window.kobraAuth.orderReport({action:'backfill'});$('reports-message').textContent=`${result.archived} Berichte neu archiviert. Pro Durchlauf höchstens 100 Abschlüsse.`;window.dispatchEvent(new Event('kobra-report-changed'));}
    catch(e){$('reports-message').textContent=e.message;}finally{button.disabled=false;}
  });
  $('reports-bundle').addEventListener('click',async()=>{
    const button=$('reports-bundle');if(!selected.size){$('reports-message').textContent='Bitte zuerst Aufträge auswählen.';return;}button.disabled=true;
    try{const blob=await window.kobraAuth.orderReport({action:'bundle',jobs:[...selected]});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='Kobra-Auftragsberichte.zip';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);$('reports-message').textContent='ZIP mit PDF, JSON, Markdown und Prüfmanifest heruntergeladen.';}
    catch(e){$('reports-message').textContent=e.message;}finally{button.disabled=false;}
  });
  return {
    originalUpdated(result){if(detail?.job.id===result.job.id){detail=result;versions();}},
    setScope(ip){if(ip!==scope){scope=ip;selected.clear();request++;detail=null;$('order-detail').hidden=true;}},
    decorate(job,file,actions){
      const label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';box.checked=selected.has(job.id);box.disabled=!job.report_version;label.className='report-select';
      box.setAttribute('aria-label','Bericht auswählen: '+job.filename);box.addEventListener('change',()=>{
        if(box.checked&&selected.size>=25){box.checked=false;$('reports-message').textContent='Bitte höchstens 25 Aufträge auswählen.';return;}
        box.checked?selected.add(job.id):selected.delete(job.id);
      });label.append(box,document.createTextNode(job.report_version?'Für ZIP auswählen':'Noch nicht archiviert'));file.append(label);
      const a=job.annotation||{};if(a.customer_order||a.part){const p=document.createElement('p');p.textContent=[a.customer_order,a.position,a.part].filter(Boolean).join(' · ');file.append(p);}
      const button=document.createElement('button');button.type='button';button.className='timeline-button';button.textContent=job.report_version?'Auftrag & Berichte · v'+job.report_version:'Auftrag & Berichte';button.addEventListener('click',()=>open(job));actions.append(button);
    }
  };
})();
