(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) api.init(root.document, root);
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const LABELS = {
    persistence_ft: 'Persistence', maul1_only_ft: 'Phase 5A MAUL1-only',
    maul1_plus_coastal_ft: 'Phase 5A coastal', maul1_coastal_tidal: 'Phase 5B coastal + tidal',
    full_multivariable: 'Phase 5B full multivariable', bounded_damped_trend_ft: 'Damped-trend challenger'
  };
  const METHODS = Object.keys(LABELS);
  const COLORS = ['#727b84', '#287f8e', '#8064a2', '#c17b16', '#bd4c4c', '#39916e'];
  const escape = value => String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const fmt = (value, n=3) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toFixed(n);
  const table = (headers, rows) => `<table class="model-lab-table"><thead><tr>${headers.map(x=>`<th scope="col">${x}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table>`;

  function init(document, window) {
    const $ = id => document.getElementById(id);
    const panel = $('model-lab-view');
    if (!panel) return null;
    let payload = null, report = null, loaded = false;
    function renderPerformance() {
      const audit = payload.summary;
      const phase6 = report.phase6_qualifying_rise_groups_24h;
      const diag = report.horizons['24'].underforecast_and_false_alarm;
      const coastal = phase6.maul1_coastal_tidal;
      const compact = audit.definition_reproduction;
      $('rise-investigation-status').textContent = `${compact.phase6_groups} target-time groups; ${compact.detected_groups} detected and ${compact.missed_groups} missed by the Phase 5B coastal + tidal model. Grouping establishes verification units, not independent physical storms.`;
      $('rise-investigation-metrics').innerHTML = [
        ['Qualifying rise groups', compact.phase6_groups], ['Detected / missed', `${compact.detected_groups} / ${compact.missed_groups}`],
        ['False alert episodes', compact.phase5b_false_alert_clusters], ['False alert target windows', compact.false_positive_target_windows],
        ['Target-window POD', `${fmt(compact.target_window_probability_of_detection*100,1)}%`],
        ['Target-window false-alarm ratio', `${fmt(compact.target_window_false_alarm_ratio*100,1)}%`]
      ].map(([label,value])=>`<div class="rise-metric"><span>${escape(label)}</span><strong>${escape(value)}</strong></div>`).join('');
      const rows = METHODS.map((name, i) => {
        const rise = phase6[name], alerts = diag[name];
        const horizonCells = ['6','12','24'].map(h=>`<td>${fmt(report.horizons[h].metrics[name].mae_ft)}</td><td>${fmt(report.horizons[h].metrics[name].bias_ft)}</td>`).join('');
        return `<tr><th scope="row"><span class="model-swatch" style="--model-color:${COLORS[i]}"></span>${escape(LABELS[name])}</th><td>${rise.event_count}</td><td>${rise.detected_events}</td><td>${rise.missed_events}</td><td>${alerts.false_alert_episode_clusters}</td><td>${alerts.false_positive_target_windows}</td>${horizonCells}<td>${rise.median_lead_to_first_qualifying_verification_target_hours==null?'—':fmt(rise.median_lead_to_first_qualifying_verification_target_hours,1)}</td></tr>`;
      });
      $('rise-horizon-summary').innerHTML = table(['Model','24h rise groups','Detected','Missed','False alert episodes','False alert target windows','6h MAE (ft)','6h bias (ft)','12h MAE (ft)','12h bias (ft)','24h MAE (ft)','24h bias (ft)','Median lead to qualifying target (h)'], rows) +
        `<p class="small">The forecast-window false-alert counts use overlapping hourly targets. MAE and bias are paired all-case hindcast metrics. Significant-rise grouping and alert episodes are defined at 24h only; the global horizon selector controls the other Model Lab panels.</p>`;
      const context = audit.event_level_summary;
      const miss = context.large_subthreshold_forecast_not_causal;
      const near = context.near_threshold_underforecast_not_causal;
      const fp = audit.false_vs_true_alert_cluster_comparison;
      $('rise-diagnosis').innerHTML = `<p><strong>Supported descriptive finding:</strong> ${miss.n_groups} of the ${compact.missed_groups} missed groups never reached a 0.50 ft forecast threshold. Their median maximum predicted rise was ${fmt(miss.median_max_predicted_change_ft)} ft against a ${fmt(miss.median_max_observed_change_ft)} ft median observed target rise. Another ${near.n_groups} missed groups peaked at a forecast rise between 0.40 and 0.50 ft. Two threshold crossings occurred only after their group’s first qualifying target and therefore failed the predeclared lead rule.</p><p>The alert threshold found ${compact.true_positive_target_windows} of ${compact.qualifying_observed_target_windows} qualifying target windows (POD ${fmt(compact.target_window_probability_of_detection*100,1)}%; false-alarm ratio ${fmt(compact.target_window_false_alarm_ratio*100,1)}%). False and hit-containing alert episodes had similar median NWCL1 residuals (${fmt(fp.false_median_nwcl1_residual_mllw_ft)} vs ${fmt(fp.true_median_nwcl1_residual_mllw_ft)} ft MLLW) and winds (${fmt(fp.false_median_wind_speed_knots,1)} vs ${fmt(fp.true_median_wind_speed_knots,1)} knots). These are co-occurrences; they do not show that coastal forcing caused misses or false alarms.</p><p>NWCL1 setup and wind, DENL1 discharge, and MDLL1 within-station changes were available in the event issue windows summarized by the audit. Their presence alone did not distinguish hits from misses. The historical feature set does not establish what source values had arrived by an actual forecast issuance.</p>`;
      $('rise-limitations').innerHTML = `<ul><li>All values are ${escape(payload.evidence_label.toLowerCase())}; the reused 2023 onward period has already been inspected.</li><li>Valid times are archived, but original receipt times are missing. Completed historical bins do not prove issue-time availability.</li><li>Phase 6 target-time groups are not confirmed independent hydrologic events; their crosswalk to the different Phase 3B response catalog is descriptive and windows overlap.</li><li>MAUL1 is USGS 00065 native gage height. It is not NAVD88; no 4.0 ft NAVD88 threshold is applied. NWCL1 residual remains MLLW referenced.</li><li>MAUL1 observations may be provisional. No missing values are filled. MCHL1 remains shadow-only and is not a validated predictor.</li><li>The damped-trend candidate detected zero of 109 groups and is not a significant-rise improvement. No candidate merits isolated shadow testing on these results alone.</li></ul><p><strong>Next study:</strong> first validate and archive local precipitation and tributary series prospectively, along with receipt timestamps and QC state. Then predeclare an event-blocked experiment for rapid/slow trajectory types and alert-episode tradeoffs. Do not tune thresholds on this reused sample.</p>`;
    }
    function renderEvent() {
      const event = payload.representative_events.find(row=>row.event_id === $('rise-event-select').value) || payload.representative_events[0];
      if (!event || !window.Plotly) return;
      const rows = event.timeline_rows || [];
      const modelSpecs = [
        ['phase5a_maul1_only_stage_native_ft','Phase 5A MAUL1-only','#287f8e'],
        ['phase5a_coastal_stage_native_ft','Phase 5A coastal','#8064a2'],
        ['phase5b_coastal_tidal_stage_native_ft','Phase 5B coastal + tidal','#c17b16']
      ];
      const traces = [
        {name:'Observed MAUL1 issue stage (native 00065)',x:rows.map(r=>r.issue_time_utc),y:rows.map(r=>r.issue_maul1_stage_native_ft),mode:'lines',connectgaps:false,line:{color:'#20252b',width:2}},
        {name:'Observed MAUL1 target stage (native 00065)',x:rows.map(r=>r.valid_time_utc),y:rows.map(r=>r.actual_valid_maul1_stage_native_ft),mode:'lines+markers',connectgaps:false,line:{color:'#111820',width:3},marker:{size:4}}
      ];
      for (const [key,name,color] of modelSpecs) traces.push({name,x:rows.map(r=>r.valid_time_utc),y:rows.map(r=>r[key]),mode:'markers',connectgaps:false,marker:{color,size:6},customdata:rows.map(r=>r.issue_time_utc),hovertemplate:'Valid: %{x}<br>Forecast: %{y:.3f} ft<br>Issued: %{customdata}<extra>'+name+'</extra>'});
      const config = report.challenger_protocol.config_by_horizon['24'];
      const challenger = rows.map(r=>{
        const f=r.features||{}, stage=r.issue_maul1_stage_native_ft, change=f.maul1_change_6h_ft;
        if (stage == null) return null;
        if (change == null) return stage;
        const slope=Math.max(-config.cap_per_hour,Math.min(config.cap_per_hour,change/6));
        return stage+24*config.shrink*slope;
      });
      traces.push({name:'Bounded damped-trend challenger (experimental)',x:rows.map(r=>r.valid_time_utc),y:challenger,mode:'markers',connectgaps:false,marker:{color:'#39916e',symbol:'diamond',size:6},customdata:rows.map(r=>r.issue_time_utc),hovertemplate:'Valid: %{x}<br>Forecast: %{y:.3f} ft<br>Issued: %{customdata}<extra>Experimental challenger</extra>'});
      window.Plotly.react('rise-stage-chart',traces,{height:380,margin:{l:60,r:20,t:20,b:90},xaxis:{title:'UTC valid time',type:'date'},yaxis:{title:'MAUL1 stage (ft, native gage height)'},legend:{orientation:'h',y:-.3},hovermode:'closest'}, {responsive:true,displaylogo:false});
      const f = rows.map(r=>r.features||{}), times=rows.map(r=>r.issue_time_utc);
      const wind=f.map(v=>v.nwcl1_wind_u_knots==null||v.nwcl1_wind_v_knots==null?null:Math.hypot(v.nwcl1_wind_u_knots,v.nwcl1_wind_v_knots));
      window.Plotly.react('rise-coastal-chart',[
        {name:'NWCL1 residual setup (ft MLLW)',x:times,y:f.map(v=>v.nwcl1_residual_mllw_ft),mode:'lines+markers',connectgaps:false,line:{color:'#167c80'},yaxis:'y'},
        {name:'NWCL1 wind speed (knots)',x:times,y:wind,mode:'lines+markers',connectgaps:false,line:{color:'#5376a6'},yaxis:'y2'}
      ],{height:300,margin:{l:55,r:55,t:35,b:90},title:'Issue-time coastal context',xaxis:{title:'UTC issue time',type:'date'},yaxis:{title:'Residual (ft MLLW)'},yaxis2:{title:'Wind (knots)',overlaying:'y',side:'right'},legend:{orientation:'h',y:-.36}}, {responsive:true,displaylogo:false});
      window.Plotly.react('rise-inland-chart',[
        {name:'DENL1 discharge (log units)',x:times,y:f.map(v=>v.denl1_log_discharge),mode:'lines+markers',connectgaps:false,line:{color:'#a55d23'},yaxis:'y'},
        {name:'MDLL1 24h stage change (ft, within-station)',x:times,y:f.map(v=>v.mdll1_stage_change_24h_ft),mode:'lines+markers',connectgaps:false,line:{color:'#7562a5'},yaxis:'y2'}
      ],{height:300,margin:{l:55,r:60,t:35,b:90},title:'Issue-time river and inland context',xaxis:{title:'UTC issue time',type:'date'},yaxis:{title:'DENL1 log discharge'},yaxis2:{title:'MDLL1 24h change (ft)',overlaying:'y',side:'right'},legend:{orientation:'h',y:-.36}}, {responsive:true,displaylogo:false});
      $('rise-event-note').textContent = `${event.event_id}: ${event.selection}. ${event.interpretation} ${rows.length} aligned hourly issue/valid pairs; missing feature values remain gaps. Challenger points are reconstructed from the frozen historical configuration using only issue-time MAUL1 features. Archived USGS approval/provisional and source receipt-time flags are unavailable for these cases, so event-level QC status cannot be reconstructed.`;
    }
    async function load() {
      if (loaded) return;
      loaded = true;
      try {
        const [auditResponse, modelResponse] = await Promise.all([
          window.fetch('data/research/significant-rise.json'), window.fetch('data/research/model-lab.json')
        ]);
        if (!auditResponse.ok || !modelResponse.ok) throw new Error('report unavailable');
        payload = await auditResponse.json(); report = await modelResponse.json();
        if (payload.schema !== 'maul1.significant-rise-model-lab.v1' || report.schema !== 'maul1.model-lab.report.v1') throw new Error('unsupported report');
        $('rise-event-select').innerHTML = payload.representative_events.map(event=>`<option value="${escape(event.event_id)}">${escape(event.event_id)} · ${escape(event.selection)}</option>`).join('');
        renderPerformance(); renderEvent();
      } catch (error) {
        $('rise-investigation-status').textContent = 'Significant-rise research data is unavailable; no results were inferred.';
      }
    }
    $('rise-event-select').addEventListener('change', renderEvent);
    window.addEventListener('maul1:viewchange', event=>{if(event.detail&&event.detail.panelId==='model-lab-view')load();});
    if (!panel.hidden) load();
    return {load,renderEvent,renderPerformance};
  }
  return {init,fmt};
});
