const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const forecast = require('../site/forecast-view.js');

const html = fs.readFileSync('site/index.html', 'utf8');
const baseCss = fs.readFileSync('site/style.css', 'utf8');
const researchCss = fs.readFileSync('site/research-dashboard.css', 'utf8');
const phase6 = fs.readFileSync('site/phase6.js', 'utf8');

for (const view of ['current-forecast-view', 'forecast-verification-view', 'historical-research-view', 'model-lab-view']) {
  assert.match(html, new RegExp(`id="${view}"`), `retain ${view}`);
}
assert.match(html, /Research \/ Shadow Evaluation \/ Not Operational/);
assert.match(html, /native USGS 00065/);
assert.match(html, /forecast-chart-description/);
assert.match(html, /id="forecast-chart"[^>]*role="region"/);
assert.match(html, /Plotly time-series/);

for (const token of ['--color-ink', '--color-ocean', '--color-surface', '--space-4', '--radius-card', '--focus-ring']) {
  assert.ok(baseCss.includes(token), `shared design token ${token}`);
}
assert.match(baseCss, /@media\s*\(max-width:\s*\d+px\)/, 'responsive rules remain in the shared sheet');
assert.match(researchCss, /@media\s*\(max-width:\s*600px\)/, 'research cards have a narrow mobile layout');
assert.match(baseCss, /:focus-visible/);

const now = Date.parse('2026-10-26T15:00:00Z');
const issueTime = '2026-10-26T14:50:00Z';
const anchorTime = '2026-10-26T14:45:00Z';
const makeForecast = (value, change) => ({
  valid_time_utc: '2026-10-26T20:00:00Z',
  effective_lead_hours: 5.17,
  datum: 'USGS 00065 native gage height',
  models: {
    persistence: { status: 'issued', predicted_stage_native_ft: 2.4, predicted_change_ft: 0 },
    phase5a_maul1_only: { status: 'issued', predicted_stage_native_ft: value, predicted_change_ft: change, imputed_feature_count: 0 },
    phase5a_coastal: { status: 'withheld' },
    phase5b_coastal_tidal: { status: 'abstained' },
    phase5b_full_multivariable: { status: 'unavailable' }
  }
});
const issue = {
  mode: 'authentic', actual_issue_time_utc: issueTime, model_anchor_time_utc: anchorTime,
  latest_maul1_native_stage_ft: 2.4,
  datum: 'USGS 00065 native gage height',
  snapshot: {
    features: { maul1_change_6h_ft: 0.12 },
    availability: { MAUL1_00065: { status: 'eligible', age_hours: 0.25, observation: {
      station: 'MAUL1', parameter: 'stage', datum: 'gage height', units: 'ft', value: 2.38,
      valid_time_utc: '2026-10-26T14:40:00Z', retrieved_utc: issueTime,
      source: 'USGS NWIS IV', qc: ['P']
    } } }
  },
  forecasts: { '6': makeForecast(2.56, 0.16), '12': { valid_time_utc: '2026-10-27T02:00:00Z', datum: 'USGS 00065 native gage height', models: {} }, '24': { valid_time_utc: '2026-10-27T14:00:00Z', datum: 'USGS 00065 native gage height', models: {} } }
};

const rendered = forecast.renderGuidance(issue, now);
for (const expected of [
  'forecast-current-value', 'forecast-observation-fact', 'forecast-tendency-fact',
  'MAUL1 · native USGS 00065 gage height', '2.40 ft', '2.38 ft', 'Rising · +0.12 ft',
  '6-hour guidance', '12-hour guidance', '24-hour guidance',
  'Compare individual model guidance', 'Phase 5A · MAUL1 only', 'withheld', 'abstained', 'unavailable',
  'not a calibrated interval or probability'
]) assert.ok(rendered.includes(expected), `forecast presentation includes ${expected}`);
assert.match(rendered, /<details>/, 'model detail remains progressively disclosed');

