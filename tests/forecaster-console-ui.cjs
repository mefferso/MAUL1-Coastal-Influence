const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const html = read('site/index.html');
const css = read('site/style.css');
const dashboardCss = read('site/research-dashboard.css');
const app = read('site/app.js');
const forecast = read('site/forecast-view.js');

assert.match(html, /Design A — Forecaster Console \/ Research-Only Preview/);
assert.match(html, /RESEARCH\s*\/\s*SHADOW EVALUATION\s*\/\s*NOT OPERATIONAL/);
assert.match(html, /id="current-forecast-view"[\s\S]*?id="forecast-verification-view"[\s\S]*?id="historical-research-view"[\s\S]*?id="model-lab-view"/);
assert.match(html, /id="console-network-map"/);
assert.match(html, /id="console-network-list"/);
assert.match(html, /id="forecast-chart"/);
assert.match(html, /chart-theme\.js/);
assert.match(html, /name="data-snapshot-sha" content="e236d8946fe7acbfb764f1ba60960f9bb806881e"/);
assert.match(html, /name="data-snapshot-time" content="2026-10-26T15:03:15Z"/);
assert.doesNotMatch(html, /(?:src|href)="\/(?!\/)/, 'frontend resources must remain relative for project Pages');
assert.match(html, /USGS 00065/);
assert.match(html, /63160/);
assert.match(html, /MCHL1[\s\S]{0,120}shadow.only/i);
assert.match(html, /RESEARCH \/ SHADOW EVALUATION \/ NOT OPERATIONAL/);
assert.match(css, /--station-denl1:/);
assert.match(css, /--station-nwcl1:/);
assert.match(css, /--station-mdll1:/);
assert.match(css, /--station-mchl1:/);
assert.match(css, /--station-maul1:/);
assert.match(css, /--model-persistence:/);
assert.match(css, /--focus-ring:/);
assert.match(css, /prefers-reduced-motion/);
assert.match(dashboardCss, /var\(--color-/);
assert.match(app, /30\.464079,-90\.99038/);
assert.match(app, /30\.027222,-90\.113335/);
assert.match(app, /30\.1996389,-90\.12275/);
assert.match(app, /30\.283333,-90\.396111/);
assert.match(app, /30\.30769444,-90\.6087222/);
assert.match(forecast, /forecastDatumIsNative/);
assert.match(forecast, /actual_issue_time_utc/);
assert.match(forecast, /fixed presentation label is not a skill ranking or endorsement/);
assert.match(forecast, /no substitute selected/);
assert.match(app, /'MAUL1',30\.30769444,-90\.6087222/);

for (const match of html.matchAll(/(?:src|href)="([^"]+\.(?:css|js))"/g)) {
  const asset = match[1];
  if (/^https?:\/\//i.test(asset)) continue;
  assert.equal(asset.startsWith('/'), false, `${asset} must resolve beneath the preview Pages path`);
  assert.ok(new URL(asset, 'https://mefferso.github.io/MAUL1-Preview-A/').pathname.startsWith('/MAUL1-Preview-A/'));
}

const chartTheme = require(path.join(root, 'site/chart-theme.js'));
const networkMap = require(path.join(root, 'site/network-map.js'));
assert.equal(chartTheme.modelColors.phase5a_maul1_only, chartTheme.colors.model.phase5a_maul1_only);
assert.equal(chartTheme.stationColors.MAUL1, chartTheme.colors.station.MAUL1);
assert.equal(chartTheme.stationColors.MCHL1, chartTheme.colors.station.MCHL1);
assert.equal(chartTheme.layout('Forecast').showlegend, true);
assert.equal(chartTheme.chartConfig({}).responsive, true);
assert.deepEqual(networkMap.stations.map(({id,lat,lon})=>[id,lat,lon]), [
  ['DENL1',30.464079,-90.99038], ['NWCL1',30.027222,-90.113335],
  ['MDLL1',30.1996389,-90.12275], ['MCHL1',30.283333,-90.396111],
  ['MAUL1',30.30769444,-90.6087222]
]);
assert.equal(networkMap.stations.find(station=>station.id==='MCHL1').shadow, true);
assert.match(networkMap.stations.find(station=>station.id==='MCHL1').detail, /forecast-ineligible/);

console.log('Forecaster Console UI regression checks passed');
