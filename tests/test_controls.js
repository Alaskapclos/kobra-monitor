'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {webcrypto}=require('node:crypto'),flush=()=>new Promise(setImmediate);
function harness(){
 const elements={};for(const id of ['light-control-switch','light-control-message'])elements[id]={textContent:'',hidden:false,disabled:false,attributes:{},listeners:{},setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,v){this.listeners[k]=v;}};
 const calls=[],events={};let authenticated=true,count=0,held=0,release=null,unchanged=false,fail=false;
 const window={addEventListener(k,f){events[k]=f;},dispatchEvent(){},kobraAuth:{login(){}}};
 const context={window,document:{getElementById:id=>elements[id]},crypto:webcrypto,Uint8Array,AbortSignal,Event,location:{hash:'#overview'},fetch:async(path,options)=>{
  if(path==='/api/session'){if(++count===held)await new Promise(r=>release=r);return {json:async()=>({authenticated,account_configured:true,csrf:'fixture'})};}
  const body=JSON.parse(options.body);calls.push(body);if(body.action==='execute'&&fail)throw Error('Fixture failure');
  const result=body.action==='prepare'?{id:'a'.repeat(32),ip:body.ip,desired:body.desired,state:unchanged?'unchanged':'prepared',token:'fixture',detail:'Bereits so gemeldet.'}:{state:'confirmed',detail:'Fixture-Rückmeldung.'};
  return {ok:true,status:200,json:async()=>result};
 }};
 vm.runInNewContext(fs.readFileSync('static/controls.js','utf8'),context);
 const data={ip:'192.168.250.1',connection:'online',light_control:{enabled:true,supported:true},device_status:{light_on:{value:false,age_s:0,current_session:true}}};
 return {elements,calls,events,context,data,render:(d=data,age=0,connection=d.connection)=>window.kobraLightControls.render(d,age,connection),click:()=>elements['light-control-switch'].listeners.click(),hold:n=>held=n,release:()=>release(),expire:()=>authenticated=false,unchanged:()=>unchanged=true,fail:()=>fail=true};
}
(async()=>{
 let h=harness();h.render();assert.equal(h.elements['light-control-switch'].disabled,false);h.render({...h.data,light_control:{enabled:false}});assert.equal(h.elements['light-control-switch'].hidden,true);
 const html=fs.readFileSync('static/index.html','utf8');assert(!html.includes('light-control-dialog'));assert(!html.includes('light-control-card'));
 assert(html.indexOf('id="light-control-switch"')>html.indexOf('id="device-light-icon"'));assert(html.indexOf('id="light-control-switch"')<html.indexOf('id="device-light_on"'));
 h=harness();for(const change of [{connection:'offline'},{device_status:{}},{light_control:{enabled:true,supported:false}},{device_status:{light_on:{value:0,age_s:0,current_session:true}}},{device_status:{light_on:{value:false,age_s:0,current_session:false}}}]){h.render({...h.data,...change});assert.equal(h.elements['light-control-switch'].disabled,true);await h.click();}
 for(const age of [16,NaN,-1]){h.render(h.data,age);assert.equal(h.elements['light-control-switch'].disabled,true);}assert.equal(h.calls.length,0);
 h=harness();h.render();await h.click();assert.deepEqual(h.calls.map(c=>c.action),['prepare','execute']);assert.equal(h.calls[0].desired,true);assert.equal(h.elements['light-control-switch'].attributes['aria-checked'],'false');h.render({...h.data,device_status:{light_on:{value:true,age_s:0,current_session:true}}});assert.equal(h.elements['light-control-switch'].attributes['aria-checked'],'true');
 h=harness();h.render();await Promise.all([h.click(),h.click()]);assert.equal(h.calls.filter(c=>c.action==='execute').length,1);
 h=harness();h.render();h.unchanged();await h.click();assert.deepEqual(h.calls.map(c=>c.action),['prepare']);
 h=harness();h.render();h.hold(1);let pending=h.click();await flush();h.render({...h.data,ip:'192.168.250.2'});h.release();await pending;assert.equal(h.calls.length,0);
 h=harness();h.render();h.hold(2);pending=h.click();await flush();assert.equal(h.calls[0].action,'prepare');h.render({...h.data,ip:'192.168.250.2'});h.release();await pending;await flush();assert.deepEqual(h.calls.map(c=>c.action),['prepare','cancel']);
 h=harness();h.render();h.hold(1);pending=h.click();await flush();h.context.location.hash='#spools';h.events.hashchange();h.release();await pending;assert.equal(h.calls.length,0);
 h=harness();h.render();h.expire();await h.click();assert.equal(h.calls.length,0);assert.match(h.elements['light-control-message'].textContent,/anmelden/);
 h=harness();h.render();h.fail();await h.click();assert.equal(h.calls.filter(c=>c.action==='execute').length,1);assert.match(h.elements['light-control-message'].textContent,/Ausgang unklar/);
 console.log('10 direct-light UI cases passed: inline placement, stale lockout, one-click dispatch/telemetry, dedupe, unchanged state, selection before prepare/execute, navigation, expired login, no retry');
})().catch(e=>{console.error(e);process.exit(1);});
