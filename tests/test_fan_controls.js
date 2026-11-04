'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
const flush=()=>new Promise(setImmediate);
function harness(){
 const elements={};for(const id of ['fan-control-dialog','fan-control-range','fan-control-value','fan-control-ok','fan-control-message','fan-control-title','fan-control-printer','fan-control-unit','fan-control-cancel','control-part_fan','control-aux_fan','control-chamber_fan'])elements[id]={value:'0',textContent:'',hidden:false,disabled:false,open:false,listeners:{},setAttribute(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},addEventListener(k,f){this.listeners[k]=f;}};
 let held=0,count=0,release,failed=false,previous=0;const calls=[],events={};
 const window={addEventListener(k,f){events[k]=f;},dispatchEvent(){}};
 const context={window,document:{getElementById:id=>elements[id]},crypto:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)},Uint8Array,AbortSignal,Event,location:{hash:'#overview'},fetch:async(path,options)=>{
 if(path==='/api/session'){if(++count===held)await new Promise(r=>release=r);return {json:async()=>({authenticated:true,account_configured:true,csrf:'fixture'})};}
 const body=JSON.parse(options.body);calls.push(body);if(body.action==='execute'&&failed)throw Error('fixture');
 return {ok:true,json:async()=>body.action==='prepare_fan'?{id:'a'.repeat(32),token:'fixture',state:'prepared',previous}:{state:'confirmed'}};
 }};
 vm.runInNewContext(fs.readFileSync('static/fan-controls.js','utf8'),context);
 const data={ip:'192.0.2.1',connection:'online',data:{printer_name:'Testdrucker'},fan_control:{enabled:true,supported:true},device_status:Object.fromEntries(['fan_speed','aux_fan_speed','box_fan_level'].map(k=>[k,{value:0,age_s:0,current_session:true}]))};
 return {elements,calls,events,context,data,render:(d=data)=>window.kobraFanControls.render(d),open:(fan='part_fan')=>elements['control-'+fan].listeners.click(),set:n=>{elements['fan-control-value'].value=String(n);elements['fan-control-value'].listeners.input();},ok:()=>elements['fan-control-ok'].listeners.click(),cancel:()=>elements['fan-control-cancel'].listeners.click(),hold:n=>held=n,release:()=>release(),fail:()=>failed=true,previous:n=>previous=n};
}
(async()=>{
 let h=harness();h.render();h.open();assert(h.elements['fan-control-dialog'].open);h.set(40);assert.equal(h.calls.length,0);h.cancel();assert.equal(h.calls.length,0);
 for(const fan of ['part_fan','aux_fan','chamber_fan']){h=harness();h.render();h.open(fan);h.set(40);await h.ok();assert.deepEqual(h.calls.map(c=>c.action),['prepare_fan','execute']);assert.equal(h.calls[0].fan,fan);assert.equal(h.calls[0].desired,40);assert.equal(h.data.device_status.fan_speed.value,0);}
 h=harness();h.render();h.open();for(const n of [-1,101,1.5,'']){h.set(n);assert(h.elements['fan-control-ok'].disabled);await h.ok();}assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.set(40);await Promise.all([h.ok(),h.ok()]);assert.equal(h.calls.filter(c=>c.action==='execute').length,1);
 h=harness();h.render();h.open();h.render({...h.data,ip:'192.0.2.2'});await h.ok();assert.equal(h.calls.length,0);assert(!h.elements['fan-control-dialog'].open);
 h=harness();h.render();h.open();h.set(40);h.hold(2);let pending=h.ok();await flush();h.render({...h.data,ip:'192.0.2.2'});h.release();await pending;await flush();assert.deepEqual(h.calls.map(c=>c.action),['prepare_fan','cancel']);
 h=harness();h.render();h.open();h.set(40);h.previous(20);await h.ok();assert.deepEqual(h.calls.map(c=>c.action),['prepare_fan','cancel']);
 h=harness();h.render();h.open();h.render({...h.data,connection:'offline'});await h.ok();assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.context.location.hash='#spools';h.events.hashchange();await h.ok();assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.set(40);h.fail();await h.ok();assert.equal(h.calls.filter(c=>c.action==='execute').length,1);assert.match(h.elements['fan-control-message'].textContent,/Ausgang unklar/);
 console.log('12 fan UI cases passed');
})().catch(e=>{console.error(e);process.exit(1);});
