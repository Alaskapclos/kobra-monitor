'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const nodes=new Map();
const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',addEventListener(){}});return nodes.get(id);};
let sent=null,fail=false;
const context=vm.createContext({document:{getElementById:node},window:{addEventListener(){},kobraAuth:{ready:new Promise(()=>{}),reorder:async ips=>{sent=[...ips];if(fail)throw Error('Speichern fehlgeschlagen');return [...ips];}}},Date,AbortSignal,setTimeout:()=>0,clearTimeout(){},setInterval(){},fetch:()=>new Promise(()=>{})});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/monitor.js'),'utf8'),context);
const run=script=>vm.runInContext(script,context),list=script=>Array.from(run(script));
(async()=>{
 assert.deepEqual(list("reorderedIps(['a','b','c'],'c','a')"),['c','a','b']);
 assert.deepEqual(list("reorderedIps(['a','b','c'],'a','c')"),['b','c','a']);
 assert.deepEqual(list("reorderedIps(['a','b'],'missing','a')"),['a','b']);
 run("render=()=>{};lastResponse={ips:['a','b'],printers:[{ip:'a'},{ip:'b'}]};selectedIp='b';");
 await run("movePrinter('b','a')");assert.deepEqual(sent,['b','a']);assert.equal(run('selectedIp'),'b');
 assert.deepEqual(list('pendingOrder'),['b','a'],'Keep the order until a fresh server snapshot confirms it');
 fail=true;await run("movePrinter('a','b')");assert.equal(run('pendingOrder'),null);
 assert.equal(node('printer-order-status').textContent,'Speichern fehlgeschlagen');
 console.log('5 printer order cases passed (move both ways, unknown target, selection retained, failed save)');
})().catch(error=>{console.error(error);process.exitCode=1;});
