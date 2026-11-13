/* SPDX-License-Identifier: GPL-3.0-only */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const element={hidden:true,addEventListener(){}};
const context=vm.createContext({window:{kobraAuth:{ready:Promise.resolve(),authenticated:false},addEventListener(){}},document:{getElementById:()=>element},console});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/reprints.js'),'utf8'),context);
const assess=context.window.kobraReprints.stockAssessment;
const target={ip:'192.0.2.1',slots:[{global_index:0},{global_index:1}]};
const m=(i,g)=>({paint_index:i,estimated_g:g}),a=(i,s)=>({paint_index:i,slot:s});
let reads=0;const reader=()=>{reads++;return{id:7,grams:100};};
let r=assess([m(0,80)],[a(0,0)],target,reader);assert.equal(r.rows[0].status,'enough');assert.equal(r.rows[0].missing,0);
r=assess([m(0,80)],[a(0,0)],target,()=>({id:7,grams:0}));assert.equal(r.rows[0].status,'short');assert.equal(r.rows[0].missing,80);
r=assess([m(0,50),m(1,60)],[a(0,0),a(1,0)],target,reader);assert.equal(r.rows.length,1);assert.equal(r.rows[0].needed,110);assert.equal(r.rows[0].missing,10);assert.equal(r.rows[0].slots.length,1);
r=assess([m(0,50),m(1,60)],[a(0,0),a(1,1)],target,(ip,s)=>({id:7,grams:s.global_index?100:120}));assert.equal(r.rows[0].grams,100);assert.equal(r.rows[0].status,'short');assert.equal(r.rows[0].slots.length,2);
r=assess([m(0,50),m(1,60)],[a(0,0),a(1,1)],target,(ip,s)=>({id:s.global_index+1,grams:55}));assert.equal(r.rows.length,2);assert.equal(r.rows[0].status,'enough');assert.equal(r.rows[1].missing,5);
reads=0;r=assess([m(0,80)],[a(0,null)],target,reader);assert.equal(reads,0);assert.equal(r.rows.length,0);assert.match(r.unknown[0],/auswählen/);
for(const stock of [null,undefined,{id:7,grams:null},{id:7,grams:'100'},{id:7,grams:NaN},{id:7,grams:-1},{id:null,grams:100}]){r=assess([m(0,80)],[a(0,0)],target,()=>stock);assert.equal(r.rows.length,0);assert.match(r.unknown[0],/nicht aktuell/);}
for(const value of [0,null,undefined,-1,NaN,Infinity,'30']){r=assess([m(0,50),m(1,value)],[a(0,0),a(1,0)],target,reader);assert.equal(r.rows[0].status,'unknown');assert.equal(r.unknown.length,1);}
r=assess([m(0,.1),m(1,.2)],[a(0,0),a(1,0)],target,()=>({id:7,grams:.3}));assert.equal(r.rows[0].status,'enough');
console.log('Material advisory: aggregate per physical spool, real zero, shortage, missing/invalid data, explicit slots and rounding passed');
