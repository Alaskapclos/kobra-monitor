'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
 constructor(){this.dataset={};this.children=[];this.attributes={};this.hidden=false;this.textContent='';this.className='';}
 append(...items){for(const i of items){i.parent=this;this.children.push(i);}}setAttribute(k,v){this.attributes[k]=v;}addEventListener(){}
 remove(){this.parent.children=this.parent.children.filter(c=>c!==this);}
 querySelector(s){return this.children.find(c=>c.className.split(' ').includes(s.slice(1)))||this.children.map(c=>c.querySelector(s)).find(Boolean)||null;}
}
const context={window:{},document:{getElementById:()=>null,createElement:()=>new Element()},Date,Map,Set,Number};
vm.runInNewContext(fs.readFileSync('static/ace-controls.js','utf8'),context);const api=context.window.kobraAceControls;
const printer=()=>({ip:'192.0.2.1',connection:'online',data:{printer_name:'Synthetic S1'},drying_control:{enabled:true,supported:true},ace_climate:[{id:0,status:0,current_temp:0,humidity:0,ages:{status:1,current_temp:1,humidity:1},current:{status:true,current_temp:true,humidity:true},configuration:'one'}]});
const draw=(p=printer(),extra=0,failed=false)=>{const tile=new Element();api.renderTile(tile,p,extra,failed);return tile;};
const read=(t,field)=>t.querySelector('.ace-climate-'+field).textContent;
let n=0;function test(name,fn){fn();n++;}
test('real zero temperature and humidity are shown',()=>{const t=draw();assert.equal(read(t,'temp'),'0 °C');assert.equal(read(t,'humidity'),'0 % rF');assert.equal(read(t,'state'),'Trocknung aus');});
test('absent humidity is unknown, never inherited from another printer',()=>{const p=printer();delete p.ace_climate[0].humidity;assert.equal(read(draw(p),'humidity'),'Luftfeuchte —');});
test('unknown status is never off or actionable',()=>{const p=printer();delete p.ace_climate[0].status;const t=draw(p);assert.equal(read(t,'state'),'Trocknung unbekannt');assert.equal(t.querySelector('.ace-drying-switch').disabled,true);});
test('stale individual fields do not age along with another measurement',()=>{const p=printer();p.ace_climate[0].ages.humidity=70;assert.equal(read(draw(p),'humidity'),'Luftfeuchte —');assert.equal(read(draw(p),'temp'),'0 °C');});
test('offline/reconnect/failed response disable controls and remove current claims',()=>{for(const change of [p=>p.connection='offline',p=>p.ace_climate[0].current.status=false]){const p=printer();change(p);assert.equal(draw(p).querySelector('.ace-drying-switch').disabled,true);}assert.equal(read(draw(printer(),0,true),'temp'),'Temperatur —');assert.equal(read(draw(printer(),11),'state'),'Trocknung unbekannt');});
test('independent multiple ACE units preserve target labels',()=>{const p=printer();p.ace_climate.push({...p.ace_climate[0],id:1,status:1,current_temp:40,humidity:25});const t=draw(p);assert.equal(t.querySelector('.picker-ace-climate').children.length,2);assert.match(t.querySelector('.picker-ace-climate').children[1].toggle.attributes['aria-label'],/ACE 2/);});
test('refresh preserves the focused switch node; removal removes obsolete ACE',()=>{const p=printer(),t=draw(p),button=t.querySelector('.ace-drying-switch');api.renderTile(t,p);assert.equal(t.querySelector('.ace-drying-switch'),button);p.ace_climate=[];api.renderTile(t,p);assert.equal(t.querySelector('.ace-drying-switch'),null);assert.equal(t.querySelector('.picker-ace-climate').hidden,true);});
test('no drying permission hides switch while keeping climate visible',()=>{const p=printer();p.drying_control.enabled=false;const t=draw(p);assert.equal(t.querySelector('.ace-drying-switch').hidden,true);assert.equal(read(t,'temp'),'0 °C');});
console.log(n+' ACE climate cases passed: measured zeros, missing/old fields, isolated units, permission, switch identity and removal');
