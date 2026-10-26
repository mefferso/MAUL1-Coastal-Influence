const assert = require('node:assert/strict');
const readiness = require('../site/phase6-readiness.js');

const history = [
  {issuance_id:'a',mode:'authentic',actual_issue_time_utc:'2026-10-22T00:00:00Z',verification_files:['../verification/a-0001.json']},
  {issuance_id:'b',mode:'authentic',actual_issue_time_utc:'2026-10-23T00:00:00Z',verification_files:['../verification/b-0001.json']},
  {issuance_id:'sim',mode:'simulation',actual_issue_time_utc:'2026-10-23T01:00:00Z',verification_files:[]},
];
const performance = {
  evaluation_time_utc:'2026-10-24T00:00:00Z',
  verification_completeness:{
    'persistence:6h':{forecast_slots:2,issued:2,matured:2,verified:1,due_unverified:1,not_yet_due:0,abstained:0,other_unavailable:0},
    'phase5a_coastal:6h':{forecast_slots:2,issued:1,matured:1,verified:1,due_unverified:0,not_yet_due:0,abstained:1,other_unavailable:0},
    'persistence:12h':{forecast_slots:2,issued:2,matured:1,verified:0,due_unverified:1,not_yet_due:1,abstained:0,other_unavailable:0},
  },
  model_horizon_metrics:{
    'persistence:6h':{n:1,mae_ft:.2,rmse_ft:.2,bias_ft:-.2,mae_persistence_ft:.2,rises:{'0.50':{hits:0,misses:1,false_alarms:0}},qualifying_24h_events:null,observation_latency_minutes:{n:1,median:40,p90:40}},
    'phase5a_coastal:6h':{n:1,mae_ft:.1,rmse_ft:.1,bias_ft:-.1,mae_persistence_ft:.2,rises:{'0.50':{hits:0,misses:1,false_alarms:2}},qualifying_24h_events:null,observation_latency_minutes:{n:1,median:40,p90:40}},
    'persistence:12h':{n:0,mae_ft:null,rmse_ft:null,bias_ft:null,qualifying_24h_events:{event_count:1,status:'insufficient_independent_events'}},
    'phase5a_coastal:24h':{n:1,mae_ft:.2,rmse_ft:.2,bias_ft:0,qualifying_24h_events:{event_count:2,status:'insufficient_independent_events'}},
  },
};
const latest = {issuance_id:'b',actual_issue_time_utc:'2026-10-23T00:00:00Z',feature_anchor_time_utc:'2026-10-23T00:00:00Z',snapshot:{availability:{
  MAUL1_00065:{status:'eligible',age_hours:.5},MCHL1:{status:'missing',age_hours:null},NWCL1:{status:'stale',age_hours:3},
}}};
const gates = {owner_approval:{status:'pending'},thresholds:{minimum_verified_issue_target_pairs_per_horizon:100,minimum_predeclared_rise_groups:20}};
const verifications = [
  {issuance_id:'a',horizon_hours:6,model:'persistence',observation_valid_time_utc:'2026-10-22T06:00:00Z',observed_native_stage_ft:2,predicted_native_stage_ft:2.2,revision:1},
  {issuance_id:'a',horizon_hours:6,model:'phase5a_coastal',observation_valid_time_utc:'2026-10-22T06:00:00Z',observed_native_stage_ft:2,predicted_native_stage_ft:2.1,revision:1},
  {issuance_id:'b',horizon_hours:6,model:'persistence',observation_valid_time_utc:'2026-10-23T06:00:00Z',observed_native_stage_ft:2.3,predicted_native_stage_ft:2.3,revision:1},
  {issuance_id:'b',horizon_hours:6,model:'phase5a_coastal',observation_valid_time_utc:'2026-10-23T06:00:00Z',observed_native_stage_ft:2.4,predicted_native_stage_ft:2.5,revision:1},
  {issuance_id:'sim',horizon_hours:6,model:'phase5a_coastal',observation_valid_time_utc:'2026-10-23T06:00:00Z',observed_native_stage_ft:2.4,predicted_native_stage_ft:1,revision:1},
];
const summary = readiness.summarizeReadiness(history,performance,latest,gates,verifications);
assert.equal(JSON.stringify(summary),JSON.stringify(readiness.summarizeReadiness(history,performance,latest,gates,verifications.slice().reverse())));
assert.equal(summary.authenticIssuanceCount,2);
assert.equal(summary.horizons.find(x=>x.horizon===6).issueTargetSlots,2);
assert.equal(summary.horizons.find(x=>x.horizon===6).maturedSlots.min,1);
assert.equal(summary.horizons.find(x=>x.horizon===6).verifiedPerModel.min,1);
assert.equal(summary.horizons.find(x=>x.horizon===6).dueUnverifiedModelPairs,1);
assert.equal(summary.sources.find(x=>x.name==='MCHL1').status,'missing');
assert.equal(summary.sources.find(x=>x.name==='MCHL1').ageHours,null);
assert.equal(summary.sources.find(x=>x.name==='NWCL1').ageHours,3);
const comparison=summary.comparisons.find(x=>x.model==='phase5a_coastal'&&x.horizon===6);
assert.equal(comparison.pairedN,1); // issue b has a different observed value; only issue a pairs
assert.ok(Math.abs(comparison.modelStats.rmseFt-0.1)<1e-12);
assert.ok(Math.abs(comparison.persistenceStats.rmseFt-0.2)<1e-12);
assert.equal(comparison.falseAlarmPairs,2);
assert.equal(summary.eventReadiness.eventGroupCount,2);
assert.equal(summary.eventReadiness.status,'insufficient_independent_events');
assert.equal(summary.eventReadiness.eventMisses,null);
assert.equal(summary.falseAlertEpisodes.status,'not_computed');
assert.equal(summary.gateApproval.status,'pending');
const html=readiness.renderReadiness(summary);
for (const label of ['AUTHENTIC PROSPECTIVE EVIDENCE','Research / shadow only','insufficient','Hindcast','independent event groups','False-alert episodes','Owner approval required','MCHL1','Phase 6.17 evidence definitions and gate rationale']) assert.match(html,new RegExp(label,'i'));
assert.match(html,/actual issuance/i);
assert.match(html,/feature anchor/i);
console.log('Phase 6 evidence-readiness checks passed');