const traces = forecast.buildTraces(issue, now);
assert.ok(traces.every(trace => trace.y.every(Number.isFinite)), 'forecast chart has numeric stage values only');
assert.equal(traces.find(trace => trace.name === 'Model anchor · native stage').y[0], 2.4);
assert.equal(traces.find(trace => trace.name === 'Phase 5A · MAUL1 only').y.at(-1), 2.56);
assert.equal(traces.find(trace => trace.name === 'Latest observation · USGS 00065').y[0], 2.38);
assert.ok(!traces.some(trace => /63160|NAVD88/i.test(trace.name)), 'direct NAVD88 data is not mixed into native stage traces');

const stale = structuredClone(issue);
stale.snapshot.availability.MAUL1_00065.observation.valid_time_utc = '2026-10-26T10:00:00Z';
assert.match(forecast.renderGuidance(stale, now), /Stale at view/);
assert.equal(forecast.buildTraces(stale, now).some(trace => trace.name === 'Latest observation · USGS 00065'), false);
const missing = structuredClone(issue);
missing.snapshot.availability.MAUL1_00065.observation = null;
assert.match(forecast.renderGuidance(missing, now), /Unavailable or ineligible/);
assert.equal(forecast.buildTraces(missing, now).some(trace => trace.name === 'Latest observation · USGS 00065'), false);

assert.match(phase6, /displayModeBar\s*:\s*true/);
assert.match(phase6, /scrollZoom\s*:\s*true/);
assert.match(phase6, /hovermode\s*:\s*['"]x unified['"]/);

const captured = {};
const nodes = new Map();
const node = id => {
  if (!nodes.has(id)) nodes.set(id, { id, innerHTML: '', textContent: '', clientWidth: 900, addEventListener() {}, set disabled(value) { this._disabled = value; } });
  return nodes.get(id);
};
const chartIssue = structuredClone(issue);
chartIssue.issuance_id = 'phase6-18-chart-fixture';
chartIssue.actual_issue_time_utc = new Date(Date.now() - 10 * 60000).toISOString();
chartIssue.model_anchor_time_utc = new Date(Date.now() - 15 * 60000).toISOString();
chartIssue.snapshot.availability.MAUL1_00065.observation.valid_time_utc = new Date(Date.now() - 20 * 60000).toISOString();
chartIssue.snapshot.availability.MAUL1_00065.observation.retrieved_utc = chartIssue.actual_issue_time_utc;
chartIssue.forecasts['6'].valid_time_utc = new Date(Date.now() + 6 * 3600000).toISOString();
chartIssue.forecasts['12'].valid_time_utc = new Date(Date.now() + 12 * 3600000).toISOString();
chartIssue.forecasts['24'].valid_time_utc = new Date(Date.now() + 24 * 3600000).toISOString();
const mockWindow = {
  MAUL1ResearchDashboard: { loadLatestIssue: async () => ({ latest: chartIssue, record: chartIssue }) },
  MAUL1ForecastView: {
    ...forecast,
    renderArchiveCycleHealth: () => 'fixture archive status',
    renderVerificationOverview: () => ''
  },
  Plotly: { react: (...args) => { captured.plotly = args; } }
};
const mockFetch = async () => ({ ok: true, json: async () => [] });
const context = vm.createContext({ window: mockWindow, document: { getElementById: node }, fetch: mockFetch, Date, Promise, console });
vm.runInContext(phase6, context);
(async () => {
  for (let i = 0; i < 100 && !captured.plotly; i++) await new Promise(resolve => setTimeout(resolve, 5));
  assert.ok(captured.plotly, 'Phase 6 renders the Plotly chart for a valid authentic issue');
  const [, chartTraces, chartLayout, chartConfig] = captured.plotly;
  assert.equal(chartTraces.find(trace => trace.name === 'Model anchor · native stage').y[0], 2.4);
  assert.equal(chartTraces.find(trace => trace.name === 'Phase 5A · MAUL1 only').y.at(-1), 2.56);
  assert.equal(chartTraces.find(trace => trace.name === 'Latest observation · USGS 00065').y[0], 2.38);
  assert.equal(chartLayout.xaxis.title.text, 'Valid time · UTC');
  assert.equal(chartLayout.yaxis.title.text, 'MAUL1 native stage · ft');
  assert.equal(chartLayout.hovermode, 'x unified');
  assert.equal(chartConfig.displayModeBar, true);
  assert.equal(chartConfig.scrollZoom, true);
  console.log('Phase 6.18 UI regression checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
