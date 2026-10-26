const fs=require('fs');
const path=require('path');
const vm=require('vm');
const assert=require('node:assert/strict');
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{id,innerHTML:'',textContent:'',value:'0',addEventListener(){},disabled:false});return elements.get(id)}
function read(file){return JSON.parse(fs.readFileSync(file,'utf8'))}
const fetch=async requestPath=>{const file=path.normalize(path.join('site',requestPath));try{return {ok:true,json:async()=>read(file)}}catch{return {ok:false,json:async()=>null}}};
const latest=read('site/data/prospective/latest.json');
const view={renderArchiveCycleHealth:()=>'',renderGuidance:()=>'<p>Latest authentic issue fixture</p>',buildTraces:()=>[],renderVerificationOverview:()=>''};
const window={MAUL1EvidenceReadiness:null,MAUL1ResearchDashboard:{loadLatestIssue:async()=>({latest,record:latest})},MAUL1ForecastView:view};
const context=vm.createContext({window,document:{getElementById:element},fetch,Date,Promise,console});
vm.runInContext(fs.readFileSync('site/phase6-readiness.js','utf8'),context);
vm.runInContext(fs.readFileSync('site/phase6.js','utf8'),context);
(async()=>{
  for(let i=0;i<200&&!element('phase6-content').innerHTML.includes('AUTHENTIC PROSPECTIVE EVIDENCE');i++) await new Promise(resolve=>setTimeout(resolve,10));
  const html=element('phase6-content').innerHTML;
  assert.match(html,/AUTHENTIC PROSPECTIVE EVIDENCE/);
  assert.match(html,/INSUFFICIENT FOR CHALLENGER PROMOTION/);
  assert.match(html,/MAE: model \/ persistence \/ Δ/);
  assert.match(html,/Predeclared substantial-rise evidence/);
  assert.match(html,/Owner approval required/);
  assert.match(html,/Phase 6\.16 \+53m11s timing erratum/);
  assert.match(html,/native gage height/);
  assert.match(html,/not computed/);
  console.log('Phase 6 dashboard renders prospective evidence readiness');
})().catch(error=>{console.error(error);process.exitCode=1;});
