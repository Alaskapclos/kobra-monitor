'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
const flush=()=>new Promise(setImmediate);
function harness(){
 const elements={};for(const id of ['speed-control-open','speed-control-dialog','speed-control-value','speed-control-message','speed-control-note','speed-control-printer','speed-control-file','speed-control-cancel','speed-control-ok'])elements[id]={value:'2',textContent:'',hidden:false,disabled:false,open:false,listeners:{},setAttribute(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},addEventListener(k,f){this.listeners[k]=f;}};
 let held=0,count=0,release,failed=false,previous=2,authenticated=true;const calls=[],events={};
 const window={addEventListener(k,f){events[k]=f;},dispatchEvent(){}};
 const context={window,document:{getElementById:id=>elements[id]},crypto:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)},Uint8Array,AbortSignal,Event,location:{hash:'#overview'},fetch:async(path,options)=>{
 if(path==='/api/session'){if(++count===held)await new Promise(r=>release=r);return {json:async()=>({authenticated,account_configured:true,csrf:'fixture'})};}
 const body=JSON.parse(options.body);calls.push(body);if(body.action==='execute'&&failed)throw Error('fixture');
 return {ok:true,json:async()=>body.action==='prepare_speed'?{id:'a'.repeat(32),token:'fixture',context:body.context,state:body.desired===2?'unchanged':'prepared',previous,detail:'Bereits so gemeldet.'}:{state:'confirmed'}};
 }};
 vm.runInNewContext(fs.readFileSync('static/speed-controls.js','utf8'),context);
 const data={ip:'192.0.2.1',connection:'online',data:{printer_name:'Testdrucker',filename:'part.3mf',print_state:'printing'},speed_control:{enabled:true,supported:true,available:true,context:'a'.repeat(64)},device_status:{speed_mode:{value:2,age_s:0,current_session:true}}};
 return {elements,calls,events,context,data,render:(d=data,age=0)=>window.kobraSpeedControls.render(d,age),open:()=>elements['speed-control-open'].listeners.click(),set:n=>elements['speed-control-value'].value=String(n),ok:()=>elements['speed-control-ok'].listeners.click(),cancel:()=>elements['speed-control-cancel'].listeners.click(),hold:n=>held=n,release:()=>release(),fail:()=>failed=true,previous:n=>previous=n,expire:()=>authenticated=false};
}
(async()=>{
 let h=harness();h.render();h.open();assert(h.elements['speed-control-dialog'].open);h.set(3);assert.equal(h.calls.length,0);h.cancel();assert.equal(h.calls.length,0);
 for(const mode of [1,3]){h=harness();h.render();h.open();h.set(mode);await h.ok();assert.deepEqual(h.calls.map(c=>c.action),['prepare_speed','execute']);assert.equal(h.calls[0].desired,mode);assert.equal(h.calls[0].context,'a'.repeat(64));assert.equal(h.data.device_status.speed_mode.value,2);}
 h=harness();h.render();h.open();await h.ok();assert.deepEqual(h.calls.map(c=>c.action),['prepare_speed']);
 h=harness();for(const change of [{connection:'offline'},{speed_control:{enabled:false}},{speed_control:{enabled:true,supported:true,available:false}},{device_status:{speed_mode:{value:99,age_s:0,current_session:true}}}]){h.render({...h.data,...change});h.open();assert(!h.elements['speed-control-dialog'].open);}assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.set(3);h.hold(1);let pending=h.ok();await flush();h.render({...h.data,ip:'192.0.2.2'});h.release();await pending;assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.set(3);h.hold(2);pending=h.ok();await flush();h.render({...h.data,speed_control:{...h.data.speed_control,context:'b'.repeat(64)}});h.release();await pending;await flush();assert.deepEqual(h.calls.map(c=>c.action),['prepare_speed','cancel']);
 h=harness();h.render();h.open();h.set(3);h.previous(1);await h.ok();assert.deepEqual(h.calls.map(c=>c.action),['prepare_speed','cancel']);
 h=harness();h.render();h.open();h.render(h.data,16);await h.ok();assert.equal(h.calls.length,0);assert(!h.elements['speed-control-dialog'].open);
 h=harness();h.render();h.open();h.context.location.hash='#spools';h.events.hashchange();await h.ok();assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.set(3);h.fail();await h.ok();assert.equal(h.calls.filter(c=>c.action==='execute').length,1);assert.match(h.elements['speed-control-message'].textContent,/Ausgang unklar/);
 h=harness();h.render();h.open();h.set(3);await Promise.all([h.ok(),h.ok()]);assert.equal(h.calls.filter(c=>c.action==='execute').length,1);
 h=harness();h.render();h.open();h.set(3);h.expire();await h.ok();assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();for(const mode of [0,4,1.5,'invalid']){h.set(mode);await h.ok();}assert.equal(h.calls.length,0);
 console.log('14 speed-mode UI cases passed (HTTP-compatible UUID, dialog/OK, modes, unchanged, availability, job/selection changes, stale data, navigation, no retry, dedupe, login and invalid mode)');
})().catch(e=>{console.error(e);process.exit(1);});
