'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
class Element{constructor(){this.handlers={};this.children=[];this.hidden=true;this.value='';}addEventListener(k,f){this.handlers[k]=f;}setAttribute(k,v){this[k]=v;}append(...v){this.children.push(...v);}replaceChildren(){this.children=[];}get options(){return this.children;}}
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
let clock=1000000,fail=false,calls=[];
const data={url:'http://spoolman:8000',configured:true,inventory_current:true,checked_at:clock/1000,spools:[{id:42,name:'<script>Test</script>',vendor:'Testfirma',material:'PETG',remaining_weight:0},{id:43,name:'PLA',remaining_weight:null}],mappings:{},error:''};
const window={kobraAuth:{spoolRequest:async body=>{calls.push(body);if(fail)throw Error('Testfehler');return structuredClone(data);}}};
class Clock extends Date{static now(){return clock;}}
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/spools.js'),'utf8'),{window,Date:Clock,document:{getElementById:node,createElement:()=>new Element()}});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const rows=()=>node('spools-assignments').children;
(async()=>{
 window.kobraSpools.setPrinters([{ip:'192.168.1.20',data:{ace_slots:[{global_index:0},{global_index:1}]}}],'192.168.1.20');
 node('spools-open').handlers.click();await tick();assert.equal(rows().length,2);assert.equal(node('spools-content').hidden,false);
 assert.match(window.kobraSpools.caption(data.spools[0]),/0 g Rest/);assert.match(window.kobraSpools.caption(data.spools[1]),/unbekannt/);
 let select=rows()[0].children[0].children[0];assert.match(select.children[1].textContent,/<script>Test<\/script>/);assert.equal(select.children[1].innerHTML,undefined);
 select.value='42';await rows()[0].children[1].handlers.click();assert.equal(calls.at(-1).spool_id,42);assert.equal(calls.at(-1).slot,0);
 data.mappings={'192.168.1.20':{'0':42}};data.error='Verbindung fehlt';data.inventory_current=false;await node('spools-refresh').handlers.click();assert.match(node('spools-message').textContent,/Verbindung fehlt/);
 select=rows()[0].children[0].children[0];assert.equal(select.children[2].disabled,true);select.value='';await rows()[0].children[1].handlers.click();assert.equal(calls.at(-1).spool_id,null);
 data.mappings={'192.168.1.99':{'2':42}};await node('spools-refresh').handlers.click();assert.equal(rows().length,3);assert.match(rows()[2].children[0].textContent,/Nicht mehr gemeldeter/);
 fail=true;await node('spools-refresh').handlers.click();assert.match(node('spools-message').textContent,/Testfehler/);assert.equal(node('spools-connect').disabled,false);fail=false;
 data.error='';data.inventory_current=true;data.checked_at=clock/1000;await node('spools-refresh').handlers.click();clock+=61000;window.kobraSpools.setPrinters([{ip:'192.168.1.20',data:{ace_slots:[{global_index:0},{global_index:1}]}}],'192.168.1.20');assert.match(node('spools-updated').textContent,/Nicht aktuell/);
 console.log('8 spool UI cases passed: slots, zero/unknown, safe text, assignment, outage, offline clear/orphan, failed request, expiry');
})().catch(error=>{console.error(error);process.exitCode=1;});
