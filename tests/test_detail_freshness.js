'use strict';
// Exercise the selected printer, including loss and recovery, with no printer I/O.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
class Element {
 constructor(){this.children=[];this.style={};this.dataset={};this.attributes={};this.className='';this.handlers={};this.hidden=false;this.classList={toggle:(name,on)=>{const values=this.className.split(' ').filter(v=>v&&v!==name);if(on)values.push(name);this.className=values.join(' ');}};}
 addEventListener(k,f){this.handlers[k]=f;}setAttribute(k,v){this.attributes[k]=String(v);}append(...xs){this.children.push(...xs);}replaceChildren(){this.children=[];}querySelector(){return this.children[0];}
}
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
node('connection-pill').append(new Element());
let now=1000000;class Clock extends Date {static now(){return now;}}
const context=vm.createContext({document:{getElementById:node,createElement:()=>new Element(),querySelector:node},window:{addEventListener(){},kobraAuth:{ready:new Promise(()=>{})}},Date:Clock,AbortSignal,setInterval(){},setTimeout(){},clearTimeout(){},fetch:()=>{throw Error('No network in detail tests');}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/monitor.js'),'utf8'),context);
function draw(snapshot,failed=false,extraSeconds=0){context.fixture=snapshot;context.failed=failed;context.extraSeconds=extraSeconds;vm.runInContext('requestFailed=failed;lastFetchAt=Date.now()-extraSeconds*1000;renderPrinter(fixture)',context);}
function fixture(){return {ip:'192.168.250.1',connection:'online',age_s:2,stale_after_s:90,section_age_s:{printer:2,print:2,temperature:2,ace:2},data:{print_state:'printing',progress:.42,remain_time:3600,curr_layer:5,total_layers:100,filename:'test.gcode',nozzle_temp:220,nozzle_target:220,bed_temp:60,bed_target:60,loaded_slot:3,ace_units:[{}],ace_slots:[{global_index:3,type:'PLA',consumables_percent:75}],ace_drying:{current_temp:27,humidity:30,status:0}}};}
const text=id=>node(id).textContent;
const badge=()=>node('slots').children[0].children[0].children[1].textContent;
let p=fixture();draw(p);assert.equal(text('progress-value'),'42%');assert.equal(text('remaining'),'1 h 0 min');assert.equal(text('layer'),'5 / 100');assert.equal(text('nozzle-mode'),'Sollwert aktiv');assert.equal(badge(),'Geladen');
p.connection='offline';draw(p);assert.equal(text('print-state'),'Status veraltet');assert.equal(text('remaining'),'—');assert.equal(text('layer'),'—');assert.equal(text('progress-value'),'—');assert.match(text('print-subtitle'),/Letzter bekannter/);assert.match(text('file-label'),/ZULETZT GEMELDETE/);assert.equal(text('nozzle-temp'),'220');assert.equal(text('nozzle-mode'),'Letzter bekannter Wert');assert.match(text('temp-freshness'),/Veraltet/);assert.match(node('.temperatures-card').className,/is-stale/);assert.match(text('ace-freshness'),/Veraltet/);assert.match(node('.drying-card').className,/is-stale/);assert.equal(badge(),'Zuletzt geladen');
p=fixture();p.data.progress=.43;draw(p);assert.equal(text('progress-value'),'43%');assert.doesNotMatch(text('temp-freshness'),/Veraltet/);assert.doesNotMatch(node('.temperatures-card').className,/is-stale/);assert.equal(badge(),'Geladen');
draw(p,true);assert.equal(text('remaining'),'—');assert.match(text('temp-freshness'),/Veraltet/);assert.equal(text('nozzle-mode'),'Letzter bekannter Wert');assert.equal(badge(),'Zuletzt geladen');draw(p);assert.equal(text('remaining'),'1 h 0 min');
draw(p,false,11);assert.match(text('connection-banner'),/nicht erreichbar/);assert.equal(text('progress-value'),'—');assert.match(text('temp-freshness'),/Veraltet/);
p=fixture();p.section_age_s.print=91;draw(p);assert.equal(text('progress-value'),'—');assert.equal(text('nozzle-mode'),'Sollwert aktiv');assert.doesNotMatch(node('.temperatures-card').className,/is-stale/);
p=fixture();p.section_age_s.temperature=91;draw(p);assert.equal(text('progress-value'),'42%');assert.match(text('temp-freshness'),/Veraltet/);assert.equal(text('nozzle-mode'),'Letzter bekannter Wert');
p=fixture();p.age_s=91;draw(p);assert.equal(text('progress-value'),'—');assert.match(text('print-subtitle'),/Letzter bekannter/);assert.match(text('ace-freshness'),/Veraltet/);
p=fixture();p.data.print_state='auto_leveling';p.data.progress=.99;draw(p);assert.equal(text('progress-value'),'—');assert.equal(text('remaining'),'—');assert.equal(text('layer'),'—');assert.equal(text('progress-caption'),'Vorbereitung');
p=fixture();p.section_age_s={};draw(p);assert.equal(text('nozzle-temp'),'—');assert.equal(text('nozzle-mode'),'—');assert.equal(text('remaining'),'—');
p=fixture();p.section_age_s.temperature=-1;draw(p);assert.equal(text('nozzle-temp'),'—');assert.equal(text('nozzle-mode'),'—');
p=fixture();p.data.progress=0;p.data.nozzle_temp=0;p.data.nozzle_target=0;draw(p);assert.equal(text('progress-value'),'0%');assert.equal(text('nozzle-temp'),'0');assert.equal(text('nozzle-mode'),'Heizung aus');
console.log('12 detail freshness cases passed: offline, recovery, monitor loss, section freshness, stale ACE, preparation, missing/invalid ages and real zero values');
