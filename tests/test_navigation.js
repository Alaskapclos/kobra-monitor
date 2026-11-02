'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{constructor(label,classes=[]){this.label=label;this.classes=new Set(classes);this.attrs={};this.dataset={};this.scrolled=0;this.classList={contains:k=>this.classes.has(k),toggle:(k,v)=>v?this.classes.add(k):this.classes.delete(k)};}getAttribute(k){return k==='aria-labelledby'?this.label:this.attrs[k];}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}scrollIntoView(){this.scrolled++;}}
const sections=[new Element(null,['page-heading']),new Element(null,['overview-grid']),new Element('camera-title'),new Element('history-title'),new Element('order-title'),new Element('timeline-title'),new Element('filament-title'),new Element('spools-title'),new Element(null,['bottom-grid']),new Element('help-title'),new Element('notify-title')];
const links=['overview','orders','spools','settings'].map(v=>{const e=new Element();e.dataset.view=v;return e;});
const heading={querySelector:()=>({textContent:''})},picker=new Element(),help=sections[9];let hashchange,closed=0;
const main={querySelectorAll:()=>sections,querySelector:s=>s==='.page-heading'?heading:{textContent:''},scrollIntoView(){}};
const context=vm.createContext({location:{hash:''},window:{addEventListener:(_,f)=>hashchange=f,kobraCamera:{close:()=>closed++}},document:{querySelectorAll:()=>links,querySelector:()=>main,getElementById:id=>id==='help'?help:picker},Object});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../static/navigation.js'),'utf8'),context);
function nav(hash){context.location.hash=hash;hashchange();}
assert(!sections[1].classes.has('workspace-hidden'));assert(sections[3].classes.has('workspace-hidden'));
nav('#orders');assert.equal(closed,1);assert(!sections[3].classes.has('workspace-hidden'));assert(sections[1].classes.has('workspace-hidden'));assert.equal(links[1].attrs['aria-current'],'page');
nav('#spools');assert(!sections[6].classes.has('workspace-hidden'));assert(!sections[8].classes.has('workspace-hidden'));assert(sections[3].classes.has('workspace-hidden'));
nav('#help');assert(!help.classes.has('workspace-hidden'));assert(help.scrolled);assert(picker.classes.has('workspace-hidden'));
nav('#printer-switcher');assert(!sections[1].classes.has('workspace-hidden'));assert(!picker.classes.has('workspace-hidden'));
nav('#unknown');assert(!sections[1].classes.has('workspace-hidden'));
console.log('6 navigation cases passed: overview, orders/camera release, spools/climate, help deep link, overview return, invalid hash');
