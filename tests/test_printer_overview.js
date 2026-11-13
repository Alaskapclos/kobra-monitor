'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
class Element{
 constructor(){this.children=[];this.handlers={};this.style={};this.className='';this.attributes={};this.hidden=false;this.dataset={};this.classList={toggle:(name,on)=>{let values=this.className.split(' ').filter(Boolean).filter(v=>v!==name);if(on)values.push(name);this.className=values.join(' ');},remove:(...names)=>{this.className=this.className.split(' ').filter(v=>!names.includes(v)).join(' ');}};}
 addEventListener(k,f){this.handlers[k]=f;}setAttribute(k,v){this.attributes[k]=String(v);}append(...items){for(const item of items){item.parent=this;this.children.push(item);}}
 querySelector(selector){for(const child of this.children){if(child.className.split(' ').includes(selector.slice(1)))return child;const found=child.querySelector(selector);if(found)return found;}return null;}
 replaceChildren(){this.children=[];}insertBefore(child,before){if(child.parent){child.parent.children=child.parent.children.filter(v=>v!==child);}const index=this.children.indexOf(before);this.children.splice(index<0?this.children.length:index,0,child);child.parent=this;}remove(){if(this.parent)this.parent.children=this.parent.children.filter(v=>v!==this);}
 focus(){document.activeElement=this;}
}
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
const document={body:new Element(),querySelectorAll:()=>[],getElementById:node,createElement:()=>new Element(),querySelector:()=>null,activeElement:null};
const context=vm.createContext({document,window:{addEventListener(){},kobraAuth:{ready:new Promise(()=>{}),setPrinters(){}}},Date,AbortSignal,setTimeout:()=>0,clearTimeout(){},setInterval(){},fetch:()=>new Promise(()=>{})});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/monitor.js'),'utf8'),context);
const run=code=>vm.runInContext(code,context);
function view(p,extra=0,failed=false){context.fixture=p;context.extra=extra;context.failed=failed;return run('printerOverview(fixture,extra,failed)');}
const printer=(ip='a')=>({ip,connection:'online',age_s:2,stale_after_s:90,section_age_s:{print:2,temperature:2},data:{printer_name:ip,print_state:'printing',progress:.35,remain_time:5400,nozzle_temp:220.4,bed_temp:60}});
let p=printer(),v=view(p);assert.equal(v.progress,35);assert.equal(v.remaining,'1 h 30 min');assert.equal(v.nozzle,'220 °C');assert.equal(v.bed,'60 °C');
let second=printer('b');second.data.progress=.8;second.data.nozzle_temp=240;assert.equal(view(second).progress,80);assert.equal(view(p).progress,35,'Printers stay independent');
p.data.print_state='auto_leveling';p.data.progress=.95;p.data.remain_time=40000;v=view(p);assert.equal(v.progress,null);assert.equal(v.remaining,'—');assert.equal(v.state,'Vorbereitung');assert.equal(v.nozzle,'220 °C');
p=printer();p.section_age_s.print=100;v=view(p);assert.equal(v.progress,null);assert.equal(v.remaining,'—');assert.equal(v.nozzle,'220 °C');assert.match(v.note,/Druckstatus fehlt/);
p=printer();p.section_age_s.temperature=100;v=view(p);assert.equal(v.progress,35);assert.equal(v.nozzle,'—');assert.equal(v.bed,'—');assert.match(v.note,/Temperaturwerte fehlen/);
p=printer();p.connection='offline';v=view(p);assert.equal(v.progress,null);assert.equal(v.remaining,'—');assert.equal(v.nozzle,'—');assert.match(v.note,/Verbindung unterbrochen/);
p=printer();assert.equal(view(p,0,true).nozzle,'—');assert.equal(view(p,11).connection,'offline');assert.equal(view(p,0,true).progress,null);
p=printer();p.data.progress=NaN;p.data.nozzle_temp=Infinity;p.data.bed_temp='60';p.data.remain_time=-1;v=view(p);assert.equal(v.progress,null);assert.equal(v.nozzle,'—');assert.equal(v.bed,'—');assert.equal(v.remaining,'—');
p=printer();p.data.progress=0;p.data.nozzle_temp=0;v=view(p);assert.equal(v.progress,0);assert.equal(v.nozzle,'0 °C');
p=printer();p.data.print_state='paused';assert.equal(view(p).progress,35);assert.match(view(p).detail,/Pausiert/);p.data.print_state='complete';assert.equal(view(p).progress,null);assert.equal(view(p).remaining,'—');
// Exercise the actual card renderer with two printers and changing readings.
run('renderPrinter=()=>{};refreshArchive=()=>{};lastFetchAt=Date.now();');
context.fixture={ips:['a','b'],printers:[printer('a'),second]};run('lastResponse=fixture;selectedIp="b";render(fixture)');
const cards=node('printer-switcher').children;assert.equal(cards.length,2);assert.equal(cards[0].querySelector('.picker-nozzle').textContent,'220 °C');assert.equal(cards[1].querySelector('.picker-nozzle').textContent,'240 °C');assert.equal(run('selectedIp'),'b');
context.fixture.ips=['b','a'];run('render(fixture)');assert.equal(node('printer-switcher').children[0],cards[1]);assert.equal(run('selectedIp'),'b');
run('requestFailed=true;render(fixture)');for(const card of node('printer-switcher').children){assert.equal(card.querySelector('.picker-nozzle').textContent,'—');assert.equal(card.querySelector('.picker-progress-track').hidden,true);}
context.window.kobraSpools={setPrinters:values=>{context.spoolViews=values;}};
run('render(fixture)');assert.ok(context.spoolViews.every(p=>p.connection==='offline'),'Spool identity cannot stay live after a failed monitor request');
run('requestFailed=false;lastFetchAt=Date.now()-11000;render(fixture)');assert.ok(context.spoolViews.every(p=>p.connection==='offline'));
run('lastFetchAt=Date.now()-5000;render(fixture)');assert.ok(context.spoolViews.every(p=>p.section_age_s.print>=7));assert.equal(context.fixture.printers[0].section_age_s.print,2,'Do not mutate cached response ages');
run('lastFetchAt=Date.now();render(fixture)');assert.ok(context.spoolViews.every(p=>p.connection==='online'));assert.ok(context.spoolViews.every(p=>p.section_age_s.print<3));
console.log('13 overview cases passed: card freshness plus spool-view outage, age propagation and recovery without mutating cached status');
