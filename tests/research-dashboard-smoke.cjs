const assert = require('node:assert/strict');
const fs = require('node:fs');
const { renderCurrentConditions, hydrateLatestIssue, loadLatestIssue } = require('../site/research-dashboard.js');
const forecast = require('../site/forecast-view.js');

const issue = {
  mode: 'authentic', actual_issue_time_utc: '2026-10-23T13:27:17Z',
  latest_maul1_native_stage_ft: 2.415,
  snapshot: {
    availability: {
      DENL1: {status:'eligible',age_hours:0.7,observation:{value:319,units:'cfs',datum:'native',valid_time_utc:'2026-10-23T12:45:00Z',retrieved_utc:'2026-10-23T13:27:16Z',qc:['P'],source:'USGS NWIS IV',parameter:'discharge',provenance_url:'https://example.test/den'}},
      MAUL1_00065: {status:'eligible',age_hours:0.7,observation:{station:'MAUL1',value:2.42,units:'ft',datum:'gage height',valid_time_utc:'2026-10-23T12:45:00Z',retrieved_utc:'2026-10-23T13:27:16Z',qc:['P'],source:'USGS NWIS IV',parameter:'stage',provenance_url:'https://example.test/maul'}},
      MCHL1: {status:'missing',observation:null},
      MDLL1: {status:'eligible',age_hours:0.7,observation:{value:0.77,units:'ft',datum:'native',valid_time_utc:'2026-10-23T12:45:00Z',retrieved_utc:'2026-10-23T13:27:16Z',qc:['P'],source:'USGS NWIS IV',parameter:'00065',provenance_url:'https://example.test/mdl'}},
      NWCL1: {status:'eligible',age_hours:1.75,observation:{value:1.079,units:'ft',datum:'MLLW',valid_time_utc:'2026-10-23T11:42:00Z',retrieved_utc:'2026-10-23T13:27:17Z',qc:'0,0,0,0',source:'NOAA CO-OPS 8761927',parameter:'water_level',provenance_url:'https://example.test/nwc'}}
    },
    feature_diagnostics:{expected_latest_bin_utc:'2026-10-23T12:00:00Z',mchl1_shadow:{forecast_eligible:false,latest_completed_bin_utc:'2026-10-23T12:00:00Z',features:{mchl1_stage_change_6h_native_ft:-0.04}},stations:{}},
    features:{maul1_change_6h_ft:-0.1275,denl1_log_change_6h:-0.0031,mdll1_stage_change_6h_ft:0.075,nwcl1_wind_u_knots:-4.09,nwcl1_wind_v_knots:1.2,nwcl1_residual_mllw_ft:null}
  }
};

