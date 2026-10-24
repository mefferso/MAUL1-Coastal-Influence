(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.MAUL1ForecastView = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const modelNames = {
    persistence: 'Persistence',
    phase5a_maul1_only: 'Phase 5A · MAUL1 only',
    phase5a_coastal: 'Phase 5A · coastal predictors',
    phase5b_coastal_tidal: 'Phase 5B · coastal + tidal',
    phase5b_full_multivariable: 'Phase 5B · full multivariable'
  };
  const modelOrder = ['phase5a_maul1_only', 'phase5a_coastal', 'phase5b_coastal_tidal', 'phase5b_full_multivariable'];
  const horizons = [6, 12, 24];
  const numeric = value => value !== null && value !== '' && Number.isFinite(Number(value));
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const ft = value => numeric(value) ? `${Number(value).toFixed(2)} ft` : '—';
  const nativeDatum = value => { if (!value) return true; const label=String(value); return !/(NAVD88|MLLW|MHHW|NGVD)/i.test(label) && /(native|gage height|00065)/i.test(label); };
  const validNative = (record, now=Date.now()) => record?.mode === 'authentic' && numeric(record.latest_maul1_native_stage_ft) &&
    nativeDatum(record.datum) && nativeDatum(record.stage_datum) &&
    Number.isFinite(Date.parse(record.actual_issue_time_utc)) && Date.parse(record.actual_issue_time_utc) <= now &&
    Number.isFinite(Date.parse(record.model_anchor_time_utc)) && Date.parse(record.model_anchor_time_utc) <= Date.parse(record.actual_issue_time_utc);
  const forecastDatumIsNative = forecast => nativeDatum(forecast?.datum);
  const forecastChronologyIsValid = (record, forecast) => { const issue=Date.parse(record?.actual_issue_time_utc), valid=Date.parse(forecast?.valid_time_utc); return Number.isFinite(issue) && Number.isFinite(valid) && valid >= issue; };
  const qcIsUsable = value => { if(value==null)return true; const flags=Array.isArray(value)?value.map(x=>String(x).trim()):typeof value==='string'?value.split(',').map(x=>x.trim()):null; return flags!==null && flags.every(x=>['','0','P','provisional'].includes(x)); };
  const observationAtIssue = (record, now=Date.now()) => {
    const observation=record?.snapshot?.availability?.MAUL1_00065?.observation;
    const valid=Date.parse(observation?.valid_time_utc), retrieved=Date.parse(observation?.retrieved_utc), issue=Date.parse(record?.actual_issue_time_utc);
    return record?.snapshot?.availability?.MAUL1_00065?.status==='eligible' && observation?.station==='MAUL1' && observation?.parameter==='stage' && observation?.source==='USGS NWIS IV' && observation?.units==='ft' && Boolean(observation?.datum) && nativeDatum(observation?.datum) && numeric(observation?.value) && observation?.qc!=null && qcIsUsable(observation.qc) && Number.isFinite(valid) && Number.isFinite(retrieved) && Number.isFinite(issue) && issue<=now && valid<=retrieved && retrieved<=issue && valid<=issue ? observation : null;
  };
  const eligibleObservation = (record, now=Date.now()) => {
    const observation=observationAtIssue(record,now), valid=Date.parse(observation?.valid_time_utc);
    return observation && now-valid<=2*3600000 ? observation : null;
  };
  const signedFt = value => numeric(value) ? `${Number(value)>=0?'+':''}${Number(value).toFixed(2)} ft` : '—';
  function renderGuidance(record, now=Date.now()) {
    if (!validNative(record,now)) return '<p class="research-empty">No compatible authentic native-stage issuance is available for forecast guidance.</p>';
    const issueEpoch=Date.parse(record.actual_issue_time_utc), issueAge=(now-issueEpoch)/3600000;
    const issueFreshness=issueAge>3?`<span class="research-status status-stale">Archived issue is stale · ${issueAge.toFixed(1)} h old</span>`:`<span class="research-status status-fresh">Authentic issue · ${issueAge<1?`${Math.round(issueAge*60)} min`:`${issueAge.toFixed(1)} h`} old</span>`;
    const archivedObservation=observationAtIssue(record,now);
    const observation=eligibleObservation(record,now);
    const featureValues=record.snapshot?.features||{};
    const sixHourChange=featureValues.maul1_change_6h_ft;
    const observationSummary=archivedObservation
      ? `<div class="forecast-fact"><span>Latest archived MAUL1 observation · native USGS 00065</span><strong>${ft(archivedObservation.value)} · ${observation?'fresh':'stale at view'}</strong><small>Valid ${esc(archivedObservation.valid_time_utc)} · ${( (now-Date.parse(archivedObservation.valid_time_utc))/3600000 ).toFixed(1)} h old${observation?'':'; withheld from chart because it is stale'}</small></div>`
      : `<div class="forecast-fact"><span>Latest archived MAUL1 observation · native USGS 00065</span><strong>Unavailable or ineligible</strong><small>No authentic issue observation with valid station, datum, QC, and retrieval chronology was verified.</small></div>`;
    const recentChange=numeric(sixHourChange)?`<div class="forecast-fact"><span>Recent six-hour native-stage input change</span><strong>${Number(sixHourChange)>0?'Rising':Number(sixHourChange)<0?'Falling':'Stable'} · ${signedFt(sixHourChange)}</strong><small>Frozen model input feature; valid at the archived feature time.</small></div>`:`<div class="forecast-fact"><span>Recent six-hour native-stage input change</span><strong>Unavailable</strong><small>No complete six-hour model input change is documented.</small></div>`;
    const diagnostics=record.snapshot?.feature_diagnostics||{};
    const missing=diagnostics.missing_features||{};
    const missingEntries=Object.entries(missing).flatMap(([group,names])=>(Array.isArray(names)?names:[]).map(name=>({group,name})));
    const allModelOutputs=horizons.flatMap(h=>Object.values(record.forecasts?.[String(h)]?.models||{})).filter(item=>item?.status==='issued');
    const imputedCounts=allModelOutputs.map(item=>Number.isInteger(item.imputed_feature_count)?item.imputed_feature_count:0);
    const maxImputed=imputedCounts.length?Math.max(...imputedCounts):null;
    const inputNotice=missingEntries.length||maxImputed>0
      ? `Input limitations: up to ${maxImputed??0} imputed feature(s) for an issued model/horizon; ${missingEntries.length} documented predictor(s) missing.`
      : 'No imputation or predictor-missingness summary is documented for this issue.';
    const detailMissing=missingEntries.length?missingEntries.map(({group,name})=>{
      const reason=/nwcl1_residual/i.test(name)?'Same-time coastal water-level residual evidence is unavailable; wind alone does not provide that comparison.':/mchl1/i.test(name)?'MCHL1 is unverified, remains shadow-only, and is excluded from frozen model inputs.':`${group} predictor is unavailable in this archived issue.`;
      return `<li><strong>${esc(name)}</strong> · ${esc(reason)}</li>`;
    }).join(''):'<li>No predictor features are listed as missing in the issue diagnostics.</li>';
    const featureTime=diagnostics.expected_latest_bin_utc||diagnostics.model_anchor_utc||record.model_anchor_time_utc||'unavailable';
    const availability=record.snapshot?.availability||{};
    const availabilityText=Object.entries(availability).map(([station,item])=>`${esc(station)}: ${esc(item.status||'status unavailable')}${item.age_hours==null?'':` · ${Number(item.age_hours).toFixed(1)} h old`}`).join(' · ');
    const completeness=`<details class="guidance-provenance"><summary>Input completeness and timing</summary><p>${esc(inputNotice)} Imputation does not automatically invalidate a prediction, and the count alone does not establish relative model quality.</p><ul>${detailMissing}</ul><p>Archived model anchor: ${esc(record.model_anchor_time_utc||'unavailable')}. Latest completed model-feature bin: ${esc(featureTime)}. MAUL1 observation: ${archivedObservation?`eligible at issuance, valid ${esc(archivedObservation.valid_time_utc)}`:`not verified as eligible`}. Current observation and frozen inputs may use different valid times.</p><p>Issue snapshot status: ${availabilityText||'unavailable'}.</p><p>Per-model imputed feature counts are shown in the model comparison table.</p></details>`;
    const cards = horizons.map(horizon => {
      const forecast = record.forecasts?.[String(horizon)];
      if (!forecast || !forecastDatumIsNative(forecast) || !forecastChronologyIsValid(record, forecast)) return `<article class="horizon-card"><h3>${horizon}-hour guidance</h3><p>Forecast horizon unavailable in this authentic issue.</p></article>`;
      const persistence = forecast.models?.persistence;
      const candidates = modelOrder.map(key => forecast.models?.[key]).filter(item => item?.status === 'issued' && numeric(item.predicted_stage_native_ft));
      const values = candidates.map(item => Number(item.predicted_stage_native_ft));
      const spread = values.length ? `${Math.min(...values).toFixed(2)}–${Math.max(...values).toFixed(2)} ft` : 'unavailable';
      const changes=candidates.filter(item=>numeric(item.predicted_change_ft)).map(item=>Number(item.predicted_change_ft));
      const changeRange=changes.length?`${signedFt(Math.min(...changes))} to ${signedFt(Math.max(...changes))}`:'unavailable';
      const details = Object.entries(modelNames).map(([key, name]) => {
        const item = forecast.models?.[key];
        if (!item || item.status !== 'issued') return `<tr><th>${name}</th><td colspan="4">Unavailable for this issue</td></tr>`;
        const interval = numeric(item.interval_lower_ft) && numeric(item.interval_upper_ft)
          ? `${ft(item.interval_lower_ft)}–${ft(item.interval_upper_ft)} · archived bounds; calibration not established here`
          : 'Not calibrated / unavailable';
        return `<tr><th>${name}</th><td>${ft(item.predicted_stage_native_ft)}</td><td>${signedFt(item.predicted_change_ft)}</td><td>${Number.isInteger(item.imputed_feature_count)?item.imputed_feature_count:'—'}</td><td>${interval}</td></tr>`;
      }).join('');
      const lead = numeric(forecast.effective_lead_hours) ? `${Number(forecast.effective_lead_hours).toFixed(1)} h effective lead` : `${horizon} h nominal lead`;
      return `<article class="horizon-card"><div class="horizon-heading"><h3>${horizon}-hour guidance</h3><span>${lead}</span></div><p class="valid-time">Valid ${esc(forecast.valid_time_utc || 'time unavailable')}</p><p class="change-range">Experimental model changes from documented anchor: <strong>${changeRange}</strong></p><p class="persistence-value">Persistence baseline <strong>${persistence?.status === 'issued' ? ft(persistence.predicted_stage_native_ft) : 'unavailable'}</strong> (${numeric(persistence?.predicted_change_ft)?`${signedFt(persistence.predicted_change_ft)} change`: 'change unavailable'})</p><p class="model-spread">Available experimental stage outputs span <strong>${spread}</strong> across ${candidates.length} model(s). This is output spread, not a calibrated interval or probability.</p><details><summary>Compare individual model guidance</summary><div class="table-wrap" role="region" tabindex="0" aria-label="${horizon}-hour model guidance"><table><thead><tr><th>Model</th><th>Native stage</th><th>Change from anchor</th><th>Imputed features</th><th>Archived within-model bounds · calibration not established here</th></tr></thead><tbody>${details}</tbody></table></div></details></article>`;
    }).join('');
    return `<section class="forecast-glance" aria-label="Current forecast summary"><div class="forecast-glance-top"><div><p class="forecast-kicker">Latest archived authentic forecast</p><h3>MAUL1 · native USGS 00065 gage height</h3><p>Model anchor ${ft(record.latest_maul1_native_stage_ft)} at ${esc(record.model_anchor_time_utc||'time unavailable')} · Issue ${esc(record.actual_issue_time_utc||'time unavailable')}</p></div>${issueFreshness}</div><div class="forecast-facts">${observationSummary}${recentChange}</div><div class="horizon-grid">${cards}</div><p class="input-limitations">${esc(inputNotice)}</p>${completeness}<p class="no-preferred-model"><strong>Model skill during independent meaningful rises has not been established.</strong> These predictions are experimental, with no preferred model, flood probability, or warning recommendation.</p></section>`;
  }
  function renderArchiveCycleHealth(history, now=Date.now()) {
    const seen=new Set();
    const entries=(Array.isArray(history)?history:[]).filter(item=>{
      if(item?.mode!=='authentic'||!item.issuance_id||seen.has(item.issuance_id)||!Number.isFinite(Date.parse(item.actual_issue_time_utc))||Date.parse(item.actual_issue_time_utc)>now)return false;
      seen.add(item.issuance_id);return true;
    }).sort((a,b)=>Date.parse(a.actual_issue_time_utc)-Date.parse(b.actual_issue_time_utc));
    if(!entries.length)return '<p>No authentic forecast issue is recorded in the archive index.</p>';
    const latest=entries.at(-1), age=(now-Date.parse(latest.actual_issue_time_utc))/3600000;
    const gap=entries.length>1?(Date.parse(latest.actual_issue_time_utc)-Date.parse(entries.at(-2).actual_issue_time_utc))/3600000:null;
    return `<p><strong>Archive cycle:</strong> ${entries.length} authentic issues recorded. Latest ${esc(latest.actual_issue_time_utc)} · ${age<1?`${Math.round(age*60)} min`:`${age.toFixed(1)} h`} old${gap===null?'':`; previous archived issue was ${gap.toFixed(1)} h earlier`}. The hourly Actions schedule does not guarantee an archived issue every hour; this history records issues, not skipped runs.</p>`;
  }
  function renderVerificationOverview(report) {
    const groups=report?.model_horizon_metrics||{};
    const modelKeys=['phase5a_maul1_only','phase5a_coastal','phase5b_coastal_tidal','phase5b_full_multivariable'];
    const fmtRange=values=>values.length?`${Math.min(...values).toFixed(3)}–${Math.max(...values).toFixed(3)} ft`:'—';
    const fmtSkill=values=>values.length?`${(100*Math.min(...values)).toFixed(1)}% to ${(100*Math.max(...values)).toFixed(1)}%`:'—';
    const rows=[6,12,24].map(horizon=>{
      const persistence=groups[`persistence:${horizon}h`];
      const models=modelKeys.map(key=>groups[`${key}:${horizon}h`]).filter(Boolean);
      const mae=models.map(item=>Number(item.mae_ft)).filter(Number.isFinite);
      const skill=models.map(item=>Number(item.skill_vs_persistence)).filter(Number.isFinite);
      return `<tr><th>${horizon} h</th><td>${persistence?.n??models[0]?.n??0}</td><td>${persistence?.mae_ft==null?'—':`${Number(persistence.mae_ft).toFixed(3)} ft`}</td><td>${fmtRange(mae)}</td><td>${fmtSkill(skill)}</td></tr>`;
    }).join('');
    const eventSource=groups['phase5a_maul1_only:24h']?.qualifying_24h_events||groups['persistence:24h']?.qualifying_24h_events;
    const eventCount=Number.isInteger(eventSource?.event_count)?eventSource.event_count:0;
    const eventStatus=eventCount===0?'No independent qualifying 24-hour rises of at least 0.50 ft are yet present; meaningful event skill has not been demonstrated.':`${eventCount} independent qualifying 24-hour rise group(s) are recorded; interpret the event-level metrics with their small sample guard.`;
    return `<section class="verification-overview" aria-label="Prospective verification overview"><h3>Prospective verification at a glance</h3><div class="table-wrap" role="region" tabindex="0" aria-label="Verification overview by horizon"><table><thead><tr><th>Horizon</th><th>Verified pairs</th><th>Persistence MAE</th><th>Experimental-model MAE range</th><th>Skill range vs persistence</th></tr></thead><tbody>${rows}</tbody></table></div><p><strong>Independent event evidence:</strong> ${eventCount} qualifying 24-hour rises of at least 0.50 ft. ${esc(eventStatus)}</p><p>Verified pairs are overlapping forecast/observation comparisons, not independent events. Nearby issue times can share target observations and the same rising episode, so pair counts do not measure the number of independent flood events. MAE and skill are descriptive at this sample size; no model is selected.</p></section>`;
  }
  function buildTraces(record, now=Date.now()) {
    if (!validNative(record,now)) return [];
    const issueTime = record.actual_issue_time_utc;
    const anchor = Number(record.latest_maul1_native_stage_ft);
    const traces = [];
    const eligible = horizons.map(h => [h, record.forecasts?.[String(h)]]).filter(([, f]) => f && forecastDatumIsNative(f) && forecastChronologyIsValid(record, f));
    const observation=eligibleObservation(record,now);
    if(observation) {
      traces.push({name:'Latest observation · USGS 00065',x:[observation.valid_time_utc],y:[Number(observation.value)],mode:'markers',marker:{color:'#12303c',size:10,symbol:'diamond'},hovertemplate:'Observed %{y:.2f} ft native stage<br>Valid '+observation.valid_time_utc+'<br>Retrieved '+observation.retrieved_utc+'<extra>Latest observation</extra>',issuance:issueTime});
    }
    const perModel = key => eligible.map(([horizon, forecast]) => {
      const item = forecast.models?.[key];
      const lead = numeric(forecast.effective_lead_hours) ? Number(forecast.effective_lead_hours) : horizon;
      return item?.status === 'issued' && numeric(item.predicted_stage_native_ft) && Number.isFinite(lead) && lead >= 0
        ? { x: forecast.valid_time_utc, y: Number(item.predicted_stage_native_ft), item, validTime: forecast.valid_time_utc, lead }
        : null;
    }).filter(Boolean).sort((a,b)=>Date.parse(a.x)-Date.parse(b.x));
    const colors = {persistence:'#697b80',phase5a_maul1_only:'#287a8d',phase5a_coastal:'#99558c',phase5b_coastal_tidal:'#ca7a36',phase5b_full_multivariable:'#496d4c'};
    traces.push({name:'Model anchor · native stage',x:[record.model_anchor_time_utc],y:[anchor],mode:'markers',marker:{color:'#12303c',size:9,symbol:'circle-open',line:{width:2}},hovertemplate:'Model anchor %{y:.2f} ft native stage<br>%{x}<extra>Forecast reference</extra>',issuance:issueTime});
    for (const key of ['persistence', ...modelOrder]) {
      const points = [{x:record.model_anchor_time_utc,y:anchor,item:null,validTime:record.model_anchor_time_utc,lead:null}, ...perModel(key)];
      if (points.length < 2) continue;
      const intervals = points.map(point => point.item && numeric(point.item.interval_lower_ft) && numeric(point.item.interval_upper_ft)
        ? { lower: Math.max(0, point.y - Number(point.item.interval_lower_ft)), upper: Math.max(0, Number(point.item.interval_upper_ft) - point.y) }
        : null);
      const hasInterval = intervals.some(Boolean);
      traces.push({
        name: modelNames[key], x: points.map(p=>p.x), y: points.map(p=>p.y), mode:'lines+markers',
        line:{color:colors[key],width:key==='persistence'?2.2:1.8,dash:key==='persistence'?'dash':'solid'},
        marker:{size:key==='persistence'?7:6},
        ...(hasInterval ? {error_y:{type:'data',array:intervals.map(v=>v?.upper||0),arrayminus:intervals.map(v=>v?.lower||0),visible:true,color:colors[key],thickness:1,width:3}} : {}),
        customdata:points.map(p=>[issueTime,p.validTime,p.lead]), hovertemplate:'Valid %{customdata[1]}<br>%{y:.2f} ft native stage<br>Effective forecast lead %{customdata[2]:.2f} h<br>Issued %{customdata[0]}<extra>'+modelNames[key]+'</extra>',
        issuance:issueTime
      });
    }
    return traces;
  }
  return { renderGuidance, buildTraces, modelNames, eligibleObservation, observationAtIssue, renderArchiveCycleHealth, renderVerificationOverview };
});
