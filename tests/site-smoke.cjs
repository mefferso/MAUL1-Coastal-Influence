const fs=require('fs');const vm=require('vm');const zlib=require('zlib');const assert=require('assert/strict');
const elements=new Map();const callbacks={};
function element(id){if(!elements.has(id))elements.set(id,{value:'',textContent:'',innerHTML:'',removeAllListeners(){},on(){}});return elements.get(id)}
const window={MAUL1ChartTheme:require('../site/chart-theme.js'),DecompressionStream:global.DecompressionStream,addEventListener:(name,callback)=>callbacks[name]=callback};
const Plotly={react:async()=>{},relayout:()=>{}};
const L={map:()=>({setView(){return this}}),tileLayer:()=>({addTo(){}}),divIcon:options=>options,marker:()=>({addTo(){return this},bindPopup(){}})};
const fetch=async(path)=>({ok:true,json:async()=>JSON.parse(fs.readFileSync('site/'+path,'utf8')),body:new ReadableStream({start(controller){controller.enqueue(fs.readFileSync('site/'+path));controller.close()}})});
assert.match(fs.readFileSync('site/index.html','utf8'),/Experimental event onset/);
assert.match(fs.readFileSync('site/index.html','utf8'),/Independent Event Verification/);
assert.match(fs.readFileSync('site/index.html','utf8'),/Phase 5A experimental hindcasts/);
assert.match(fs.readFileSync('site/app.js','utf8'),/loadPhase5A/);
assert.match(fs.readFileSync('site/index.html','utf8'),/Phase 5B tidal-aware robustness experiments/);
assert.match(fs.readFileSync('site/app.js','utf8'),/loadPhase5B/);
if(fs.existsSync('site/data/history/phase5a/summary.json')){
  const phase5a=JSON.parse(fs.readFileSync('site/data/history/phase5a/summary.json','utf8'));
  assert.equal(phase5a.schema_version,'5A.1');
  assert.ok(phase5a.holdout_results['6'].methods.persistence.n>0);
  assert.match(fs.readFileSync('site/data/history/phase5a/report.md','utf8'),/Holdout verification/);
  assert.ok(fs.statSync('site/data/history/phase5a/predictions.csv.gz').size>0);
}
if(fs.existsSync('site/data/history/phase5b/summary.json')){
  const phase5b=JSON.parse(fs.readFileSync('site/data/history/phase5b/summary.json','utf8'));
  assert.equal(phase5b.schema_version,'5B.1');
  assert.equal(phase5b.astronomical_prediction_availability.verified_advance_availability,false);
  assert.ok(phase5b.holdout_results['6'].full_multivariable.n>0);
  assert.match(fs.readFileSync('site/data/history/phase5b/report.md','utf8'),/not operational forecasts/);
  assert.ok(fs.statSync('site/data/history/phase5b/predictions.csv.gz').size>0);
}
const context=vm.createContext({DecompressionStream:global.DecompressionStream,window,document:{getElementById:element},fetch,Plotly,L,Date,Promise,Response,console});vm.runInContext(fs.readFileSync('site/app.js','utf8'),context);
callbacks.load();
setTimeout(()=>{assert.match(element('status').textContent,/Archive generated/);assert.match(element('phase4-summary').textContent,/189 retrospective MAUL1 responses/);assert.match(element('phase4-cases').textContent,/Tropical Storm Beta/);assert.match(element('summary').textContent,/real observations/);assert.match(element('coverage').innerHTML,/DENL1/);assert.match(element('verification-summary').innerHTML,/target signal episode/);assert.equal(vm.runInContext("until([{time:'2020-01-01T00:00:00Z'},{time:'2020-01-01T01:00:00Z'}], '2020-01-01T00:00:00Z').length",context),1);console.log('Site loads compressed real event and renders research diagnostics')},1500);
