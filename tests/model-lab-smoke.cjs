'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const api = require('../site/model-lab.js');
const ids = ['model-lab-view','model-lab-status','model-lab-horizon','model-lab-regime','model-lab-case',
  'model-lab-metrics','model-lab-annual','model-lab-ablations','model-lab-events','model-lab-missingness','model-lab-trajectories','model-lab-failures',
  'model-lab-case-note','model-lab-case-chart','model-lab-provenance'];
const elements = new Map(ids.map(id => [id, {id, hidden:id==='model-lab-view', value:id==='model-lab-horizon'?'24':id==='model-lab-regime'?'all paired cases':'',
  innerHTML:'',textContent:'',listeners:{},addEventListener(name,fn){this.listeners[name]=fn;}}]));
const document = {getElementById:id=>elements.get(id)||null};
const plotCalls=[];
const Plotly={react:(id,traces,layout)=>plotCalls.push({id,traces,layout}),Plots:{resize(){}}};
const handlers={};
const win={Plotly,fetch:async()=>({ok:true,json:async()=>fixture()}),addEventListener:(name,fn)=>{handlers[name]=fn;}};
function fixture(){
  const fields=['persistence_ft','maul1_only_ft','maul1_plus_coastal_ft','maul1_coastal_tidal','full_multivariable','bounded_damped_trend_ft'];
  const metric=Object.fromEntries(fields.map(k=>[k,{label:k,n:2,mae_ft:.1,rmse_ft:.12,bias_ft:0,skill_vs_persistence:.4}]));
  const horizons={};
  const trajectory=Object.fromEntries(fields.map(k=>[k,{direction_correct_fraction:.6,direction_cases_abs_change_at_least_0_02_ft:10,rising_target_n:5,underforecast_fraction_on_rising_targets:.4,threshold_timing_eligible_issue_count:4,mean_absolute_horizon_timing_error_hours:3,threshold_timing_missed_by_forecast_n:1}]));
  for(const h of ['6','12','24']) horizons[h]={paired_sample_n:2,regimes:{'all paired cases':{models:metric}},improvement_vs_persistence_bootstrap:Object.fromEntries(fields.map(k=>[k,{improvement_ft_ci95:[.01,.03]}])),annual_and_seasonal:{'year:2024':metric,'season:winter':metric},issue_feature_missingness:{maul1_change_6h_ft:{available_n:2,missing_n:0,missing_fraction:0}},trajectory_diagnostics:trajectory,event_groups:Object.fromEntries(fields.map(k=>[k,{event_count:2}])),underforecast_and_false_alarm:Object.fromEntries(fields.map(k=>[k,{label:k,paired_target_windows_n:2,true_positive_target_windows:1,false_positive_target_windows:0,missed_rise_target_windows:1,false_alert_episode_clusters:0}]))};
  const methods=Object.fromEntries(fields.map(k=>[k,2.1]));
  const point={issue_time_utc:'2024-03-01T00:00:00Z',valid_time_utc:'2024-03-01T06:00:00Z',observed_stage_ft:2,forecasts:methods};
  return {schema:'maul1.model-lab.report.v1',summary:{archive_first_observation_utc:'2016-01-01T00:00:00Z',archive_last_observation_utc:'2026-10-20T12:00:00Z'},
    horizons,challenger_headline:Object.fromEntries(['6','12','24'].map(h=>[h,{bounded_damped_trend_ft:{beats_persistence:false,beats_maul1_only:false}}])),
    predictor_ablations:Object.fromEntries(['6','12','24'].map(h=>[h,{maul1_additive_value_and_degradation:metric}])),
    worst_event_failures_phase5b_coastal_tidal:{'6':[],'12':[],'24':[]},
    case_studies:[{case_id:'case-1',label:'Example retrospective case',selection:'Illustration only.',anchor_issue_time_utc:'2024-03-01T00:00:00Z',anchor_valid_time_utc:'2024-03-02T00:00:00Z',target_rise_from_issue_ft:.5,observations:[{time_utc:'2024-03-01T00:00:00Z',stage_ft:2},{time_utc:'2024-03-01T06:00:00Z',stage_ft:2.1}],forecasts_by_horizon:{'6':[point],'12':[point],'24':[point]}}],
    phase6_qualifying_rise_groups_24h:Object.fromEntries(fields.map(k=>[k,{event_count:6,status:'computed',detected_events:2,missed_events:4,detection_rate:1/3,median_lead_to_first_qualifying_verification_target_hours:24}])),
    provenance:{target:'USGS 07380215 00065, ft native gage height',hourly_archive_months:130},baseline_reproduction:{status:'matched'},promotion_criteria:{criteria:['future independent shadow validation']}};
}
(async()=>{
  const app=api.init(document,win);
  handlers['maul1:viewchange']({detail:{panelId:'model-lab-view'}});
  await new Promise(resolve=>setTimeout(resolve,0));
  assert.match(elements.get('model-lab-status').textContent,/does not beat both persistence and MAUL1-only/);
  assert.match(elements.get('model-lab-metrics').innerHTML,/Damped-trend challenger/);
  assert.equal(plotCalls.length,1);
  assert.equal(plotCalls[0].traces[0].mode,'lines');
  assert.equal(plotCalls[0].traces[0].connectgaps,false);
  assert.equal(plotCalls[0].traces.slice(1).length,6);
  assert.ok(plotCalls[0].traces.slice(1).every(trace=>trace.mode==='markers'));
  assert.ok(plotCalls[0].traces[1].hovertemplate.includes('Issued:'));
  elements.get('model-lab-horizon').value='6';
  elements.get('model-lab-horizon').listeners.change();
  assert.equal(plotCalls.length,2);
  assert.equal(app.getReport().schema,'maul1.model-lab.report.v1');
  console.log('Model Lab smoke passed: report loads on tab activation, controls rerender, issuance markers stay separate.');
})().catch(error=>{console.error(error);process.exitCode=1;});