const html = renderCurrentConditions(issue, Date.parse('2026-10-23T17:00:00Z'));
assert.match(html, /MAUL1/);
assert.match(html, /2\.42 ft/);
assert.match(html, /native USGS 00065 gage height/i);
assert.match(html, /NAVD88 elevation unavailable/i);
assert.match(html, /reference line is withheld/i);
assert.match(html, /DENL1/);
assert.match(html, /NWCL1/);
assert.match(html, /MDLL1/);
assert.match(html, /MCHL1/);
assert.match(html, /shadow-only/i);
assert.match(html, /Missing observation · missing/i);
const staleMchl = JSON.parse(JSON.stringify(issue));
staleMchl.snapshot.availability.MCHL1.status = 'eligible';
staleMchl.snapshot.availability.MCHL1.observation = {value:1.25,units:'ft',datum:'HADS native gage height (unverified)',valid_time_utc:'2026-10-23T11:00:00Z',retrieved_utc:'2026-10-23T13:27:16Z',qc:'unverified',source:'Iowa Environmental Mesonet archive of NWS HADS SHEF'};
const staleMchlHtml = renderCurrentConditions(staleMchl, Date.parse('2026-10-23T17:00:00Z'));
assert.match(staleMchlHtml, /Unverified · shadow-only/);
assert.match(staleMchlHtml, /Stale · 6\.0 h old/);
assert.match(html, /indeterminate/i);
assert.match(html, /2026-10-23T12:45:00Z/);
assert.match(html, /USGS NWIS IV/);
assert.match(html, /stale/i);
const unverified = JSON.parse(JSON.stringify(issue));
unverified.snapshot.availability.MAUL1_00065.observation.parameter = '00065';
unverified.snapshot.availability.MAUL1_00065.observation.datum = 'NAVD88';
assert.match(renderCurrentConditions(unverified, Date.parse('2026-10-23T14:00:00Z')), /reference line is withheld/i);
assert.doesNotMatch(renderCurrentConditions(unverified, Date.parse('2026-10-23T14:00:00Z')), /2\.42 ft/);
const badQcNative = JSON.parse(JSON.stringify(issue));
badQcNative.snapshot.availability.MAUL1_00065.observation.qc = ['ice'];
assert.doesNotMatch(renderCurrentConditions(badQcNative, Date.parse('2026-10-23T14:00:00Z')), /2\.42 ft/);
const direct = JSON.parse(JSON.stringify(issue));
direct.snapshot.availability.MAUL1_00065.observation.parameter = '63160';
direct.snapshot.availability.MAUL1_00065.observation.datum = 'NAVD88';
assert.match(renderCurrentConditions(direct, Date.parse('2026-10-23T14:00:00Z')), /reference line is withheld/i);
direct.snapshot.availability.MAUL1_63160 = {status:'eligible',observation:{station:'MAUL1',parameter:'elevation',parameter_code:'63160',datum:'NAVD88',units:'ft',value:4.25,valid_time_utc:'2026-10-23T12:45:00Z',retrieved_utc:'2026-10-23T13:27:16Z',qc:['P'],source:'USGS NWIS IV',provenance_url:'https://example.test/maul-navd'}};
assert.match(renderCurrentConditions(direct, Date.parse('2026-10-23T14:00:00Z')), /Local 4\.0 ft NAVD88 threshold difference: 0\.25 ft/);
assert.match(renderCurrentConditions(direct, Date.parse('2026-10-23T17:00:00Z')), /NAVD88 elevation unavailable/i);
assert.match(renderCurrentConditions(null, Date.now()), /No authentic prospective/i);
assert.match(renderCurrentConditions({...issue, mode:'simulation'}, Date.now()), /No authentic prospective/i);

