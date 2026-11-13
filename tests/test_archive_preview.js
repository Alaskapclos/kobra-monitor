/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.events={};this.hidden=true;this.value='';this.textContent='';this.isConnected=true;}
 append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;}
 setAttribute(){}addEventListener(name,fn){this.events[name]=fn;}focus(){this.focused=true;}
 getContext(){return {clearRect(){},beginPath(){},moveTo(){},lineTo(){},closePath(){},fill(){},stroke(){}};}
 getBoundingClientRect(){return {width:400,height:300};}
}
const ids=new Map(),pending=[],listeners={};
const context=vm.createContext({window:{addEventListener:(name,fn)=>{listeners[name]=fn;},kobraAuth:{authenticated:true}},
 document:{getElementById:id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);},createElement:tag=>new Element(tag)},
 URLSearchParams,AbortController,URL,Blob,ResizeObserver:class{observe(){}disconnect(){}},
 requestAnimationFrame:()=>1,cancelAnimationFrame(){},fetch:(url,options)=>new Promise(resolve=>pending.push({url,options,resolve}))});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../static/archive-preview.js'),'utf8'),context);
const api=context.window.kobraPreview;
const file=name=>({sha256:'a'.repeat(64),names:[name]});
const response=value=>({ok:true,json:async()=>value});
const children=()=>ids.get('file-preview-body').children;
(async()=>{
 // An earlier request must not replace a newer selection.
 const first=api.open(file('<img onerror=alert(1)>'),new Element());
 const second=api.open(file('Second'),new Element());
 pending[1].resolve(response({images:[],sources:[]}));await second;
 pending[0].resolve(response({images:['old.png'],sources:[]}));await first;
 assert.equal(ids.get('file-preview-title').textContent,'Second');
 assert.equal(children()[1].textContent,'Keine unterstützten Vorschaudaten enthalten.');
 assert.equal(pending[0].options.signal.aborted,true);
 // Closing while a geometry request runs keeps it closed and empty.
 const opened=api.open(file('Model'),new Element());pending[2].resolve(response({images:[],sources:[{kind:'model',name:'3D/a.model'}]}));await opened;
 const loading=children()[0].children[0].events.click();
 api.close();pending[3].resolve(response({kind:'model',triangles:[[0,0,0,1,0,0,0,1,0]],note:'test'}));await loading;
 assert.equal(ids.get('file-preview').hidden,true);assert.equal(children().length,0);
 // Display server rejection as ordinary text and keep the original link.
 const failed=api.open(file('Unsupported'),new Element());pending[4].resolve(response({images:[],sources:[{kind:'gcode',name:'a.gcode'}]}));await failed;
 const error=children()[0].children[0].events.click();pending[5].resolve({ok:false,json:async()=>({error:'Kurven nicht unterstützt'})});await error;
 assert.equal(children()[1].textContent,'Kurven nicht unterstützt');assert.equal(children()[3].textContent,'Originaldatei herunterladen');
 listeners.keydown({key:'Escape'});assert.equal(ids.get('file-preview').hidden,true);
 console.log('4 preview UI cases passed: stale selection, cancelled geometry, explicit rejection and Escape cleanup');
})().catch(error=>{console.error(error);process.exitCode=1;});
