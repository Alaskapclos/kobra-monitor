'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const nodes=new Map(),revoked=[],pending=[],timers=[];let serial=0,now=1000,fail=false;
const node=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,src:'',textContent:'',handlers:{},addEventListener(k,f){this.handlers[k]=f;},setAttribute(){},removeAttribute(k){this[k]='';}});return nodes.get(id);};
const context=vm.createContext({document:{hidden:false,getElementById:node,addEventListener(){}},window:{},Date:{now:()=>now},AbortController,AbortSignal,
 URL:{createObjectURL:()=>`blob:${++serial}`,revokeObjectURL:u=>revoked.push(u)},Image:class{decode(){return new Promise((resolve,reject)=>pending.push({resolve,reject}));}},
 setTimeout:f=>{timers.push(f);return timers.length;},clearTimeout(){},fetch:async()=>{if(fail)throw Error('Testunterbrechung');return {ok:true,status:200,blob:async()=>({})};}});
context.URLSearchParams=URLSearchParams;
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/camera.js'),'utf8').split('window.kobraCamera=')[0],context);
const image=node('camera-image'),message=node('camera-message');let camera=new context.window.KobraCameraFrame('192.168.1.20',image,message,'a'.repeat(32),()=>{});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 camera.open();await tick();
 assert.equal(image.hidden,true,'No incomplete first frame');pending.shift().resolve();await tick();const first=image.src;assert.equal(image.hidden,false);
 timers.shift()();await tick();assert.equal(image.src,first,'Keep current frame during delayed decode');assert.equal(image.hidden,false);assert.equal(revoked.includes(first),false);
 pending.shift().resolve();await tick();assert.notEqual(image.src,first);assert.equal(image.hidden,false);assert.ok(revoked.includes(first));const second=image.src;
 timers.shift()();await tick();pending.shift().reject(Error('Invalid frame'));await tick();assert.equal(image.src,second);assert.match(message.textContent,/keine Live-Aktualisierung/);assert.ok(revoked.includes('blob:3'));
 fail=true;timers.shift()();await tick();assert.equal(image.src,second);assert.equal(image.hidden,false);assert.match(message.textContent,/Letztes Kamerabild/);
 now+=11000;timers.shift()();await tick();assert.equal(image.hidden,true,'Do not hold a stale frame indefinitely');assert.ok(revoked.includes(second));
 fail=false;timers.shift()();await tick();pending.shift().resolve();await tick();assert.equal(image.hidden,false,'A fresh decoded image recovers after the outage');assert.equal(image.src,'blob:4');assert.doesNotMatch(message.textContent,/Letztes Kamerabild|keine Live-Aktualisierung/);
 timers.shift()();await tick();camera.close();pending.shift().resolve();await tick();assert.equal(image.hidden,true);assert.equal(image.src,'');assert.ok(revoked.includes('blob:5'),'Discard late decoded frame of former printer');
 console.log('7 camera rendering cases passed: decode before swap, no blank replacement, failed decode, transient outage label, stale expiry, recovery, printer switch');
})().catch(error=>{console.error(error);process.exitCode=1;});
