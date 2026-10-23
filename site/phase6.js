(() => {
  const root = document.getElementById('phase6-content');
  if (!root) return;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = value => value == null || value === '' || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(2)} ft`;
  const models = ['persistence','phase5a_maul1_only','phase5a_coastal','phase5b_coastal_tidal','phase5b_full_multivariable'];
  const showForecast = record => {
    if (!record || record.mode !== 'authentic') return '<p>No authentic prospective issuance has been archived yet. Scheduled runs and source availability determine when the first issue can be made.</p>';
    let html = `<p>Actual issue: <strong>${esc(record.actual_issue_time_utc)}</strong> · Native MAUL1 stage ${fmt(record.latest_maul1_native_stage_ft)}</p>`;
    const availability = record.snapshot?.availability || {};
    html += '<p>Input availability: ' + Object.entries(availability).map(([k,v])=>`${esc(k)} ${esc(v.status)}${v.age_hours == null ? '' : ` (${Number(v.age_hours).toFixed(1)} h old)`}`).join(' · ') + '</p>';
    html += '<div class="table-wrap" role="region" tabindex="0" aria-label="Forecast guidance by horizon and model"><table><thead><tr><th>Horizon</th><th>Valid time</th>' + models.map(m=>`<th>${esc(m.replaceAll('_',' '))}</th>`).join('') + '</tr></thead><tbody>';
    for (const [h, forecast] of Object.entries(record.forecasts || {})) {
      html += `<tr><th>${esc(h)} h</th><td>${esc(forecast.valid_time_utc)}</td>`;
      for (const name of models) { const m=forecast.models?.[name]; html += `<td>${m?.status === 'issued' ? `${fmt(m.predicted_stage_native_ft)}<br><small>Δ ${fmt(m.predicted_change_ft)}; 80% interval ${fmt(m.interval_lower_ft)}–${fmt(m.interval_upper_ft)}</small>` : esc(m?.status || 'unavailable')}</td>`; }
      html += '</tr>';
    }
    return html + '</tbody></table></div>';
  };
  const showVerification = async entry => {
    if (!entry?.verification_files?.length) return '<p>No completed verifications are available for this issuance yet.</p>';
    const files = await Promise.all(entry.verification_files.map(path=>fetch(`data/prospective/history/${path}`).then(r=>r.ok?r.json():null).catch(()=>null)));
    const rows=files.flatMap(x=>x?.revisions || []);
    if (!rows.length) return '<p>No completed verifications are available for this issuance yet.</p>';
    return '<div class="table-wrap" role="region" tabindex="0" aria-label="Forecast verification observations"><table><thead><tr><th>Model / horizon</th><th>Forecast valid time</th><th>Observed time</th><th>Observed native stage</th><th>Error</th><th>Revision</th></tr></thead><tbody>' + rows.map(v=>`<tr><td>${esc(v.model)} / ${esc(v.horizon_hours)} h</td><td>${esc(v.forecast_valid_time_utc)}</td><td>${esc(v.observation_valid_time_utc)}</td><td>${fmt(v.observed_native_stage_ft)}</td><td>${fmt(v.signed_error_ft)}</td><td>${esc(v.revision)}</td></tr>`).join('') + '</tbody></table></div>';
  };
  const showMetrics = report => {
    const groups=report?.model_horizon_metrics || {};
    if (!Object.keys(groups).length) return '<p>No prospective verification sample is available. Accuracy and event skill are intentionally withheld until observations mature.</p>';
    const byModel = new Map(Object.entries(groups).map(([key,value])=>[key,value]));
    const completeness=report?.verification_completeness || {};
    const horizonList = [6,12,24];
    const rows = [];
    for (const model of models) for (const horizon of horizonList) {
      const name = `${model}:${horizon}h`;
      const m = byModel.get(name);
      const c = completeness[name];
      const coverage = c ? `${c.verified}/${c.matured} verified/matured; ${c.due_unverified} due unverified; ${c.not_yet_due} not yet due` : '—';
      if (!m) {
        rows.push(`<tr><th>${esc(model.replaceAll('_',' '))} / ${horizon} h</th><td colspan="10">Pending verification; no matured archived outcomes yet.</td><td>${esc(coverage)}</td><td>Independent-event score pending</td></tr>`);
        continue;
      }
      const riseCounts = ['0.25','0.50','1.00'].map(t=>{
        const r=m.rises?.[t];
        return `${t} ft: ${r ? `${r.hits}/${r.misses}/${r.false_alarms}; POD ${r.probability_of_detection==null?'—':`${(100*r.probability_of_detection).toFixed(0)}%`}; FAR ${r.false_alarm_ratio==null?'—':`${(100*r.false_alarm_ratio).toFixed(0)}%`}` : '—'}`;
      }).join('<br>');
      const event=m.qualifying_24h_events;
      let eventSummary='Not grouped at this horizon';
      if (horizon===24) {
        if (!event || event.status!=='computed') eventSummary=`${event?.event_count ?? 0} groups; event metrics withheld until five`;
        else {
          const leads=(event.events || []).filter(x=>x.detected && x.lead_to_first_qualifying_target_hours!=null).map(x=>x.lead_to_first_qualifying_target_hours).sort((a,b)=>a-b);
          const median=leads.length ? (leads.length%2 ? leads[(leads.length-1)/2] : (leads[leads.length/2-1]+leads[leads.length/2])/2) : null;
          eventSummary=`${event.detected_events}/${event.event_count} detected; ${event.missed_events} missed; median lead ${median==null?'—':`${median.toFixed(1)} h`}`;
        }
      }
      const age=m.input_age_effect || {};
      const ageSummary=`≤1 h: ${fmt(age.le_1h?.mae_ft)} (n=${age.le_1h?.n ?? 0})<br>&gt;1 h: ${fmt(age.gt_1h?.mae_ft)} (n=${age.gt_1h?.n ?? 0})`;
      const latency=m.observation_latency_minutes || {};
      const delaySummary=latency.median==null?'—':`${Number(latency.median).toFixed(0)} min (n=${latency.n})`;
      rows.push(`<tr><th>${esc(model.replaceAll('_',' '))} / ${horizon} h</th><td>${esc(m.n)}</td><td>${fmt(m.mae_ft)}</td><td>${fmt(m.rmse_ft)}</td><td>${fmt(m.bias_ft)}</td><td>${fmt(m.mae_persistence_ft)}${m.skill_vs_persistence==null?'':`<br><small>skill ${(100*m.skill_vs_persistence).toFixed(1)}%</small>`}</td><td>${riseCounts}<br><small>hits/misses/false alarms</small></td><td>${m.intervals?.coverage==null?'—':`${(100*m.intervals.coverage).toFixed(0)}%`}<br><small>n=${esc(m.intervals?.n ?? 0)}</small></td><td>${m.intervals?.upper_bound_exceedance_frequency==null?'—':`${(100*m.intervals.upper_bound_exceedance_frequency).toFixed(0)}%`}</td><td>${ageSummary}</td><td>${delaySummary}</td><td>${esc(coverage)}</td><td>${esc(eventSummary)}</td></tr>`);
    }
    return '<div class="table-wrap" role="region" tabindex="0" aria-label="Prospective forecast scorecard"><table><thead><tr><th>Model / horizon</th><th>Verified N</th><th>MAE</th><th>RMSE</th><th>Bias</th><th>Persistence MAE / skill</th><th>Rise hits / misses / false alarms at 0.25, 0.50, 1.00 ft</th><th>80% interval coverage</th><th>Upper bound exceeded</th><th>MAE by MAUL1 input age</th><th>Target observation delay</th><th>Verification coverage</th><th>Independent 0.50-ft 24h rise groups / lead</th></tr></thead><tbody>' + rows.join('') + '</tbody></table></div><p>Rise counts use individual overlapping forecasts. Observation delay is retrieval time minus observation valid time. Due-but-unverified targets are not assigned a cause. The 24-hour event row groups outcome-qualified windows; event skill stays withheld below five independent groups. Pending rows have no score yet.</p>';
  };
  Promise.all(['data/prospective/latest.json','data/prospective/history/index.json','data/prospective/performance.json'].map(path=>fetch(path).then(r=>r.ok?r.json():null))).then(async ([latest, history, metrics]) => {
    root.innerHTML = `<div id="phase6-latest">${showForecast(latest)}</div><h3>Archived forecast history</h3><label for="phase6-issue-select">Select an immutable issuance:</label> <select id="phase6-issue-select"></select><div id="phase6-selected">No previous issues.</div><h3>Prospective performance</h3><p>Verification count: ${esc(metrics?.verification_count ?? 0)} · ${esc(metrics?.revision_count ?? 0)} retained verification revisions. Overlapping hourly forecasts are not independent event samples.</p>${showMetrics(metrics)}<p><strong>Limitations:</strong> research-only; MAUL1 native gage-height datum; no NAVD88 threshold equivalence; input availability depends on source freshness; event metrics remain withheld below five independent groups. Frozen model version: ${esc(latest?.snapshot?.model_artifact_sha256 || 'pending first issue')}.</p>`;
    const select=document.getElementById('phase6-issue-select');
    const entries=(history || []).filter(x=>x.mode==='authentic').slice().reverse();
    if (!entries.length) { select.disabled=true; return; }
    select.innerHTML=entries.map((x,i)=>`<option value="${i}">${esc(x.actual_issue_time_utc)} · ${esc(x.issuance_id)}</option>`).join('');
    const render=async()=>{
      const entry=entries[Number(select.value)];
      const response=await fetch(`data/prospective/history/${entry.forecast_file}`);
      const record=response.ok?await response.json():null;
      const verified=await showVerification(entry);
      document.getElementById('phase6-selected').innerHTML=showForecast(record)+`<h4>Subsequent observations</h4>${verified}`;
    };
    select.addEventListener('change',render); await render();
  }).catch(() => { root.textContent = 'Prospective archive is temporarily unavailable.'; });
})();
