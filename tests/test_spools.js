'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
class Element{constructor(){this.handlers={};this.children=[];this.hidden=true;this.value='';}addEventListener(k,f){this.handlers[k]=f;}setAttribute(k,v){this[k]=v;}removeAttribute(k){delete this[k];}append(...v){this.children.push(...v);}replaceChildren(){this.children=[];}get options(){return this.children;}}
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
let clock=1000000,fail=false,calls=[];
const data={url:'http://spoolman:8000',configured:true,inventory_current:true,checked_at:clock/1000,spools:[{id:42,name:'<script>Test</script>',vendor:'Testfirma',material:'PETG',remaining_weight:0},{id:43,name:'PLA',remaining_weight:null}],mappings:{},error:''};
const window={kobraAuth:{spoolRequest:async body=>{calls.push(body);if(fail)throw Error('Testfehler');return structuredClone(data);}}};
class Clock extends Date{static now(){return clock;}}
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/spools.js'),'utf8'),{window,URL,Date:Clock,document:{getElementById:node,createElement:()=>new Element(),createTextNode:text=>({textContent:text})}});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const rows=()=>node('spools-assignments').children;
(async()=>{
 window.kobraSpools.setPrinters([{ip:'192.168.1.20',data:{ace_slots:[{global_index:0},{global_index:1}]}}],'192.168.1.20');
 await tick();node('spools-open').handlers.click();await tick();assert.equal(rows().length,2);assert.equal(node('spools-content').hidden,false);
 assert.match(window.kobraSpools.caption(data.spools[0]),/0 g Rest/);assert.match(window.kobraSpools.caption(data.spools[1]),/unbekannt/);
 let select=rows()[0].children[0].children[0];assert.match(select.children[1].textContent,/<script>Test<\/script>/);assert.equal(select.children[1].innerHTML,undefined);
 select.value='42';await rows()[0].children[1].handlers.click();assert.equal(calls.at(-1).spool_id,42);assert.equal(calls.at(-1).slot,0);
 data.mappings={'192.168.1.20':{'0':42}};data.error='Verbindung fehlt';data.inventory_current=false;await node('spools-refresh').handlers.click();assert.match(node('spools-message').textContent,/Verbindung fehlt/);
 select=rows()[0].children[0].children[0];assert.equal(select.children[2].disabled,true);select.value='';await rows()[0].children[1].handlers.click();assert.equal(calls.at(-1).spool_id,null);
 data.mappings={'192.168.1.99':{'2':42}};await node('spools-refresh').handlers.click();assert.equal(rows().length,3);assert.match(rows()[2].children[0].textContent,/Nicht mehr gemeldeter/);
 fail=true;await node('spools-refresh').handlers.click();assert.match(node('spools-message').textContent,/Testfehler/);assert.equal(node('spools-connect').disabled,false);fail=false;
 data.error='';data.inventory_current=true;data.checked_at=clock/1000;await node('spools-refresh').handlers.click();clock+=61000;window.kobraSpools.setPrinters([{ip:'192.168.1.20',data:{ace_slots:[{global_index:0},{global_index:1}]}}],'192.168.1.20');assert.match(node('spools-updated').textContent,/Nicht aktuell/);
 await tick();data.inventory_current=true;data.checked_at=clock/1000;data.mappings={};
 data.detections=[{ip:'192.168.1.20',slot:0,sku:'TEST-UNIQUE-0001',status:'unknown',spool_id:null}];
 await node('spools-refresh').handlers.click();
 window.kobraSpools.setPrinters([{ip:'192.168.1.20',connection:'online',section_age_s:{ace:0},data:{ace_slots:[{global_index:0,sku:'TEST-UNIQUE-0001'}]}}],'192.168.1.20');await tick();
 let card=rows()[0],link=card.children[5],check=card.children[4].children[0];select=card.children[0].children[0];select.value='42';
 await link.handlers.click();assert.match(node('spools-message').textContent,/bestätigen/);
 check.checked=true;await link.handlers.click();await tick();assert.equal(calls.at(-1).action,'link_sku');assert.equal(calls.at(-1).unique_confirmed,true);
 data.sku_links={'TEST-UNIQUE-0001':42};data.detections[0].status='recognized';data.detections[0].spool_id=42;
 await node('spools-refresh').handlers.click();assert.match(rows()[0].children[3].textContent,/wiedererkannt/);assert.equal(rows().length,2);
 await rows()[1].children[1].handlers.click();assert.equal(calls.at(-1).spool_id,null);
 data.detections[0].status='duplicate';await node('spools-refresh').handlers.click();assert.match(rows()[0].children[3].textContent,/mehrfach/);assert.equal(rows()[0].children.length,4);
 assert.equal(node('spools-visit').href,'http://spoolman:8000/');assert.equal(node('spools-visit').hidden,false);
 for(const url of ['javascript:alert(1)','https://user:secret@example.com','']){data.url=url;await node('spools-refresh').handlers.click();assert.equal(node('spools-visit').hidden,true);assert.equal(node('spools-visit').href,undefined);}
 console.log('14 spool UI cases passed: existing 8 plus explicit consent, SKU link, recognized/unlink, duplicate blocked');
})().catch(error=>{console.error(error);process.exitCode=1;});
