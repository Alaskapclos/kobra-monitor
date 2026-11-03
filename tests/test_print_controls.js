'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
const flush=()=>new Promise(setImmediate);
function harness(){
 const elements={};for(const id of ['print-controls','control-print_pause','control-print_resume','control-print_stop','print-control-dialog','print-control-title','print-control-warning','print-control-message','print-control-printer','print-control-file','print-control-cancel','print-control-ok'])elements[id]={value:'2',textContent:'',hidden:false,disabled:false,open:false,listeners:{},classList:{toggle(){}},setAttribute(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},addEventListener(k,f){this.listeners[k]=f;}};
 let held=0,count=0,release,failed=false,previous=1,authenticated=true;const calls=[],events={};
 const window={addEventListener(k,f){events[k]=f;},dispatchEvent(){}};
 const context={window,document:{getElementById:id=>elements[id]},crypto:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)},Uint8Array,AbortSignal,Event,location:{hash:'#overview'},fetch:async(path,options)=>{
 if(path==='/api/session'){if(++count===held)await new Promise(r=>release=r);return {json:async()=>({authenticated,account_configured:true,csrf:'fixture'})};}
 const body=JSON.parse(options.body);calls.push(body);if(body.action==='execute'&&failed)throw Error('fixture');
 return {ok:true,json:async()=>body.action==='prepare_print'?{id:'a'.repeat(32),token:'fixture',context:body.context,state:'prepared',previous,detail:'Bereits so gemeldet.'}:{state:'confirmed'}};
 }};
 vm.runInNewContext(fs.readFileSync('static/print-controls.js','utf8'),context);
 const data={ip:'192.0.2.1',connection:'online',data:{printer_name:'Testdrucker',filename:'part.3mf',print_state:'printing'},print_control:{enabled:true,supported:true,available:{print_pause:true,print_resume:false,print_stop:true},context:'a'.repeat(64),phase:1,age_s:0,filename:'part.3mf'},device_status:{speed_mode:{value:2,age_s:0,current_session:true}}};
 return {elements,calls,events,context,data,render:(d=data,age=0)=>window.kobraPrintControls.render(d,age),open:(action='print_pause')=>elements['control-'+action].listeners.click(),ok:()=>elements['print-control-ok'].listeners.click(),cancel:()=>elements['print-control-cancel'].listeners.click(),hold:n=>held=n,release:()=>release(),fail:()=>failed=true,previous:n=>previous=n,expire:()=>authenticated=false};
}
(async()=>{
 let h=harness();h.render();h.open();assert(h.elements['print-control-dialog'].open);assert.equal(h.calls.length,0);h.cancel();await h.ok();assert.equal(h.calls.length,0);
 for(const action of ['print_pause','print_stop','print_resume']){h=harness();if(action==='print_resume'){h.data.print_control.phase=2;h.data.print_control.available.print_resume=true;h.previous(2);}h.render();h.open(action);if(action==='print_stop')assert.match(h.elements['print-control-warning'].textContent,/nicht fortgesetzt/);await h.ok();assert.deepEqual(h.calls.map(c=>c.action),['prepare_print','execute']);assert.equal(h.calls[0].operation,action);}
 h=harness();h.render();h.open('print_resume');assert(!h.elements['print-control-dialog'].open);
 h=harness();h.render();h.open();h.hold(1);let pending=h.ok();await flush();h.render({...h.data,ip:'192.0.2.2'});h.release();await pending;assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.hold(2);pending=h.ok();await flush();h.render({...h.data,print_control:{...h.data.print_control,context:'b'.repeat(64)}});h.release();await pending;await flush();assert.deepEqual(h.calls.map(c=>c.action),['prepare_print','cancel']);
 h=harness();h.render();h.open();h.previous(2);await h.ok();assert.deepEqual(h.calls.map(c=>c.action),['prepare_print','cancel']);
 h=harness();h.render();h.open();h.render(h.data,16);await h.ok();assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.context.location.hash='#spools';h.events.hashchange();await h.ok();assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.fail();await h.ok();assert.equal(h.calls.filter(c=>c.action==='execute').length,1);assert.match(h.elements['print-control-message'].textContent,/Ausgang unklar/);
 h=harness();h.render();h.open();await Promise.all([h.ok(),h.ok()]);assert.equal(h.calls.filter(c=>c.action==='execute').length,1);
 h=harness();h.render();h.open();h.expire();await h.ok();assert.equal(h.calls.length,0);
 for(const change of [{connection:'offline'},{print_control:{enabled:false}},{print_control:{enabled:true,supported:true,phase:0,available:{}}}]){h=harness();h.render({...h.data,...change});h.open();assert(!h.elements['print-control-dialog'].open);assert.equal(h.calls.length,0);}
 console.log('14 print-control UI cases passed');
})().catch(e=>{console.error(e);process.exit(1);});
