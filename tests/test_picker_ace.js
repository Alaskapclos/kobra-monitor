'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
class Element{
 constructor(){this.children=[];this.style={};this.className='';this.attributes={};this.hidden=false;this.classList={toggle:(name,on)=>{const names=this.className.split(' ').filter(v=>v&&v!==name);if(on)names.push(name);this.className=names.join(' ');}};}
 append(...children){this.children.push(...children);}replaceChildren(){this.children=[];}setAttribute(k,v){this.attributes[k]=v;}
 querySelector(selector){for(const child of this.children){if(child.className.split(' ').includes(selector.slice(1)))return child;const next=child.querySelector(selector);if(next)return next;}return null;}
}
const stock={a:{id:7,grams:42,percent:4.2},b:{id:11,grams:751,percent:75.1}},source={a:'spoolman',b:'ace'};let calls=[];
const context=vm.createContext({document:{createElement:()=>new Element()},window:{kobraSpools:{remaining:(ip,slot)=>{calls.push([ip,slot.global_index]);return stock[ip];},source:ip=>source[ip]}},selectedIp:'b',number:v=>typeof v==='number'&&Number.isFinite(v),ageText:v=>'Vor '+v+' s'});
const js=fs.readFileSync(path.join(__dirname,'../static/monitor.js'),'utf8');
vm.runInContext(js.slice(js.indexOf('function renderSlots('),js.indexOf('function renderDeviceStatus('))+js.slice(js.indexOf('function renderPickerAce('),js.indexOf('function createPickerOverview(')),context);
const printer=ip=>({ip,connection:'online',stale_after_s:90,section_age_s:{ace:2},data:{loaded_slot:0,ace_units:[{}],ace_slots:[{global_index:0,type:'PLA',color:[20,100,200],consumables_percent:80}]}});
const draw=(p,age=0,failed=false)=>{const button=new Element();const summary=context.renderPickerAce(button,p,age,failed);return {button,summary,grid:button.querySelector('.picker-ace-slots'),card:button.querySelector('.compact-slot')};};
const amount=result=>result.card.children[4].children[0].textContent;
let count=0;const test=(name,fn)=>{fn();count++;};
test('stock source belongs to its own printer despite another selection',()=>{const r=draw(printer('a'));assert.equal(amount(r),4);assert.match(r.summary,/Spoolman #7/);assert.equal(calls.at(-1)[0],'a');});
test('native ACE source remains native on second printer',()=>{const r=draw(printer('b'));assert.equal(amount(r),80);assert.doesNotMatch(r.summary,/Spoolman/);});
test('real native zero remains zero',()=>{const p=printer('b');p.data.ace_slots[0].consumables_percent=0;assert.equal(amount(draw(p)),0);});
test('missing ACE value uses its own assigned stock',()=>{const p=printer('b');delete p.data.ace_slots[0].consumables_percent;assert.equal(amount(draw(p)),75);});
test('stock preference overrides misleading native zero',()=>{const p=printer('a');p.data.ace_slots[0].consumables_percent=0;assert.equal(amount(draw(p)),4);});
test('missing assigned stock is unknown rather than native fallback',()=>{const saved=stock.a;stock.a=null;assert.equal(amount(draw(printer('a'))),'—');stock.a=saved;});
test('offline report cannot present current amounts',()=>{const p=printer('b');p.connection='offline';const r=draw(p);assert.equal(amount(r),'—');assert.match(r.summary,/veraltet/);});
test('ACE age advances independently',()=>{const r=draw(printer('a'),59);assert.equal(amount(r),'—');});
test('failed overall request invalidates ACE',()=>{assert.equal(amount(draw(printer('b'),0,true)),'—');});
test('monitor response expires after ten seconds',()=>{assert.equal(amount(draw(printer('b'),11)),'—');});
test('missing section age is waiting, not remembered slots',()=>{const p=printer('a');delete p.section_age_s.ace;const r=draw(p);assert.equal(r.card,null);assert.match(r.summary,/Keine aktuellen/);});
test('empty slot never claims loaded material or amount',()=>{const p=printer('b');p.data.ace_slots[0].edit_status=2;const r=draw(p);assert.equal(amount(r),'—');assert.equal(r.card.children[2].textContent,'Leer');assert.doesNotMatch(r.summary,/, geladen/);});
test('loaded slot and color are preserved',()=>{const r=draw(printer('b'));assert.match(r.card.className,/active/);assert.equal(r.card.children[1].style.borderColor,'rgb(20,100,200)');assert.match(r.summary,/, geladen/);});
test('eight slots preserve global indexes',()=>{const p=printer('b');p.data.loaded_slot=5;p.data.ace_slots=Array.from({length:8},(_,i)=>({global_index:i,type:'PETG',consumables_percent:100}));const r=draw(p);assert.equal(r.grid.children.length,8);assert.match(r.grid.children[5].attributes['aria-label'],/Slot 6, PETG, geladen/);});
test('refresh replaces slots instead of appending',()=>{const button=new Element(),p=printer('b');context.renderPickerAce(button,p);p.data.ace_slots.push({global_index:1,type:'TPU'});context.renderPickerAce(button,p);assert.equal(button.children.length,1);assert.equal(button.querySelector('.picker-ace-slots').children.length,2);});
test('no ACE slots is an explicit empty state',()=>{const p=printer('a');p.data.ace_slots=[];const r=draw(p);assert.equal(r.card,null);assert.match(r.summary,/Keine Slots/);});
console.log(count+' compact ACE cases passed: independent printers, source selection, freshness, empty and loaded slots, eight slots and refresh');
