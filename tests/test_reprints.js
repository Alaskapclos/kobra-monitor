/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ids=new Map(),pending=[],timers=new Map(),saved=new Map();let tick=0;
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.events={};this.hidden=false;this.disabled=false;this.checked=false;this.value='';this.dataset={};this.textContent='';}
 set id(value){this._id=value;ids.set(value,this);}get id(){return this._id;}
 append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;}
 setAttribute(k,v){this[k]=v;}
 addEventListener(name,fn){this.events[name]=fn;}focus(){}scrollIntoView(){}
 querySelectorAll(selector){const out=[];for(const child of this.children){if(selector==='select'&&child.tag==='select'||selector==='[data-paint]'&&child.dataset.paint!==undefined)out.push(child);out.push(...child.querySelectorAll(selector));}return out;}
}
const get=id=>{if(!ids.has(id)){const e=new Element();e.id=id;}return ids.get(id);};
const auth={authenticated:true,ready:Promise.resolve(),reprintRequest:body=>new Promise((resolve,reject)=>pending.push({body,resolve,reject}))};
const context=vm.createContext({window:{kobraAuth:auth,addEventListener(){},dispatchEvent(){}},
 document:{getElementById:get,createElement:tag=>new Element(tag)},
 Option:function(label,value){const e=new Element('option');e.textContent=label;e.value=value;return e;},
 crypto:require('node:crypto').webcrypto,Uint8Array,Event:class{},
 sessionStorage:{getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)},
 setTimeout:fn=>{timers.set(++tick,fn);return tick;},clearTimeout:id=>timers.delete(id)});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../static/reprints.js'),'utf8'),context);
const api=context.window.kobraReprints,flush=()=>new Promise(resolve=>setImmediate(resolve));
const job={id:'a'.repeat(32),sha256:'b'.repeat(64),filename:'<script>test</script>.gcode.3mf'};
const material={paint_index:1,type:'PLA',color:'#112233',estimated_g:3};
const op={id:'c'.repeat(32),source_job:job.id,sha256:job.sha256,source_filename:job.filename,ip:'192.0.2.1',
 nozzle_mm:.4,materials:[material],assignments:[{paint_index:1,slot:2}],selected_slots:[{global_index:2,type:'PLA',sku:'TEST'}]};
(async()=>{
 const opening=api.open(job);assert.equal(pending[0].body,undefined);
 pending[0].resolve({targets:[{ip:op.ip,name:'S1',enabled:true,reason:'Bereit',slots:[{global_index:2,status:5,type:'PLA'}]}]});await flush();
 assert.equal(pending[1].body.action,'check');pending[1].resolve({materials:[material],nozzle_mm:.4,slicer_warning_count:0});await opening;
 assert.equal(get('reprint-file').textContent,job.filename);assert.equal(get('reprint-prepare').disabled,true);
 get('reprint-target').value=op.ip;get('reprint-target').events.change();
 let slot=get('reprint-choices').querySelectorAll('[data-paint]')[0];assert.equal(slot.value,'');
 get('reprint-prepare').events.click();assert.equal(pending.length,2); // missing explicit slot
 slot.value='2';get('reprint-prepare').events.click();await flush();
 assert.equal(pending[2].body.action,'prepare');assert.equal(pending[2].body.assignments[0].paint_index,1);
 pending[2].resolve({...op,state:'prepared',token:'first',detail:'Prepared'});await flush();
 assert.equal(get('reprint-transfer').hidden,false);assert.equal(pending.filter(p=>p.body?.action==='transfer').length,0);
 get('reprint-transfer').events.click();get('reprint-transfer').events.click();await flush();
 assert.equal(pending.filter(p=>p.body?.action==='transfer').length,1);
 pending[3].resolve({...op,state:'uploaded',token:'second',detail:'Stored'});await flush();
 assert.equal(get('reprint-start').disabled,true);assert.equal(pending.filter(p=>p.body?.action==='start').length,0);
 get('reprint-start-form').events.submit({preventDefault(){}});assert.equal(pending.length,4);
 for(const id of ['reprint-bed','reprint-material','reprint-nozzle']){get(id).checked=true;get(id).events.change();}
 assert.equal(get('reprint-start').disabled,false);
 get('reprint-start-form').events.submit({preventDefault(){}});await flush();
 assert.equal(pending[4].body.action,'start');assert.equal(pending[4].body.token,'second');
 pending[4].reject(Error('synthetic timeout'));await flush();
 assert.equal(get('reprint-start-form').hidden,true);assert.equal(saved.get('kobra-reprint-id'),op.id);
 const poll=Array.from(timers.values()).pop();poll();await flush();
 assert.equal(pending[5].body.action,'status');pending[5].resolve({...op,state:'awaiting',detail:'Waiting'});await flush();
 assert.equal(pending.filter(p=>p.body?.action==='start').length,1); // feedback never resends
 api.resetSession();assert.equal(get('reprint-panel').hidden,true);
 assert.equal(timers.size,0);
 console.log('Repeat UI: explicit target/slot, two phases, three readiness checks, double-click guard, timeout/status-only recovery and session cleanup passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
