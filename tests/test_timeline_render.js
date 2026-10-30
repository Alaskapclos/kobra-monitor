'use strict';
// Execute the actual UI renderer without a browser. Assertions check that
// missing readings and disconnections never become continuous temperature lines.
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const assert=require('node:assert/strict');
class Element {
  constructor(tag='div'){this.tag=tag;this.attributes={};this.children=[];this.textContent='';}
  setAttribute(k,v){this.attributes[k]=String(v);}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  addEventListener(){}
}
const ids=new Map();
const context=vm.createContext({
  window:{addEventListener(){}},document:{getElementById:id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);},
    createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)},
  setInterval:()=>0,fetch:()=>new Promise(()=>{}),AbortSignal,Date,console
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/monitor.js'),'utf8'),context);
const point=(at,temp=200)=>({at,nozzle_temp:temp,bed_temp:temp===null?null:75,nozzle_target:temp,bed_target:temp===null?null:75});
const job={id:'a'.repeat(32),ip:'192.168.1.102',first_seen:1000,last_seen:1300,ended_at:1300};
const svg=()=>ids.get('timeline-content').children.find(e=>e.tag==='svg');
const nozzle=()=>svg().children.find(e=>e.tag==='path'&&e.attributes.class==='chart-series chart-nozzle');
context.fixture={job,points:[point(1000),point(1030),point(1200),point(1230,null),point(1260),point(1290)],events:[]};
vm.runInContext('renderTimeline(fixture)',context);
assert.equal((nozzle().attributes.d.match(/M/g)||[]).length,3,'Long gap and missing sample must split the curve');
assert.equal(svg().children.filter(e=>e.attributes.class==='chart-gap').length,1);
context.fixture={job,points:[point(1000),point(1030)],events:[{at:1010,kind:'disconnected'}]};
vm.runInContext('renderTimeline(fixture)',context);
assert.equal((nozzle().attributes.d.match(/M/g)||[]).length,2,'Even a short disconnection must split the curve');
assert.equal(svg().children.filter(e=>e.attributes.class==='chart-event').length,1);
context.fixture={job,points:[point(1000,null),point(1030,null)],events:[]};
vm.runInContext('renderTimeline(fixture)',context);
assert.equal(nozzle().attributes.d,'','Missing temperatures must never be drawn as zero');
context.fixture={job,points:[],events:[]};
vm.runInContext('renderTimeline(fixture)',context);
assert.equal(svg(),undefined,'No samples should display an empty-state message');
console.log('4 temperature rendering cases passed');
