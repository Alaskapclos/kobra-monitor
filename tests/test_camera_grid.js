'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
class Element {
 constructor(){this.children=[];this.handlers={};this.parentElement={hidden:false};this.hidden=true;this.value='';}
 addEventListener(k,f){this.handlers[k]=f;}setAttribute(k,v){this[k]=v;}removeAttribute(k){this[k]='';}
 replaceChildren(){this.children=[];}append(...items){this.children.push(...items);}
 querySelector(selector){return this.children.find(c=>c.tag===selector);}
 querySelectorAll(selector){return this.children.filter(c=>selector==='.'+c.className);}
}
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
let token=0,releaseGate=null;const released=[],active=new Set();
const context=vm.createContext({window:{kobraAuth:{releaseCameras:async viewer=>{released.push(viewer);if(releaseGate)await releaseGate;}}},document:{hidden:false,getElementById:node,addEventListener(){},createElement:tag=>Object.assign(new Element(),{tag})},crypto:{getRandomValues:bytes=>{bytes[15]=++token;return bytes;}},URLSearchParams});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/camera.js'),'utf8'),context);
context.window.KobraCameraFrame=class{constructor(ip,image,message,viewer){Object.assign(this,{ip,image,message,viewer});}open(){active.add(this);}close(){active.delete(this);}};
const camera=context.window.kobraCamera,tick=()=>new Promise(resolve=>setImmediate(resolve));
const ips=()=>[...active].map(v=>v.ip);const click=id=>node(id).handlers.click();const change=(id,value)=>{node(id).value=value;node(id).handlers.change();};
const printers=Array.from({length:7},(_,i)=>({ip:'192.168.1.'+(20+i),data:{printer_name:'Drucker '+i}}));
(async()=>{
 camera.setPrinters(printers);camera.setPrinter(printers[0].ip,true);change('camera-mode','all');click('camera-open');await tick();assert.deepEqual(ips(),printers.slice(0,4).map(p=>p.ip));assert.equal(node('camera-grid').children.length,4);
 let allow;releaseGate=new Promise(resolve=>allow=resolve);click('camera-next');await tick();assert.equal(active.size,0,'Old page closes before next starts');allow();releaseGate=null;await tick();assert.deepEqual(ips(),printers.slice(4).map(p=>p.ip));assert.equal(node('camera-next').disabled,true);assert.match(node('camera-page-label').textContent,/Seite 2 von 2/);assert.equal(released.length,1);
 change('camera-page-size','2');await tick();assert.deepEqual(ips(),printers.slice(0,2).map(p=>p.ip));assert.match(node('camera-page-label').textContent,/Seite 1 von 4/);
 camera.setPrinter(printers[5].ip,true);assert.deepEqual(ips(),printers.slice(0,2).map(p=>p.ip),'Status selection does not replace matrix');
 camera.setPrinters([...printers].reverse());await tick();assert.deepEqual(ips(),printers.slice(-2).reverse().map(p=>p.ip),'Follow saved printer order');
 change('camera-mode','single');await tick();assert.deepEqual(ips(),[printers[5].ip]);camera.close();assert.equal(active.size,0);
 camera.setPrinters([]);change('camera-mode','all');assert.equal(node('camera-open').disabled,true);assert.match(node('camera-page-label').textContent,/Seite 1 von 1/);
 console.log('7 camera grid cases passed: four tiles, page release before acquire, two tiles, independent selection, reorder, single/close, empty fleet');
})().catch(error=>{console.error(error);process.exitCode=1;});
