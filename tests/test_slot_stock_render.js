'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
class Element{constructor(){this.children=[];this.style={};}setAttribute(k,v){this[k]=v;}append(...children){this.children.push(...children);}replaceChildren(){this.children=[];}}
const area=new Element();let preferStock=false;let stock={id:7,grams:375,percent:50};
const context=vm.createContext({$:()=>area,number:v=>typeof v==='number'&&Number.isFinite(v),selectedIp:'test',document:{createElement:()=>new Element()},window:{kobraSpools:{remaining:()=>stock,source:()=>preferStock?'spoolman':'ace'}}});
const source=fs.readFileSync(path.join(__dirname,'../static/monitor.js'),'utf8');
vm.runInContext(source.slice(source.indexOf('function renderSlots('),source.indexOf('function renderDeviceStatus(')),context);
const draw=(percent,stale=false)=>context.renderSlots({loaded_slot:0,ace_slots:[{global_index:0,type:'PLA',consumables_percent:percent}]},true,stale);
draw(undefined);let card=area.children[0];assert.equal(card.children[4].children[0].textContent,50);assert.equal(card.children[5].children[0].style.width,'50%');assert.match(card.children[6].textContent,/Spoolman #7 · 375 g/);
draw(0);card=area.children[0];assert.equal(card.children[4].children[0].textContent,0);assert.equal(card.children.length,6);
draw(80);assert.equal(area.children[0].children[4].children[0].textContent,80);
draw(undefined,true);card=area.children[0];assert.equal(card.children[4].children[0].textContent,'—');assert.equal(card.children.length,6);
stock={id:7,grams:375,percent:null};draw(undefined);card=area.children[0];assert.equal(card.children[4].children[0].textContent,'—');assert.match(card.children[6].textContent,/Ausgangsgewicht/);
stock=null;draw(undefined);assert.equal(area.children[0].children.length,6);
stock={id:7,grams:375,percent:50};preferStock=true;draw(0);card=area.children[0];assert.equal(card.children[4].children[0].textContent,50);assert.match(card.children[6].textContent,/Spoolman/);
stock=null;draw(80);assert.equal(area.children[0].children[4].children[0].textContent,'—');assert.match(area.children[0].children[6].textContent,/nicht aktuell/);
preferStock=false;draw(0);assert.equal(area.children[0].children[4].children[0].textContent,0);
console.log('9 slot stock rendering cases passed: grams and percentage, native zero, native precedence, stale slot, missing initial weight, missing mapping');
