const assert = require('node:assert/strict');
const { renderCurrentConditions } = require('../site/research-dashboard.js');

const issue = {
  mode: 'authentic', actual_issue_time_utc: '2026-10-23T13:27:17Z',
  latest_maul1_native_stage_ft: 2.415,
  snapshot: {
    availability: {
      DENL1: {status:'eligible',age_hours:0.7,observation:{value:319,units:'cfs',datum:'native',valid_time_utc:'2026-10-23T12:45:00Z',retrieved_utc:'2026-10-23T13:27:16Z',qc:['P'],source:'USGS NWIS IV',parameter:'discharge',provenance_url:'https://example.test/den'}},
      MAUL1_00065: {status:'eligible',age_hours:0.7,observation:{value:2.42,units:'ft',datum:'gage height',valid_time_utc:'2026-10-23T12:45:00Z',retrieved_utc:'2026-10-23T13:27:16Z',qc:['P'],source:'USGS NWIS IV',parameter:'00065',provenance_url:'https://example.test/maul'}},
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
assert.match(futureObservationHtml, /Future timestamp · freshness unknown/);
const malformedObservation = JSON.parse(JSON.stringify(issue));
malformedObservation.snapshot.availability.MAUL1_00065.observation.value = 'not-a-stage';
assert.match(renderCurrentConditions(malformedObservation, Date.parse('2026-10-23T14:00:00Z')), /Invalid observation value/);
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
