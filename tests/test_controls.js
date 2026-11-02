'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');const {webcrypto}=require('node:crypto');
function harness(){
 const elements={};
 const ids=['light-control-card','light-control-switch','light-control-dialog','light-control-message',
 'light-control-target','light-control-confirm-target','light-control-confirm-action','light-control-cancel','light-control-apply'];
 for(const id of ids)elements[id]={textContent:'',hidden:false,disabled:false,open:false,attributes:{},listeners:{},
  setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,v){this.listeners[k]=v;},
  showModal(){this.open=true;},close(){this.open=false;}};
 const calls=[],events={};let authenticated=true;
 const window={addEventListener(k,f){events[k]=f;},dispatchEvent(){},kobraAuth:{login(){}}};
 const context={window,document:{getElementById:id=>elements[id]},crypto:webcrypto,Uint8Array,
  AbortSignal,Event,location:{hash:'#overview'},fetch:async(path,options)=>{
   if(path==='/api/session')return {json:async()=>({authenticated,account_configured:true,csrf:'fixture'})};
   const body=JSON.parse(options.body);calls.push(body);
   const result=body.action==='prepare'?{id:'a'.repeat(32),ip:body.ip,desired:body.desired,state:'prepared',token:'fixture'}:
               {state:body.action==='execute'?'confirmed':'cancelled',detail:'Bestätigte Fixture-Rückmeldung.'};
   return {ok:true,status:200,json:async()=>result};
  }};
 vm.runInNewContext(fs.readFileSync('static/controls.js','utf8'),context);
 const data={ip:'192.168.250.1',connection:'online',data:{printer_name:'Testdrucker'},
  light_control:{enabled:true,supported:true},device_status:{light_on:{value:false,age_s:0,current_session:true}}};
 return {elements,calls,events,context,data,render:(d=data,age=0,connection=d.connection)=>window.kobraLightControls.render(d,age,connection),
  click:id=>elements[id].listeners.click(),setAuthenticated:v=>authenticated=v};
}
(async()=>{
 let h=harness();h.render();assert.equal(h.elements['light-control-switch'].disabled,false);
 assert.equal(h.elements['light-control-switch'].attributes['aria-checked'],'false');
 h.render({...h.data,light_control:{enabled:false}});assert.equal(h.elements['light-control-card'].hidden,true);
 h=harness();for(const change of [{connection:'offline'},{device_status:{}},{light_control:{enabled:true,supported:false}},
 {device_status:{light_on:{value:0,age_s:0,current_session:true}}},
 {device_status:{light_on:{value:false,age_s:0,current_session:false}}}]){
  h.render({...h.data,...change});assert.equal(h.elements['light-control-switch'].disabled,true);
 }
 h.render(h.data,16);assert.equal(h.elements['light-control-switch'].disabled,true);
 h.render(h.data,0,'offline');assert.equal(h.elements['light-control-switch'].disabled,true);
 h=harness();h.render();await h.click('light-control-switch');
 assert.equal(h.elements['light-control-dialog'].open,true);assert.equal(h.calls.length,1);
 assert.equal(h.calls[0].desired,true);assert.equal(h.elements['light-control-switch'].attributes['aria-checked'],'false');
 h.click('light-control-cancel');await new Promise(setImmediate);
 assert.deepEqual(h.calls.map(c=>c.action),['prepare','cancel']);assert.equal(h.elements['light-control-dialog'].open,false);
 h=harness();h.render();await h.click('light-control-switch');
 await Promise.all([h.click('light-control-apply'),h.click('light-control-apply')]);
 assert.equal(h.calls.filter(c=>c.action==='execute').length,1);
 assert.equal(h.elements['light-control-message'].textContent,'Bestätigte Fixture-Rückmeldung.');
 assert.equal(h.elements['light-control-switch'].attributes['aria-checked'],'false');
 h.render({...h.data,device_status:{light_on:{value:true,age_s:0,current_session:true}}});
 assert.equal(h.elements['light-control-switch'].attributes['aria-checked'],'true');
 h=harness();h.render();await h.click('light-control-switch');h.render({...h.data,ip:'192.168.250.2'});
 await new Promise(setImmediate);assert.equal(h.elements['light-control-dialog'].open,false);
 assert.equal(h.calls.filter(c=>c.action==='execute').length,0);assert.equal(h.calls.filter(c=>c.action==='cancel').length,1);
 h=harness();h.render();await h.click('light-control-switch');h.context.location.hash='#spools';h.events.hashchange();
 await new Promise(setImmediate);assert.equal(h.elements['light-control-dialog'].open,false);assert.equal(h.calls.at(-1).action,'cancel');
 h=harness();h.render();h.setAuthenticated(false);await h.click('light-control-switch');
 assert.equal(h.calls.length,0);assert.match(h.elements['light-control-message'].textContent,/anmelden/);
 console.log('8 control UI cases passed: allowlist, freshness, prepare, cancel, single dispatch/telemetry, printer switch, navigation, expired login');
})().catch(e=>{console.error(e);process.exit(1);});
