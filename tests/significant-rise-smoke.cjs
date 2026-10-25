'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const api = require('../site/significant-rise.js');
const html = fs.readFileSync('site/index.html','utf8');
const audit = JSON.parse(fs.readFileSync('site/data/research/significant-rise.json','utf8'));
const report = JSON.parse(fs.readFileSync('site/data/research/model-lab.json','utf8'));
for (const [tab,panel] of [['tab-current','current-forecast-view'],['tab-verification','forecast-verification-view'],['tab-history','historical-research-view'],['tab-model-lab','model-lab-view']]) {
  assert.match(html,new RegExp(`id="${tab}"[^>]*aria-controls="${panel}"`));
}
assert.match(html,/Significant-Rise Investigation/);
assert.match(html,/Retrospective \/ Development Evidence/);
const ids=['model-lab-view','model-lab-horizon','rise-event-select','rise-investigation-status','rise-investigation-metrics','rise-horizon-summary','rise-event-note','rise-stage-chart','rise-coastal-chart','rise-inland-chart','rise-diagnosis','rise-limitations'];
const elements=new Map(ids.map(id=>[id,{id,hidden:id==='model-lab-view',value:id==='model-lab-horizon'?'24':'',innerHTML:'',textContent:'',listeners:{},addEventListener(name,fn){this.listeners[name]=fn;}}]));
const document={getElementById:id=>elements.get(id)||null};
const plots=[];
const Plotly={react:(id,traces,layout)=>plots.push({id,traces,layout})};
const handlers={};
const win={Plotly,fetch:async url=>({ok:true,json:async()=>url.includes('significant-rise')?audit:report}),addEventListener:(name,fn)=>{handlers[name]=fn;}};
(async()=>{
  const app=api.init(document,win);
  handlers['maul1:viewchange']({detail:{panelId:'model-lab-view'}});
  await new Promise(resolve=>setTimeout(resolve,0));
  assert.match(elements.get('rise-investigation-status').textContent,/109 target-time groups/);
  assert.match(elements.get('rise-horizon-summary').innerHTML,/False alert episodes/);
  assert.match(elements.get('rise-horizon-summary').innerHTML,/6h MAE \(ft\)/);
  assert.match(elements.get('rise-horizon-summary').innerHTML,/12h MAE \(ft\)/);
  assert.match(elements.get('rise-horizon-summary').innerHTML,/24h MAE \(ft\)/);
  assert.match(elements.get('rise-diagnosis').innerHTML,/do not show that coastal forcing caused/);
  assert.match(elements.get('rise-limitations').innerHTML,/NAVD88/);
  assert.deepEqual(plots.map(plot=>plot.id),['rise-stage-chart','rise-coastal-chart','rise-inland-chart']);
  assert.ok(plots.every(plot=>plot.traces.every(trace=>trace.connectgaps===false)));
  assert.ok(plots[0].traces.some(trace=>trace.name.includes('experimental')));
  assert.equal(elements.get('rise-event-select').listeners.change instanceof Function,true);
  assert.equal(app!==null,true);
  console.log('Significant-rise Model Lab smoke passed: four tabs remain, paired metrics and selectable issue/valid-time timelines render with datum labels and unconnected data gaps.');
})().catch(error=>{console.error(error);process.exitCode=1;});
