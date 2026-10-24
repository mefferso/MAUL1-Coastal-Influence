'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const html = fs.readFileSync('site/index.html', 'utf8');
const js = fs.readFileSync('site/model-lab.js', 'utf8');

for (const [tab, panel] of [
  ['tab-current', 'current-forecast-view'],
  ['tab-verification', 'forecast-verification-view'],
  ['tab-history', 'historical-research-view'],
  ['tab-model-lab', 'model-lab-view']
]) {
  assert.match(html, new RegExp(`id="${tab}"[^>]*aria-controls="${panel}"`));
  assert.match(html, new RegExp(`id="${panel}"[^>]*aria-labelledby="${tab}"`));
}
for (const id of ['forecast-guidance', 'phase6-content', 'performance-explorer', 'historical-research-view']) {
  assert.match(html, new RegExp(`id="${id}"`), `${id} remains in the page`);
}
assert.match(html, /id="model-lab-annual"/);
assert.match(html, /Retrospective \/ Development Evidence/);
assert.match(html, /2023 onward benchmark has already been inspected/);
assert.match(html, /model-lab.js/);
assert.match(js, /data\/research\/model-lab\.json/);
assert.match(js, /mode:'markers'/);
assert.match(js, /connectgaps:false/);
assert.match(js, /Issued: %\{customdata\[0\]\}/);
assert.match(js, /maul1:viewchange/);
assert.doesNotMatch(js, /phase6\.js|prospective\/attempts|prospective\/verification/);
const report = JSON.parse(fs.readFileSync('site/data/research/model-lab.json', 'utf8'));
assert.equal(report.schema, 'maul1.model-lab.report.v1');
for (const horizon of ['6','12','24']) {
  assert.ok(report.horizons[horizon].metrics.bounded_damped_trend_ft.n > 0);
  assert.ok(report.horizons[horizon].annual_and_seasonal['year:2023']);
  assert.ok(report.horizons[horizon].regimes['quiet or falling target']);
}
assert.equal(report.phase6_qualifying_rise_groups_24h.bounded_damped_trend_ft.definition,
  'outcome-defined 24h rises of at least 0.50 ft; targets within 24h grouped');
assert.ok(report.case_studies.every(item => item.observations.length > 0 && item.forecasts_by_horizon['24'].length > 0));
const navigation = require('../site/navigation.js');
const modelLab = require('../site/model-lab.js');
assert.equal(modelLab.fmt(null), 'Unavailable');
assert.equal(modelLab.fmt(undefined), 'Unavailable');
assert.equal(modelLab.fmt(0), '0.000');
const panelIds = ['current-forecast-view','forecast-verification-view','historical-research-view','model-lab-view'];
const fakePanels = new Map(panelIds.map(id=>[id,{id,hidden:true,attributes:{},setAttribute(k,v){this.attributes[k]=v;}}]));
const fakeTabs = panelIds.map((id,i)=>({id:`tab-${i}`,attributes:{},listeners:{},getAttribute:()=>panelIds[i],setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,fn){this.listeners[k]=fn;},focus(){this.focused=true;}}));
const fakeWindow={location:{hash:'#current-forecast-view'},history:{replaceState(_a,_b,hash){this.hash=hash;}},listeners:{},addEventListener(k,fn){this.listeners[k]=fn;},dispatchEvent(){}};
navigation.initNavigation({querySelectorAll:()=>fakeTabs,getElementById:id=>fakePanels.get(id)},fakeWindow);
fakeTabs[3].listeners.click();
assert.equal(fakeTabs[3].attributes['aria-selected'],'true');
assert.equal(fakePanels.get('model-lab-view').hidden,false);
assert.equal(fakePanels.get('current-forecast-view').hidden,true);
assert.equal(fakePanels.get('historical-research-view').hidden,true);
console.log('Model Lab tab contract and scientific separation checks passed.');
