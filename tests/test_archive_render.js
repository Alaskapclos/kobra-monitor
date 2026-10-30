'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const assert=require('node:assert/strict');
class Element {
  constructor(){this.children=[];this.textContent='';this.value='';this.attributes={};this.dataset={};}
  setAttribute(k,v){this.attributes[k]=String(v);}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  addEventListener(){}
}
const ids=new Map();const requests=[];
const context=vm.createContext({
 window:{addEventListener(){}},document:{getElementById:id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);},
   createElement:()=>new Element(),createElementNS:()=>new Element()},
 setInterval:()=>0,setTimeout:()=>0,clearTimeout:()=>{},AbortSignal,Date,URLSearchParams,
 fetch:url=>String(url)==='/api/status'?new Promise(()=>{}):new Promise(resolve=>requests.push({url,resolve}))
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/monitor.js'),'utf8'),context);
const response=(ip,total)=>({ok:true,json:async()=>({read_only:true,ip,jobs:[],total,page:0,pages:1,summary:{total,completed:total,active:0,cancelled:0}})});
(async()=>{
 vm.runInContext("selectedIp=archiveIp='192.168.1.101';",context);
 const first=vm.runInContext('refreshArchive()',context);
 vm.runInContext("selectedIp=archiveIp='192.168.1.102';",context);
 const second=vm.runInContext('refreshArchive()',context);
 requests[1].resolve(response('192.168.1.102',2));await second;
 requests[0].resolve(response('192.168.1.101',99));await first;
 assert.equal(ids.get('archive-total').textContent,'2','A late result for another printer must not replace the selected printer');
 assert.equal(ids.get('history-message').textContent,'2 passende Aufträge');
 ids.get('history-search').value='100%_Halter';ids.get('history-filter').value='completed';
 const third=vm.runInContext('refreshArchive()',context);
 assert.equal(new URL('http://localhost'+requests[2].url).searchParams.get('search'),'100%_Halter');
 requests[2].resolve(response('192.168.1.102',0));await third;
 assert.equal(ids.get('history-next').disabled,true);
 assert.equal(ids.get('history-prev').disabled,true);
 console.log('2 archive UI cases passed (out-of-order printer responses and literal search/pagination)');
})().catch(error=>{console.error(error);process.exitCode=1;});