const futureIssue = JSON.parse(JSON.stringify(issue));
futureIssue.actual_issue_time_utc = '2026-10-23T18:00:00Z';
const futureIssueHtml = renderCurrentConditions(futureIssue, Date.parse('2026-10-23T17:00:00Z'));
assert.match(futureIssueHtml, /Issue timestamp is in the future/);
assert.doesNotMatch(futureIssueHtml, /status-fresh">Authentic issue/);
const malformedIssue = JSON.parse(JSON.stringify(issue));
malformedIssue.actual_issue_time_utc = 'not-a-time';
assert.match(renderCurrentConditions(malformedIssue, Date.parse('2026-10-23T17:00:00Z')), /Issue time unavailable/);
const futureObservation = JSON.parse(JSON.stringify(issue));
futureObservation.snapshot.availability.MAUL1_00065.observation.valid_time_utc = '2026-10-23T17:01:00Z';
const futureObservationHtml = renderCurrentConditions(futureObservation, Date.parse('2026-10-23T17:00:00Z'));
assert.doesNotMatch(futureObservationHtml, /2\.42 ft/);
assert.match(futureObservationHtml, /Missing observation · ineligible native 00065 observation/);
const malformedObservation = JSON.parse(JSON.stringify(issue));
malformedObservation.snapshot.availability.MAUL1_00065.observation.value = 'not-a-stage';
assert.doesNotMatch(renderCurrentConditions(malformedObservation, Date.parse('2026-10-23T14:00:00Z')), /2\.42 ft/);
const futureElevation = JSON.parse(JSON.stringify(direct));
futureElevation.snapshot.availability.MAUL1_63160.observation.valid_time_utc = '2026-10-23T17:01:00Z';
futureElevation.snapshot.availability.MAUL1_63160.observation.retrieved_utc = '2026-10-23T17:02:00Z';
assert.match(renderCurrentConditions(futureElevation, Date.parse('2026-10-23T17:00:00Z')), /NAVD88 elevation unavailable/);
const inconsistentElevation = JSON.parse(JSON.stringify(direct));
inconsistentElevation.snapshot.availability.MAUL1_63160.observation.retrieved_utc = '2026-10-23T12:30:00Z';
assert.match(renderCurrentConditions(inconsistentElevation, Date.parse('2026-10-23T14:00:00Z')), /NAVD88 elevation unavailable/);
const badQcElevation = JSON.parse(JSON.stringify(direct));
badQcElevation.snapshot.availability.MAUL1_63160.observation.qc = ['ice'];
assert.match(renderCurrentConditions(badQcElevation, Date.parse('2026-10-23T14:00:00Z')), /NAVD88 elevation unavailable/);


const futureIssueElevation = JSON.parse(JSON.stringify(direct));
futureIssueElevation.actual_issue_time_utc = '2026-10-23T18:00:00Z';
assert.match(renderCurrentConditions(futureIssueElevation, Date.parse('2026-10-23T14:00:00Z')), /NAVD88 elevation unavailable/);

console.log('Research dashboard rendering safeguards passed');

async function testArchiveHydration() {
  const compact = JSON.parse(fs.readFileSync('site/data/prospective/latest.json', 'utf8'));
  const entries = JSON.parse(fs.readFileSync('site/data/prospective/history/index.json', 'utf8'));
  const entry = entries.find(item => item.issuance_id === compact.issuance_id);
  assert.ok(entry, 'compact latest issue is present in the archive index');
  const fullPath = `data/prospective/history/${entry.forecast_file}`;
  const fullIssue = JSON.parse(fs.readFileSync(`site/data/prospective/archive/issues/${compact.issuance_id}.json`, 'utf8'));
  const chronologyEntry = entries.find(item => item.actual_issue_time_utc === '2026-10-24T05:54:08Z');
  assert.ok(chronologyEntry, 'the deliberately unequal Oct 24 issuance/anchor example remains archived');
  const chronologyIssue = JSON.parse(fs.readFileSync(`site/data/prospective/archive/issues/${chronologyEntry.issuance_id}.json`, 'utf8'));
  const fetcher = async path => ({
    ok: true,
    json: async () => path === 'data/prospective/history/index.json' ? entries : fullIssue
  });
  const hydrated = await hydrateLatestIssue(compact, fetcher);
  assert.equal(hydrated.issuance_id, compact.issuance_id);
  assert.equal(hydrated.actual_issue_time_utc, compact.actual_issue_time_utc);
  assert.equal(hydrated.snapshot.availability.MAUL1_00065.observation.value, fullIssue.snapshot.availability.MAUL1_00065.observation.value);
  const chartTraces = forecast.buildTraces(chronologyIssue, Date.parse('2026-10-24T06:00:00Z'));
  const chartObservation = chartTraces.find(trace => trace.name === 'Latest observation · USGS 00065');
  const chartAnchor = chartTraces.find(trace => trace.name === 'Model anchor · native stage');
  assert.equal(chartObservation.y[0], 2.68);
  assert.equal(chartObservation.x[0], '2026-10-24T04:45:00Z');
  assert.equal(chartAnchor.y[0], 2.7375);
  assert.equal(chartAnchor.x[0], '2026-10-24T05:00:00Z');
  assert.notEqual(chartObservation.y[0], chartAnchor.y[0], 'observation and forecast anchor retain their distinct archived values');
  const coastalTrace=chartTraces.find(trace=>trace.name==='Phase 5A · coastal predictors');
  assert.deepEqual(coastalTrace.x.slice(1), ['2026-10-24T11:00:00Z','2026-10-24T17:00:00Z','2026-10-25T05:00:00Z']);
  assert.ok(Math.abs(coastalTrace.customdata[1][2]-5.097778)<1e-6, 'issuance-relative lead remains hover metadata while valid UTC determines x position');
  const fetchedPaths = [];
  const loaded = await loadLatestIssue(async path => {
    fetchedPaths.push(path);
    return {ok:true,json:async()=>path === 'data/prospective/latest.json' ? compact : path === 'data/prospective/history/index.json' ? entries : fullIssue};
  });
  assert.equal(loaded.latest.issuance_id, compact.issuance_id);
  assert.equal(loaded.record.issuance_id, compact.issuance_id);
  assert.equal(loaded.record.snapshot.availability.MAUL1_00065.observation.value, fullIssue.snapshot.availability.MAUL1_00065.observation.value);
  assert.deepEqual(fetchedPaths, ['data/prospective/latest.json','data/prospective/history/index.json',`data/prospective/history/${entry.forecast_file}`]);
  const guidance = forecast.renderGuidance(chronologyIssue, Date.parse('2026-10-24T06:00:00Z'));
  assert.match(guidance, /Latest archived MAUL1 observation · native USGS 00065/);
  assert.match(guidance, /2\.68 ft · fresh/);
  assert.match(guidance, /\+0\.02 ft to \+0\.12 ft/);
  assert.match(guidance, /Persistence baseline/);
  assert.match(guidance, /Rising · \+0\.17 ft/);
  assert.match(guidance, /imputed feature/i);
  assert.match(guidance, /calibration not established here/);
  assert.match(guidance, /MCHL1 is unverified/i);
  assert.match(guidance, /Model skill during independent meaningful rises has not been established/);

  const mismatched = await hydrateLatestIssue(compact, async path => ({
    ok: true,
    json: async () => path.endsWith('index.json') ? entries : {...fullIssue, issuance_id: 'wrong-issue'}
  }));
  assert.equal(mismatched, null, 'a full issue with the wrong issuance ID is rejected');
  const wrongArchivePath = await hydrateLatestIssue(compact, async path => ({
    ok: true,
    json: async () => path.endsWith('index.json') ? entries.map(item => item.issuance_id === compact.issuance_id ? {...item, forecast_file:'../archive/issues/other.json'} : item) : fullIssue
  }));
  assert.equal(wrongArchivePath, null, 'an index path that does not match the issue ID is rejected');
  const unavailable = await hydrateLatestIssue(compact, async () => ({ok:false,json:async()=>null}));
  assert.equal(unavailable, null, 'missing archive data is not replaced with the compact record');
  const malformed = await hydrateLatestIssue(compact, async path => ({
    ok: true,
    json: async () => path.endsWith('index.json') ? entries : ({...fullIssue, actual_issue_time_utc:'invalid'})
  }));
  assert.equal(malformed, null, 'malformed issue identity is rejected');
  assert.ok(fullPath.endsWith(`${compact.issuance_id}.json`));

  const performance = JSON.parse(fs.readFileSync('site/data/prospective/performance.json', 'utf8'));
  const verificationOverview = forecast.renderVerificationOverview(performance);
  for (const horizon of [6,12,24]) assert.match(verificationOverview, new RegExp(`<td>${performance.model_horizon_metrics[`persistence:${horizon}h`].n}<\\/td>`));
  const eventCount=performance.model_horizon_metrics['phase5a_maul1_only:24h']?.qualifying_24h_events?.event_count ?? 0;
  assert.ok(verificationOverview.includes(`${eventCount} qualifying 24-hour rises of at least 0.50 ft`));
  assert.match(verificationOverview, /overlapping forecast\/observation comparisons, not independent events/i);
  const cycleOverview = forecast.renderArchiveCycleHealth(entries, Date.parse('2026-10-24T06:00:00Z'));
  assert.match(cycleOverview, /5\.2 h earlier/);
}

testArchiveHydration().then(() => console.log('Immutable authentic issue hydration checks passed')).catch(error => {
  console.error(error);
  process.exitCode = 1;
});
