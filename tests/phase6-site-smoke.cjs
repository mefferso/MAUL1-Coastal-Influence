const fs = require('fs');
const html = fs.readFileSync('site/index.html', 'utf8');
const js = fs.readFileSync('site/phase6.js', 'utf8');
for (const value of ['Prospective Forecast Verification','phase6-content','research-only']) {
  if (!html.toLowerCase().includes(value.toLowerCase()) && !js.toLowerCase().includes(value.toLowerCase())) throw new Error(`Missing Phase 6 dashboard element: ${value}`);
}
for (const value of ['latest.json','history/index.json','performance.json','actual_issue_time_utc','phase5a_coastal','phase5b_full_multivariable','No authentic prospective issuance','interval_lower_ft','verification_files','probability_of_detection']) if (!js.includes(value)) throw new Error(`Missing archived forecast rendering: ${value}`);
console.log('Phase 6 site smoke checks passed');
