'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
const flush=()=>new Promise(setImmediate);
function harness(){
 const elements={};for(const id of ['motion-controls','motion-dialog','motion-message','motion-availability','motion-step','motion-printer','motion-action','motion-present','motion-ok','motion-cancel','motion-confirmation-note','motion-consent-state','motion-dialog-title','motion-dialog-warning'])elements[id]={value:'1',checked:false,textContent:'',hidden:false,disabled:false,open:false,listeners:{},classList:{toggle(){}},setAttribute(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},addEventListener(k,f){this.listeners[k]=f;}};
 const buttons=['axis_x','axis_y','axis_z','home_xy','home_z','motors_off'].map(action=>({dataset:{motion:action,direction:'-1'},listeners:{},disabled:true,addEventListener(k,f){this.listeners[k]=f;}}));
 let held=0,count=0,release,failed=false,previous=1,authenticated=true;const calls=[],events={};
 const window={addEventListener(k,f){events[k]=f;},dispatchEvent(){}};
 const context={window,document:{getElementById:id=>elements[id],querySelectorAll:()=>buttons},crypto:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)},Uint8Array,AbortSignal,Event,location:{hash:'#overview'},fetch:async(path,options)=>{
 if(path==='/api/session'){if(++count===held)await new Promise(r=>release=r);return {json:async()=>({authenticated,account_configured:true,csrf:'fixture'})};}
 const body=JSON.parse(options.body);calls.push(body);if(body.action==='execute'&&failed)throw Error('fixture');
 return {ok:true,json:async()=>body.action==='prepare_motion'?{id:'a'.repeat(32),token:'fixture',context:body.context,state:'prepared',previous,detail:'Bereits so gemeldet.'}:{state:'sent',detail:'Befehl einmal gesendet.',motion_confirmed:true,print_cycle:'cycle-a'}};
 }};
 vm.runInNewContext(fs.readFileSync('static/motion-controls.js','utf8'),context);
 const data={ip:'192.0.2.1',connection:'online',data:{printer_name:'Testdrucker'},motion_control:{enabled:true,supported:true,available:true,context:'a'.repeat(64),age_s:0,wait_s:0,print_cycle:'cycle-a',confirmed:false}};
 return {elements,calls,events,context,data,render:(d=data,age=0)=>window.kobraMotionControls.render(d,age),open:(action='axis_x')=>buttons.find(b=>b.dataset.motion===action).listeners.click(),ok:()=>elements['motion-ok'].listeners.click(),present:()=>{elements['motion-present'].checked=true;elements['motion-present'].listeners.change();},cancel:()=>elements['motion-cancel'].listeners.click(),hold:n=>held=n,release:()=>release(),fail:()=>failed=true,expire:()=>authenticated=false};
}
(async()=>{
 let h=harness();h.render();h.open();assert(h.elements['motion-dialog'].open);assert(h.elements['motion-ok'].disabled);await h.ok();assert.equal(h.calls.length,0);h.present();h.cancel();await h.ok();assert.equal(h.calls.length,0);
 for(const action of ['axis_x','axis_y','axis_z','home_xy','home_z','motors_off']){h=harness();h.render();h.elements['motion-step'].value='15';h.open(action);h.present();await h.ok();assert.deepEqual(h.calls.map(c=>c.action),['prepare_motion','execute']);assert.equal(h.calls[0].desired,action.startsWith('home_')||action==='motors_off'?1:-15);assert.equal(h.calls[0].present,true);}
 h=harness();h.render();h.open();h.present();h.hold(1);let pending=h.ok();await flush();h.render({...h.data,ip:'192.0.2.2'});h.release();await pending;assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.present();h.hold(2);pending=h.ok();await flush();h.render({...h.data,motion_control:{...h.data.motion_control,context:'b'.repeat(64)}});h.release();await pending;await flush();assert.deepEqual(h.calls.map(c=>c.action),['prepare_motion','cancel']);
 h=harness();h.render();h.open();h.present();h.render(h.data,16);await h.ok();assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.present();h.context.location.hash='#spools';h.events.hashchange();await h.ok();assert.equal(h.calls.length,0);
 h=harness();h.render();h.open();h.present();h.fail();await h.ok();assert.equal(h.calls.filter(c=>c.action==='execute').length,1);assert.match(h.elements['motion-message'].textContent,/Ausgang unklar/);
 h=harness();h.render();h.open();h.present();await Promise.all([h.ok(),h.ok()]);assert.equal(h.calls.filter(c=>c.action==='execute').length,1);
 h=harness();h.render();h.open();h.present();h.expire();await h.ok();assert.equal(h.calls.length,0);
 for(const change of [{connection:'offline'},{motion_control:{enabled:false}},{motion_control:{enabled:true,supported:true,available:false,wait_s:60}}]){h=harness();h.render({...h.data,...change});h.open();assert(!h.elements['motion-dialog'].open);assert.equal(h.calls.length,0);}
 h=harness();h.render();h.open();h.present();await h.ok();h.render();h.open('axis_y');await flush();await flush();assert.equal(h.calls.filter(c=>c.action==='execute').length,2);assert.equal(h.calls.filter(c=>c.action==='prepare_motion')[1].present,false);assert(!h.elements['motion-dialog'].open);
 h.render({...h.data,motion_control:{...h.data.motion_control,print_cycle:'cycle-b',context:'b'.repeat(64),confirmed:false}});h.open();assert(h.elements['motion-dialog'].open);assert(!h.elements['motion-confirmation-note'].hidden);h.cancel();
 h=harness();h.data.motion_control.confirmed=true;h.render();h.open('home_xy');assert(h.elements['motion-dialog'].open);assert(h.elements['motion-confirmation-note'].hidden);assert.equal(h.calls.length,0);
 h=harness();h.data.motion_control.confirmed=true;h.render();h.open('motors_off');assert(h.elements['motion-dialog'].open);assert(h.elements['motion-confirmation-note'].hidden);assert.match(h.elements['motion-dialog-warning'].textContent,/Haltekraft/);assert.equal(h.elements['motion-ok'].textContent,'Motoren ausschalten');assert.equal(h.calls.length,0);h.present();await h.ok();assert.equal(h.calls[0].operation,'motors_off');assert.equal(h.calls[0].desired,1);assert.equal(h.calls[0].present,true);
 h.open('home_xy');assert.equal(h.elements['motion-ok'].textContent,'Fahrt ausführen');assert.match(h.elements['motion-dialog-warning'].textContent,/Kollisions/);
 console.log('22 motion-control UI cases passed');
})().catch(e=>{console.error(e);process.exit(1);});
