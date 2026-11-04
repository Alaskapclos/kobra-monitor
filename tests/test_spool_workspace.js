'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
 constructor(){this.children=[];this.attrs={};this.events={};this.classes=new Set();this.classList={toggle:(k,v)=>v?this.classes.add(k):this.classes.delete(k)};}
 replaceChildren(){this.children=[];}append(e){this.children.push(e);}setAttribute(k,v){this.attrs[k]=v;}addEventListener(k,f){this.events[k]=f;}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);},ace=[new Element(),new Element(),new Element()],manager=new Element();
let resolve,requests=0,ok=true,url='http://spoolman:8000/spoolman';
const context=vm.createContext({window:{},document:{getElementById:get,querySelectorAll:()=>ace,querySelector:()=>manager,createElement:()=>new Element()},fetch:async()=>{requests++;if(resolve)await new Promise(r=>resolve=r);return {ok,status:ok?200:401,json:async()=>({configured:true,url})};},URL,AbortSignal,Error});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../static/spool-workspace.js'),'utf8'),context);
const workspace=context.window.kobraSpoolWorkspace,flush=()=>new Promise(r=>setImmediate(r));
(async()=>{
 workspace.render('spools');assert.equal(requests,0);assert(manager.classes.has('spool-tab-hidden'));
 get('spool-tab-manage').events.click();await flush();assert.equal(get('spoolman-view-host').children[0].src,'/spoolman/');assert(ace.every(x=>x.classes.has('spool-tab-hidden')));assert.equal(get('spool-tab-manage').attrs['aria-pressed'],'true');
 workspace.render('orders');assert.equal(get('spoolman-view-host').children.length,0);
 workspace.render('spools');await flush();assert.equal(get('spoolman-view-host').children.length,1);
 get('spool-tab-ace').events.click();assert.equal(get('spoolman-view-host').children.length,0);assert(ace.every(x=>!x.classes.has('spool-tab-hidden')));
 ok=false;get('spool-tab-manage').events.click();await flush();assert.match(get('spoolman-view-message').textContent,/anmelden/);assert.equal(get('spoolman-view-host').children.length,0);
 ok=true;url='http://spoolman:8000';get('spoolman-reload').events.click();await flush();assert.match(get('spoolman-view-message').textContent,/nicht eingerichtet/);
 console.log('7 spool workspace cases passed: lazy load, native frame, leave, return, ACE return, expired login, legacy setup');
})().catch(e=>{console.error(e);process.exitCode=1;});
