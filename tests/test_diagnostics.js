'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
class Element{constructor(){this.handlers={};this.children=[];this.hidden=true;}addEventListener(k,f){this.handlers[k]=f;}setAttribute(k,v){this[k]=v;}append(...v){this.children.push(...v);}replaceChildren(){this.children=[];}focus(){}select(){this.selected=true;}}
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
let copied='',failed=false,unauthorized=false,clipboardFails=false,login=0,reason='';
const report={version:'fixture',read_only:true,uptime_seconds:120,printers:[{number:1,state:'online',age_seconds:2,temperature_current:true}],camera_decoder_ready:true,history:{available:true,jobs:7},notifications:{worker_running:true,devices:2,pending:0,devices_with_errors:0}};
const window={isSecureContext:true,Notification:{},PushManager:{},matchMedia:()=>({matches:false}),kobraNotifications:{support:()=>reason},kobraAuth:{login:()=>login++}};
const context=vm.createContext({window,location:{protocol:'https:'},navigator:{userAgent:'Android fixture',platform:'Linux',serviceWorker:{},clipboard:{writeText:async text=>{if(clipboardFails)throw Error('blocked');copied=text;}}},Notification:{permission:'granted'},document:{getElementById:node,createElement:()=>new Element()},AbortSignal,fetch:async()=>({ok:!failed&&!unauthorized,status:unauthorized?401:failed?503:200,json:async()=>report})});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/diagnostics.js'),'utf8'),context);
const tick=()=>new Promise(resolve=>setImmediate(resolve)),click=id=>node(id).handlers.click(),text=()=>node('check-results').children.map(v=>v.children[1].children.map(x=>x.textContent).join(' ')).join('\n');
(async()=>{
 node('check-content').hidden=true;click('check-open');await tick();assert.match(text(),/7 gespeicherte Aufträge/);assert.match(text(),/2 angemeldete Geräte/);assert.equal(node('check-copy').disabled,false);
 await click('check-copy');assert.equal(JSON.parse(copied).browser.https,true);assert.equal('userAgent' in JSON.parse(copied).browser,false);
 report.printers[0].temperature_current=false;await click('check-run');assert.match(text(),/Temperaturwerte fehlen/);
 report.printers[0].state='offline';report.camera_decoder_ready=false;report.notifications.devices_with_errors=1;await click('check-run');assert.match(text(),/Verbindung unterbrochen/);assert.match(text(),/FFmpeg auf dem Monitor-Rechner/);assert.match(text(),/Geräte mit Zustellfehler/);
 reason='Öffne den Monitor über seine HTTPS-Adresse.';await click('check-run');assert.match(text(),/Einrichtung benötigt Aufmerksamkeit/);reason='';
 clipboardFails=true;await click('check-copy');assert.equal(node('check-report').hidden,false);assert.equal(node('check-report').selected,true);
 failed=true;await click('check-run');assert.equal(node('check-copy').disabled,true);assert.match(node('check-message').textContent,/nicht erreichbar/);assert.equal(node('check-results').children.length,0);failed=false;
 unauthorized=true;await click('check-run');assert.equal(login,1);assert.match(node('check-message').textContent,/erneut anmelden/);
 console.log('8 diagnostics cases passed: summary, safe export, stale temperature, outage/decoder/delivery help, browser help, clipboard fallback, failed request, expired session');
})().catch(error=>{console.error(error);process.exitCode=1;});
