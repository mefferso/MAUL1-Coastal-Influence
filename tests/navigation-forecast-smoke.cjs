const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const navigation = require('../site/navigation.js');
const forecast = require('../site/forecast-view.js');

const html = fs.readFileSync('site/index.html', 'utf8');
assert.match(html, /aria-label="Application views"/);
assert.match(html, /role="tab"[^>]*aria-selected="true"[^>]*>Current Forecast/);
assert.match(html, /id="current-forecast-view"[^>]*>/);
assert.match(html, /id="forecast-verification-view"[^>]*hidden/);
assert.match(html, /id="historical-research-view"[^>]*hidden/);
for (const id of ['event', 'replay', 'phase6-content', 'research-current', 'map', 'phase3b-results', 'phase5a-results', 'phase5b-summary', 'phase4-summary']) {
  assert.ok(html.includes(`id="${id}"`), `preserved application element ${id}`);
}
assert.match(html, /Research \/ Shadow Evaluation \/ Not Operational/);
assert.match(fs.readFileSync('site/style.css','utf8'), /@media\(max-width:850px\)/);
assert.match(fs.readFileSync('site/style.css','utf8'), /\.app-view\[hidden\]\{display:none!important\}/);
assert.match(html, /id="forecast-chart"[^>]*role="img"/);

function makeTab(id, selected, panel) {
  const handlers = {};
  return {
    id, attributes: { 'aria-controls': panel.id, 'aria-selected': String(selected), tabindex: selected ? '0' : '-1' },
    addEventListener: (name, fn) => handlers[name] = fn,
    getAttribute(name) { return this.attributes[name]; },
    setAttribute(name, value) { this.attributes[name] = value; },
    focus() { this.focused = true; },
    dispatch(name, event = {}) { handlers[name]?.(event); }
  };
}
function element(id) { return { id, hidden: id !== 'current-forecast-view', attributes: {}, setAttribute(n,v){this.attributes[n]=v;} }; }
const panels = ['current-forecast-view','forecast-verification-view','historical-research-view'].map(element);
const tabs = panels.map((p,i)=>makeTab(`tab-${i}`,i===0,p));
const byId = new Map(panels.map(p=>[p.id,p]));
const winHandlers = {};
const win = { location:{hash:''}, history:{replaceState(_a,_b,hash){win.location.hash=hash;}}, addEventListener:(n,f)=>winHandlers[n]=f };
navigation.initNavigation({querySelectorAll:()=>tabs,getElementById:id=>byId.get(id)},win);
assert.equal(panels[0].hidden,false);
assert.equal(panels[1].hidden,true);
tabs[1].dispatch('click');
assert.equal(tabs[1].attributes['aria-selected'],'true');
assert.equal(panels[1].hidden,false);
assert.equal(win.location.hash,'#forecast-verification-view');
tabs[1].dispatch('keydown',{key:'ArrowRight',preventDefault(){}});
assert.equal(tabs[2].attributes['aria-selected'],'true');
assert.equal(tabs[2].focused,true);
assert.equal(panels[2].hidden,false);

const now=Date.now();
const iso=offset=>new Date(now+offset*60000).toISOString();
const issueTime=iso(-10);
const anchorTime=iso(-20);
const issue = {
  mode:'authentic', actual_issue_time_utc:issueTime, model_anchor_time_utc:anchorTime,
  latest_maul1_native_stage_ft:2.44,
  forecasts:{
    6:{valid_time_utc:iso(5*60),effective_lead_hours:5.1,models:{
      persistence:{status:'issued',predicted_stage_native_ft:2.44,predicted_change_ft:0},
      phase5a_maul1_only:{status:'issued',predicted_stage_native_ft:2.53,predicted_change_ft:.09,interval_lower_ft:2.38,interval_upper_ft:2.67},
      phase5a_coastal:{status:'issued',predicted_stage_native_ft:2.54,predicted_change_ft:.10,interval_lower_ft:2.44,interval_upper_ft:2.63}
    }},
    24:{valid_time_utc:iso(23*60),effective_lead_hours:23.1,models:{
      persistence:{status:'issued',predicted_stage_native_ft:2.44,predicted_change_ft:0}
    }}
  }
};
const guidance=forecast.renderGuidance(issue);
assert.match(guidance,/No preferred model has been established/);
assert.match(guidance,/model spread/);
assert.match(guidance,/6-hour guidance/);
assert.match(guidance,/24-hour guidance/);
assert.match(guidance,/12 hours.*unavailable|12-hour.*unavailable/i);
assert.match(forecast.renderGuidance({...issue,mode:'simulation'}),/No compatible authentic/);
assert.deepEqual(forecast.buildTraces({...issue,mode:'simulation'}),[]);
const traces=forecast.buildTraces(issue);
assert.equal(traces.length,3);
assert.ok(traces.every(t=>t.issuance===issueTime));
assert.ok(traces.some(t=>t.name==='Persistence'));
assert.deepEqual(traces.find(t=>t.name==='Phase 5A · coastal predictors').x,[0,5.1]);
assert.ok(traces.find(t=>t.name==='Phase 5A · coastal predictors').error_y);
const withObservation={...issue,snapshot:{availability:{MAUL1_00065:{status:'eligible',observation:{station:'MAUL1',parameter:'stage',datum:'gage height',units:'ft',value:2.45,valid_time_utc:iso(-25),retrieved_utc:issueTime,source:'USGS NWIS IV',qc:['P']}}}}};
const observedTraces=forecast.buildTraces(withObservation);
const observed=observedTraces.find(t=>t.name==='Latest observation · USGS 00065');
assert.ok(observed);
assert.equal(observed.mode,'markers');
assert.ok(Math.abs(observed.x[0]+(5/60))<1e-6);
assert.ok(observedTraces.find(t=>t.name==='Phase 5A · coastal predictors').x[0]===0);
const staleObservation=JSON.parse(JSON.stringify(withObservation));staleObservation.snapshot.availability.MAUL1_00065.observation.valid_time_utc=iso(-240);
assert.equal(forecast.buildTraces(staleObservation).some(t=>t.name==='Latest observation · USGS 00065'),false);
const badObservation=JSON.parse(JSON.stringify(withObservation));badObservation.snapshot.availability.MAUL1_00065.observation.datum='NAVD88';
assert.equal(forecast.buildTraces(badObservation).some(t=>t.name==='Latest observation · USGS 00065'),false);
const mislabeledObservation=JSON.parse(JSON.stringify(withObservation));mislabeledObservation.snapshot.availability.MAUL1_00065.observation.datum='gage height NAVD88';
assert.equal(forecast.buildTraces(mislabeledObservation).some(t=>t.name==='Latest observation · USGS 00065'),false);
const mislabeledForecast=JSON.parse(JSON.stringify(issue));mislabeledForecast.forecasts['6'].datum='gage height NAVD88';
assert.match(forecast.renderGuidance(mislabeledForecast),/6-hour guidance.*unavailable/i);
assert.equal(forecast.buildTraces(mislabeledForecast).some(t=>t.name==='Phase 5A · coastal predictors'&&t.x.includes(5.1)),false);
const incompatible={...issue,datum:'NAVD88'};
assert.deepEqual(forecast.buildTraces(incompatible),[]);
console.log('v1.1 navigation and forecast view smoke checks passed');
