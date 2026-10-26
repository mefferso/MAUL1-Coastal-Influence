(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) api.init(root.document, root);
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const COLORS = {
    persistence_ft: '#727b84', maul1_only_ft: '#287f8e', maul1_plus_coastal_ft: '#8064a2',
    maul1_coastal_tidal: '#c17b16', full_multivariable: '#bd4c4c', bounded_damped_trend_ft: '#39916e'
  };
  const FIELDS = ['persistence_ft', 'maul1_only_ft', 'maul1_plus_coastal_ft', 'maul1_coastal_tidal', 'full_multivariable', 'bounded_damped_trend_ft'];
  const LABELS = {
    persistence_ft: 'Persistence', maul1_only_ft: 'Phase 5A MAUL1-only',
    maul1_plus_coastal_ft: 'Phase 5A coastal', maul1_coastal_tidal: 'Phase 5B coastal + tidal',
    full_multivariable: 'Phase 5B full multivariable', bounded_damped_trend_ft: 'Damped-trend challenger'
  };
  function escape(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }
  function fmt(value, digits = 3) { return value == null || value === '' || !Number.isFinite(Number(value)) ? 'Unavailable' : Number(value).toFixed(digits); }
  function cell(value) { return value == null ? '—' : escape(value); }
  function metricTable(table, includeCI, uncertainty) {
    const header = '<thead><tr><th scope="col">Model</th><th scope="col">Eligible</th><th scope="col">Scored n</th><th scope="col">Abstentions</th><th scope="col">MAE (ft)</th><th scope="col">RMSE (ft)</th><th scope="col">Bias (ft)</th><th scope="col">Skill vs persistence</th>' + (includeCI ? '<th scope="col">MAE improvement vs persistence 95% block interval (ft)</th><th scope="col">Challenger improvement vs MAUL1-only 95% block interval (ft)</th>' : '') + '</tr></thead>';
    const body = FIELDS.map(name => {
      const row = table[name] || {};
      const interval = uncertainty && uncertainty[name] && uncertainty[name].improvement_ft_ci95;
      const challengerInterval = uncertainty && uncertainty.bounded_damped_trend_ft && uncertainty.bounded_damped_trend_ft.vs_maul1_only && uncertainty.bounded_damped_trend_ft.vs_maul1_only.improvement_ft_ci95;
      const skill = row.skill_vs_persistence == null ? 'Unavailable' : `${fmt(row.skill_vs_persistence * 100, 1)}%`;
      const ci = interval && interval[0] != null ? `${fmt(interval[0])} to ${fmt(interval[1])}` : 'Unavailable';
      const challengerCi = challengerInterval && challengerInterval[0] != null ? `${fmt(challengerInterval[0])} to ${fmt(challengerInterval[1])}` : 'Unavailable';
      return `<tr><th scope="row"><span class="model-swatch" style="--model-color:${COLORS[name]}"></span>${escape(LABELS[name] || row.label || name)}</th><td>${cell(row.eligible_issue_target_rows)}</td><td>${cell(row.n)}</td><td>${cell(row.abstention_n)}</td><td>${fmt(row.mae_ft)}</td><td>${fmt(row.rmse_ft)}</td><td>${fmt(row.bias_ft)}</td><td>${skill}</td>${includeCI ? `<td>${ci}</td><td>${name==='bounded_damped_trend_ft'?challengerCi:'—'}</td>` : ''}</tr>`;
    }).join('');
    return header + `<tbody>${body}</tbody>`;
  }
  function init(document, window) {
    const $ = id => document.getElementById(id);
    const panel = $('model-lab-view');
    if (!panel) return null;
    let report = null;
    let initialized = false;
    const setStatus = text => { if ($('model-lab-status')) $('model-lab-status').textContent = text; };
    const render = () => {
      if (!report) return;
      const horizon = $('model-lab-horizon').value;
      const regime = $('model-lab-regime').value;
      const data = report.horizons[horizon];
      const regimeData = data.regimes[regime];
      $('model-lab-metrics').innerHTML = metricTable(regimeData.models, regime === 'all paired cases', data.improvement_vs_persistence_bootstrap);
      const annualMethods = ['persistence_ft','maul1_only_ft','maul1_plus_coastal_ft','maul1_coastal_tidal','full_multivariable','bounded_damped_trend_ft'];
      $('model-lab-annual').innerHTML = '<thead><tr><th scope="col">Year / season</th><th scope="col">Scored n</th>' + annualMethods.map(name=>`<th scope="col">${escape(LABELS[name])} MAE (ft)</th>`).join('') + '</tr></thead><tbody>' + Object.entries(data.annual_and_seasonal).map(([period,models])=>`<tr><th scope="row">${escape(period.replace(':',' · '))}</th><td>${cell(models.persistence_ft.n)}</td>${annualMethods.map(name=>`<td>${fmt(models[name].mae_ft)}</td>`).join('')}</tr>`).join('') + '</tbody>';
      const ablations = report.predictor_ablations[horizon].maul1_additive_value_and_degradation;
      $('model-lab-ablations').innerHTML = '<thead><tr><th scope="col">Predictor family / model</th><th scope="col">n</th><th scope="col">MAE (ft)</th><th scope="col">Δ MAE vs MAUL1-only (ft)</th><th scope="col">Δ MAE vs persistence (ft)</th><th scope="col">RMSE (ft)</th><th scope="col">Bias (ft)</th><th scope="col">Skill vs persistence</th></tr></thead><tbody>' + Object.entries(ablations).map(([name, row]) => `<tr><th scope="row">${escape(LABELS[name] || name.replaceAll('_',' '))}${name === 'maul1_astro_retrospective' ? ' †' : ''}</th><td>${cell(row.n)}</td><td>${fmt(row.mae_ft)}</td><td>${fmt(row.mae_delta_vs_maul1_only_ft)}</td><td>${fmt(row.mae_delta_vs_persistence_ft)}</td><td>${fmt(row.rmse_ft)}</td><td>${fmt(row.bias_ft)}</td><td>${row.skill_vs_persistence == null ? 'Unavailable' : `${fmt(row.skill_vs_persistence*100,1)}%`}</td></tr>`).join('') + '</tbody>';
      if (horizon === '24') {
        const diag = data.underforecast_and_false_alarm;
        const grouped = FIELDS.map(name => `${escape(LABELS[name])}: ${data.event_groups[name].event_count}`).join(' · ');
        const phase6 = report.phase6_qualifying_rise_groups_24h;
        const eventRows = FIELDS.map(name => { const r=phase6[name]; const computed=r.status==='computed'; return `<tr><th scope="row">${escape(LABELS[name])}</th><td>${r.event_count}</td><td>${computed?`${r.detected_events} detected / ${r.missed_events} missed`:'Skill withheld (<5 independent events)'}</td><td>${computed&&r.detection_rate!=null?`${fmt(r.detection_rate*100,1)}%`:'Unavailable'}</td><td>${computed?fmt(r.median_lead_to_first_qualifying_verification_target_hours):'Unavailable'}</td></tr>`; }).join('');
        $('model-lab-events').innerHTML = '<div class="table-scroll"><table class="model-lab-table"><thead><tr><th scope="col">Model</th><th scope="col">Paired windows</th><th scope="col">Hit windows</th><th scope="col">False alarm windows</th><th scope="col">Missed rise windows</th><th scope="col">False alert clusters</th></tr></thead><tbody>' + FIELDS.map(name => { const r=diag[name]; return `<tr><th scope="row">${escape(r.label)}</th><td>${r.paired_target_windows_n}</td><td>${r.true_positive_target_windows}</td><td>${r.false_positive_target_windows}</td><td>${r.missed_rise_target_windows}</td><td>${r.false_alert_episode_clusters}</td></tr>`; }).join('') + '</tbody></table></div><p class="small"><strong>Phase 3B independent response-event groups:</strong> ${grouped}. Hourly rows within a group are correlated.</p><h4>Phase 6 qualifying 24-hour rises (≥0.50 ft; target-time groups, independence unproven)</h4><div class="table-scroll"><table class="model-lab-table"><thead><tr><th scope="col">Model</th><th scope="col">Grouped rises</th><th scope="col">Detection</th><th scope="col">Detected fraction</th><th scope="col">Median lead to first qualifying verification target (h)</th></tr></thead><tbody>' + eventRows + '</tbody></table></div><p class="small">Targets within 24 hours are grouped, but the groups are not established independent physical events. Lead is relative to the first qualifying verification target, not physical rise onset. Event skill remains withheld when fewer than five qualifying groups are available.</p>';
      } else {
        $('model-lab-events').innerHTML = '<p>Rise-detection and false-alert analysis is defined at the 24-hour horizon. Change the horizon to 24 hours to view it.</p>';
      }
      const missing = data.issue_feature_missingness;
      $('model-lab-missingness').innerHTML = '<div class="table-scroll"><table class="model-lab-table"><thead><tr><th scope="col">Issue-time feature</th><th scope="col">Available</th><th scope="col">Missing</th><th scope="col">Missing %</th></tr></thead><tbody>' + Object.entries(missing).map(([name, r]) => `<tr><th scope="row">${escape(name.replaceAll('_',' '))}</th><td>${r.available_n.toLocaleString()}</td><td>${r.missing_n.toLocaleString()}</td><td>${fmt(r.missing_fraction*100,1)}%</td></tr>`).join('') + '</tbody></table></div>';
      const trajectories = data.trajectory_diagnostics;
      $('model-lab-trajectories').innerHTML = '<thead><tr><th scope="col">Model</th><th scope="col">Direction accuracy</th><th scope="col">Rising cases</th><th scope="col">Underforecast fraction</th><th scope="col">Threshold timing cases</th><th scope="col">Mean timing error (h)</th><th scope="col">Missed threshold trajectories</th></tr></thead><tbody>' + FIELDS.map(name => { const r=trajectories[name]; return `<tr><th scope="row">${escape(LABELS[name])}</th><td>${r.direction_correct_fraction==null?'Unavailable':`${fmt(r.direction_correct_fraction*100,1)}%`} (${r.direction_cases_abs_change_at_least_0_02_ft.toLocaleString()})</td><td>${r.rising_target_n.toLocaleString()}</td><td>${r.underforecast_fraction_on_rising_targets==null?'Unavailable':`${fmt(r.underforecast_fraction_on_rising_targets*100,1)}%`}</td><td>${r.threshold_timing_eligible_issue_count.toLocaleString()}</td><td>${fmt(r.mean_absolute_horizon_timing_error_hours)}</td><td>${r.threshold_timing_missed_by_forecast_n.toLocaleString()}</td></tr>`; }).join('') + '</tbody>';
      const worst = report.worst_event_failures_phase5b_coastal_tidal[horizon];
      $('model-lab-failures').innerHTML = '<thead><tr><th scope="col">Event group</th><th scope="col">Forecast rows</th><th scope="col">MAE (ft)</th><th scope="col">Bias (ft)</th><th scope="col">Underforecast rows</th></tr></thead><tbody>' + worst.map(r => `<tr><th scope="row">${escape(r.event_id)}</th><td>${r.forecast_count}</td><td>${fmt(r.mae_ft)}</td><td>${fmt(r.bias_ft)}</td><td>${fmt(r.underforecast_fraction*100,1)}%</td></tr>`).join('') + '</tbody>';
      const chosenCase = report.case_studies.find(c => c.case_id === $('model-lab-case').value) || report.case_studies[0];
      renderCase(chosenCase, horizon);
      const p = report.provenance;
      $('model-lab-provenance').innerHTML = `<p>Archive: ${escape(report.summary.archive_first_observation_utc)} – ${escape(report.summary.archive_last_observation_utc)}. Target: ${escape(p.target)}.</p><p>Source bins use UTC valid time. Receipt times are unavailable. Baseline regeneration: ${escape(report.baseline_reproduction.status)}. Hourly archives hashed: ${p.hourly_archive_months}. No prospective archive changes.</p><p>Promotion criteria: ${report.promotion_criteria.criteria.map(escape).join('; ')}.</p><p>† NOAA astronomical valid-time values are retrospective-only; issue-time availability is unverified. MCHL1 is omitted from this challenger.</p>`;
      const headline = report.challenger_headline[horizon].bounded_damped_trend_ft;
      const verdict = headline.beats_persistence && headline.beats_maul1_only ? 'The challenger is better than persistence and MAUL1-only on this reused historical sample; it remains unpromoted pending uncertainty and robustness criteria.' : 'The bounded damped-trend challenger does not beat both persistence and MAUL1-only on this reused historical sample.';
      setStatus(`UTC holdout sample: 2023 onward · ${data.paired_sample_n.toLocaleString()} common cases across all six models. ${verdict}`);
    };
    function renderCase(item, horizon) {
      if (!item || !window.Plotly) return;
      $('model-lab-case-note').textContent = `${item.label}. ${item.selection} Anchor issue ${item.anchor_issue_time_utc}; target valid time ${item.anchor_valid_time_utc}; observed target rise from issue stage ${fmt(item.target_rise_from_issue_ft)} ft.`;
      const observations = item.observations || [];
      const selected = item.forecasts_by_horizon[horizon] || [];
      const traces = [{name:'Observed MAUL1 stage (native 00065)',x:observations.map(x=>x.time_utc),y:observations.map(x=>x.stage_ft),mode:'lines',connectgaps:false,line:{color:'#20252b',width:3},hovertemplate:'Observed valid time: %{x}<br>Stage: %{y:.3f} ft<extra></extra>'}];
      for (const name of FIELDS) {
        const points = selected.filter(point => point.forecasts[name] != null);
        traces.push({name:LABELS[name],x:points.map(x=>x.valid_time_utc),y:points.map(x=>x.forecasts[name]),mode:'markers',marker:{color:COLORS[name],size:7,symbol:'circle'},customdata:points.map(x=>[x.issue_time_utc,x.observed_stage_ft]),hovertemplate:'Valid time: %{x}<br>Predicted: %{y:.3f} ft<br>Issued: %{customdata[0]}<br>Observed: %{customdata[1]:.3f} ft<extra>%{fullData.name}</extra>'});
      }
      const layout = {height:390,margin:{l:58,r:20,t:20,b:80},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',xaxis:{title:'UTC valid time',type:'date',gridcolor:'#e5e9ed'},yaxis:{title:'MAUL1 stage (ft, native gage height)',gridcolor:'#e5e9ed'},legend:{orientation:'h',y:-.28},hovermode:'closest',shapes:[{type:'line',x0:item.anchor_issue_time_utc,x1:item.anchor_issue_time_utc,y0:0,y1:1,yref:'paper',line:{color:'#606770',dash:'dash'}}],annotations:[{x:item.anchor_issue_time_utc,y:1,yref:'paper',text:'anchor issue time',showarrow:false,xanchor:'left',font:{size:10,color:'#606770'}}]};
      window.Plotly.react('model-lab-case-chart', traces, layout, {responsive:true,displaylogo:false});
    }
    const load = async () => {
      if (initialized) { if (window.Plotly) window.Plotly.Plots.resize('model-lab-case-chart'); return; }
      initialized = true;
      try {
        const response = await window.fetch('data/research/model-lab.json');
        if (!response.ok) throw new Error('report unavailable');
        report = await response.json();
        if (report.schema !== 'maul1.model-lab.report.v1' || !report.horizons || !Array.isArray(report.case_studies)) throw new Error('unsupported report');
        const select = $('model-lab-case');
        select.innerHTML = report.case_studies.map(item => `<option value="${escape(item.case_id)}">${escape(item.label)}</option>`).join('');
        if (!report.case_studies.length) select.innerHTML = '<option value="">No eligible case study</option>';
        render();
      } catch (error) {
        setStatus('Historical Model Lab report is unavailable; no historical result was inferred.');
      }
    };
    ['model-lab-horizon','model-lab-regime','model-lab-case'].forEach(id => $(id).addEventListener('change', render));
    window.addEventListener('maul1:viewchange', event => { if (event.detail && event.detail.panelId === 'model-lab-view') load(); });
    if (!panel.hidden) load();
    return {load, render, getReport:()=>report};
  }
  return {init, metricTable, fmt};
});

