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
  const validNative = record => record?.mode === 'authentic' && numeric(record.latest_maul1_native_stage_ft) &&
    nativeDatum(record.datum) && nativeDatum(record.stage_datum) &&
    Number.isFinite(Date.parse(record.actual_issue_time_utc)) && Date.parse(record.actual_issue_time_utc) <= Date.now();
  const forecastDatumIsNative = forecast => nativeDatum(forecast?.datum);
  const forecastChronologyIsValid = (record, forecast) => { const issue=Date.parse(record?.actual_issue_time_utc), valid=Date.parse(forecast?.valid_time_utc); return Number.isFinite(issue) && Number.isFinite(valid) && valid >= issue; };
  const qcIsUsable = value => { if(value==null)return true; const flags=Array.isArray(value)?value.map(x=>String(x).trim()):typeof value==='string'?value.split(',').map(x=>x.trim()):null; return flags!==null && flags.every(x=>['','0','P','provisional'].includes(x)); };
  function renderGuidance(record) {
    if (!validNative(record)) return '<p class="research-empty">No compatible authentic native-stage issuance is available for forecast guidance.</p>';
    const cards = horizons.map(horizon => {
      const forecast = record.forecasts?.[String(horizon)];
      if (!forecast || !forecastDatumIsNative(forecast) || !forecastChronologyIsValid(record, forecast)) return `<article class="horizon-card"><h3>${horizon}-hour guidance</h3><p>Forecast horizon unavailable in this authentic issue.</p></article>`;
      const persistence = forecast.models?.persistence;
      const candidates = modelOrder.map(key => forecast.models?.[key]).filter(item => item?.status === 'issued' && numeric(item.predicted_stage_native_ft));
      const values = candidates.map(item => Number(item.predicted_stage_native_ft));
      const spread = values.length ? `${Math.min(...values).toFixed(2)}–${Math.max(...values).toFixed(2)} ft` : 'unavailable';
      const details = Object.entries(modelNames).map(([key, name]) => {
        const item = forecast.models?.[key];
        if (!item || item.status !== 'issued') return `<tr><th>${name}</th><td colspan="3">Unavailable for this issue</td></tr>`;
        const interval = numeric(item.interval_lower_ft) && numeric(item.interval_upper_ft)
          ? `${ft(item.interval_lower_ft)}–${ft(item.interval_upper_ft)} · archived interval`
          : 'Not calibrated / unavailable';
        return `<tr><th>${name}</th><td>${ft(item.predicted_stage_native_ft)}</td><td>${numeric(item.predicted_change_ft) ? `${Number(item.predicted_change_ft) >= 0 ? '+' : ''}${ft(item.predicted_change_ft)}` : '—'}</td><td>${interval}</td></tr>`;
      }).join('');
      const lead = numeric(forecast.effective_lead_hours) ? `${Number(forecast.effective_lead_hours).toFixed(1)} h effective lead` : `${horizon} h nominal lead`;
      return `<article class="horizon-card"><div class="horizon-heading"><h3>${horizon}-hour guidance</h3><span>${lead}</span></div><p class="valid-time">Valid ${esc(forecast.valid_time_utc || 'time unavailable')}</p><p class="persistence-value">Persistence <strong>${persistence?.status === 'issued' ? ft(persistence.predicted_stage_native_ft) : 'unavailable'}</strong></p><p class="model-spread">Available model outputs span <strong>${spread}</strong> across ${candidates.length} model(s). This is model spread, not an uncertainty interval.</p><details><summary>Compare model guidance</summary><div class="table-wrap" role="region" tabindex="0" aria-label="${horizon}-hour model guidance"><table><thead><tr><th>Model</th><th>Native stage</th><th>Change</th><th>Interval</th></tr></thead><tbody>${details}</tbody></table></div></details></article>`;
    }).join('');
    return `<div class="forecast-issue-meta">Authentic issue ${esc(record.actual_issue_time_utc || 'time unavailable')} · Anchor ${ft(record.latest_maul1_native_stage_ft)} native USGS 00065 gage height</div><div class="horizon-grid">${cards}</div><p class="no-preferred-model"><strong>No preferred model has been established.</strong> Current prospective verification has too few independent rising-water events to rank models reliably.</p>`;
  }
  function buildTraces(record) {
    if (!validNative(record)) return [];
    const issueTime = record.actual_issue_time_utc;
    const anchor = Number(record.latest_maul1_native_stage_ft);
    const traces = [];
    const eligible = horizons.map(h => [h, record.forecasts?.[String(h)]]).filter(([, f]) => f && forecastDatumIsNative(f) && forecastChronologyIsValid(record, f));
    const observation=record.snapshot?.availability?.MAUL1_00065?.observation;
    const observationStatus=record.snapshot?.availability?.MAUL1_00065?.status;
    const observationValid=Date.parse(observation?.valid_time_utc), observationRetrieved=Date.parse(observation?.retrieved_utc), issueEpoch=Date.parse(issueTime), anchorEpoch=Date.parse(record.model_anchor_time_utc);
    if(observationStatus==='eligible' && observation && observation.station==='MAUL1' && observation.parameter==='stage' && observation.source==='USGS NWIS IV' && observation.units==='ft' && nativeDatum(observation.datum) && numeric(observation.value) && qcIsUsable(observation.qc) && Number.isFinite(observationValid) && Number.isFinite(observationRetrieved) && Number.isFinite(anchorEpoch) && observationValid<=observationRetrieved && observationRetrieved<=issueEpoch && observationValid<=issueEpoch && issueEpoch<=Date.now() && Date.now()-observationValid<=2*3600000) {
      traces.push({name:'Latest observation · USGS 00065',x:[(observationValid-anchorEpoch)/3600000],y:[Number(observation.value)],mode:'markers',marker:{color:'#12303c',size:10,symbol:'diamond'},hovertemplate:'Observed %{y:.2f} ft native stage<br>Valid '+observation.valid_time_utc+'<br>Retrieved '+observation.retrieved_utc+'<extra>Latest observation</extra>',issuance:issueTime});
    }
    const perModel = key => eligible.map(([horizon, forecast]) => {
      const item = forecast.models?.[key];
      const lead = numeric(forecast.effective_lead_hours) ? Number(forecast.effective_lead_hours) : horizon;
      return item?.status === 'issued' && numeric(item.predicted_stage_native_ft) && Number.isFinite(lead) && lead >= 0
        ? { x: lead, y: Number(item.predicted_stage_native_ft), item, validTime: forecast.valid_time_utc }
        : null;
    }).filter(Boolean);
    const colors = {persistence:'#697b80',phase5a_maul1_only:'#287a8d',phase5a_coastal:'#99558c',phase5b_coastal_tidal:'#ca7a36',phase5b_full_multivariable:'#496d4c'};
    for (const key of ['persistence', ...modelOrder]) {
      const points = [{x:0,y:anchor,item:null,validTime:record.model_anchor_time_utc || issueTime}, ...perModel(key)];
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
        customdata:points.map(p=>[issueTime,p.validTime]), hovertemplate:'Valid %{customdata[1]}<br>%{y:.2f} ft native stage<br>Issued %{customdata[0]}<extra>'+modelNames[key]+'</extra>',
        issuance:issueTime
      });
    }
    return traces;
  }
  return { renderGuidance, buildTraces, modelNames };
});
