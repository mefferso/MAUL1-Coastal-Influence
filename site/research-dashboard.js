(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) api.start(root.document, root.fetch.bind(root));
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';

  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const numeric = value => value !== null && value !== '' && Number.isFinite(Number(value));
  const qualityIsUsable = value => {
    if (value == null) return true;
    const flags = Array.isArray(value) ? value.map(item => String(item).trim()) : typeof value === 'string' ? value.split(',').map(item => item.trim()) : null;
    return flags !== null && flags.every(flag => ['', '0', 'P', 'provisional'].includes(flag));
  };
  const fmt = (value, digits=2) => numeric(value) ? Number(value).toFixed(digits) : '—';
  const utc = value => value ? esc(value) : 'time unavailable';
  const safeUrl = value => /^https?:\/\//i.test(String(value || '')) ? String(value) : '';
  const ageHours = (time, now) => {
    const epoch = Date.parse(time);
    return Number.isFinite(epoch) && epoch <= now ? (now - epoch) / 3600000 : null;
  };
  const ageLabel = h => h === null ? 'age unavailable' : h < 1 ? `${Math.round(h*60)} min old` : `${h.toFixed(1)} h old`;
  const freshness = (time, now, maxHours) => {
    const epoch = Date.parse(time);
    if (!Number.isFinite(epoch)) return '<span class="research-status status-unknown">time unavailable</span>';
    if (epoch > now) return '<span class="research-status status-unknown">Future timestamp · freshness unknown</span>';
    const age = (now - epoch) / 3600000;
    return age > maxHours
      ? `<span class="research-status status-stale">Stale · ${ageLabel(age)}</span>`
      : `<span class="research-status status-fresh">Available · ${ageLabel(age)}</span>`;
  };
  const sourceLink = observation => {
    const url = safeUrl(observation?.provenance_url);
    return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(observation.source || 'source record')}</a>` : esc(observation?.source || 'source unavailable');
  };
  const observationCard = ({id, title, descriptor, status, observation, datum, maxAge, change, changeLabel, note, forcedLabel, now=Date.now()}) => {
    let level = 'Observation unavailable';
    let timing = 'No current observation is present in the latest authentic issue.';
    const validObservation = observation && numeric(observation.value);
    if (validObservation) {
      level = `${fmt(observation.value)} ${esc(observation.units || '')}`;
      timing = `Valid ${utc(observation.valid_time_utc)} · retrieved ${utc(observation.retrieved_utc)}`;
    }
    const stamp = validObservation
      ? freshness(observation.valid_time_utc, now, maxAge)
      : `<span class="research-status status-missing">${observation ? 'Invalid observation value' : 'Missing observation'}${status ? ` · ${esc(status)}` : ''}</span>`;
    const statusMarkup = forcedLabel ? `<div class="station-status-stack">${forcedLabel}${stamp}</div>` : stamp;
    const qc = observation?.qc == null ? 'QC unavailable' : `QC ${esc(Array.isArray(observation.qc) ? observation.qc.join(', ') : observation.qc)}`;
    const changeLine = numeric(change) ? `<p class="research-change">${esc(changeLabel)}: <strong>${fmt(change)} ft</strong></p>` : '';
    const source = observation ? sourceLink(observation) : 'Source not available in this issue';
    return `<article class="station-card" aria-labelledby="${id}-title"><div class="station-heading"><div><h3 id="${id}-title">${esc(title)}</h3><p>${esc(descriptor)}</p></div>${statusMarkup}</div><p class="station-level">${level}</p><p class="station-datum">Reference: ${esc(datum)}</p>${changeLine}<p class="station-meta">${timing}</p><p class="station-meta">${source} · ${qc}</p>${note ? `<p class="station-note">${esc(note)}</p>` : ''}</article>`;
  };
  const signedTrend = value => {
    if (!numeric(value)) return 'Trend unavailable';
    const n = Number(value);
    return n > 0 ? `rising ${fmt(n)} ft over 6 h` : n < 0 ? `falling ${fmt(n)} ft over 6 h` : 'no change over 6 h';
  };
  function renderCurrentConditions(record, now=Date.now()) {
    if (!record || record.mode !== 'authentic') return '<p class="research-empty">No authentic prospective issue is available. Current conditions are withheld until an authentic source snapshot is archived.</p>';
    const snap = record.snapshot || {};
    const availability = snap.availability || {};
    const features = snap.features || {};
    const diagnostics = snap.feature_diagnostics || {};
    const den = availability.DENL1 || {};
    const maul = availability.MAUL1_00065 || {};
    const issueEpoch = Date.parse(record.actual_issue_time_utc);
    const directNavdStatus = availability.MAUL1_63160?.status;
    const directNavd = availability.MAUL1_63160?.observation;
    const navdValidEpoch = Date.parse(directNavd?.valid_time_utc);
    const navdRetrievedEpoch = Date.parse(directNavd?.retrieved_utc);
    const navdAge = ageHours(directNavd?.valid_time_utc, now);
    const verifiedNavd = Boolean(directNavdStatus === 'eligible' && directNavd && directNavd.station === 'MAUL1' && directNavd.parameter === 'elevation' && directNavd.parameter_code === '63160' && String(directNavd.datum || '').toUpperCase() === 'NAVD88' && directNavd.units === 'ft' && directNavd.source === 'USGS NWIS IV' && numeric(directNavd.value) && qualityIsUsable(directNavd.qc) && Number.isFinite(issueEpoch) && issueEpoch <= now && Number.isFinite(navdValidEpoch) && Number.isFinite(navdRetrievedEpoch) && navdValidEpoch <= navdRetrievedEpoch && navdRetrievedEpoch <= issueEpoch && navdAge !== null && navdAge <= 2);
    const nwc = availability.NWCL1 || {};
    const mdl = availability.MDLL1 || {};
    const mch = availability.MCHL1 || {};
    const windU = features.nwcl1_wind_u_knots;
    const windV = features.nwcl1_wind_v_knots;
    const resultant = numeric(windU) && numeric(windV) ? Math.hypot(Number(windU), Number(windV)) : null;
    const missing = diagnostics.missing_features || {};
    const residualAvailable = numeric(features.nwcl1_residual_mllw_ft) && !(missing.coastal || []).includes('nwcl1_residual_mllw_ft');
    const mchl = diagnostics.mchl1_shadow || {};
    const mchlChange = mchl.features || {};
    const mchlNote = 'Unverified HADS context. Shadow-only and excluded from frozen model forecasts; relative change does not establish absolute datum or sensor validity.';
    const currentIssueAge = ageHours(record.actual_issue_time_utc, now);
    const issueStatus = !Number.isFinite(issueEpoch)
      ? '<span class="research-status status-unknown">Issue time unavailable</span>'
      : issueEpoch > now
        ? '<span class="research-status status-unknown">Issue timestamp is in the future</span>'
        : currentIssueAge > 3
          ? `<span class="research-status status-stale">Issue archive ${ageLabel(currentIssueAge)}</span>`
          : `<span class="research-status status-fresh">Authentic issue ${utc(record.actual_issue_time_utc)}</span>`;
    const maulThreshold = verifiedNavd
      ? `<p class="datum-gate"><strong>Separate direct NAVD88 observation:</strong> ${fmt(directNavd.value)} ft at ${utc(directNavd.valid_time_utc)} · ${ageLabel(ageHours(directNavd.valid_time_utc,now))} · ${sourceLink(directNavd)} · QC ${esc(Array.isArray(directNavd.qc)?directNavd.qc.join(', '):directNavd.qc ?? 'unavailable')}. Local 4.0 ft NAVD88 threshold difference: ${fmt(Number(directNavd.value)-4)} ft. This does not alter or convert native 00065 stage.</p>`
      : '<p class="datum-gate"><strong>NAVD88 elevation unavailable.</strong> This issue contains native USGS 00065 gage height only. No conversion is applied and the NAVD88 reference line is withheld.</p>';
    const denChange = numeric(features.denl1_log_change_6h) ? (Math.exp(Number(features.denl1_log_change_6h))-1)*100 : null;
    const rows = [
      observationCard({id:'maul1-current',title:'MAUL1 · target',descriptor:'Amite River at Highway 22',status:maul.status,observation:maul.observation,datum:'Native USGS 00065 gage height; not NAVD88',maxAge:2,change:features.maul1_change_6h_ft,changeLabel:'Recent native-stage change',note:'Forecast anchor changes describe model inputs and are not a second observation.',now}),
      observationCard({id:'denl1-current',title:'DENL1 · upstream river',descriptor:'USGS 07378500 discharge',status:den.status,observation:den.observation,datum:'Discharge in cfs; separate native gage height is not shown here',maxAge:3,note:numeric(denChange)?`Frozen-input 6 h log-discharge change corresponds to about ${fmt(denChange,1)}%; not a MAUL1 event classification.`:'Recent discharge trend unavailable.',now}),
      observationCard({id:'nwcl1-current',title:'NWCL1 · lake and wind',descriptor:'Lake Pontchartrain · CO-OPS 8761927',status:nwc.status,observation:nwc.observation,datum:'Water level in MLLW; no cross-station stage comparison',maxAge:3,note:`Wind-vector resultant from model inputs: ${resultant===null?'unavailable':`${fmt(resultant,1)} knots`}. Time-matched observed-minus-predicted residual: ${residualAvailable?'available':'unavailable'}; no residual screen is assigned without it.`,now}),
      observationCard({id:'mdll1-current',title:'MDLL1 · independent lake gauge',descriptor:'USGS 301200090072400',status:mdl.status,observation:mdl.observation,datum:'Native USGS gage height; datum not equated to NWCL1 MLLW',maxAge:3,change:features.mdll1_stage_change_6h_ft,changeLabel:'Recent native-stage change',now}),
      observationCard({id:'mchl1-current',title:'MCHL1 · Pass Manchac',descriptor:'HADS DCP CE678A12 · shadow context',status:mch.status,observation:mch.observation,datum:'Native reference unverified; relative changes only',maxAge:3,change:mchlChange.mchl1_stage_change_6h_native_ft,changeLabel:'Shadow 6 h stage change',forcedLabel:'<span class="research-status status-shadow">Unverified · shadow-only</span>',note:mchlNote,now})
    ].join('');
    const coastalState = residualAvailable ? 'Residual input present, but the complete frozen six-hour evidence screen is not calculated in this issue.' : 'Incomplete: a same-time observed/predicted residual is unavailable; wind context alone is not a coastal screen.';
    const riverState = den.observation ? `DENL1 discharge observation available${numeric(denChange)?` with about ${fmt(denChange,1)}% model-input change over 6 h`:''}. This is upstream context, not attribution at MAUL1.` : 'DENL1 discharge unavailable in this issue.';
    return `<div class="research-issue-row">${issueStatus}<span>Model feature anchor: ${utc(record.model_anchor_time_utc || diagnostics.model_anchor_utc || 'unavailable')}</span></div><p class="research-assessment"><strong>Current observational assessment: indeterminate.</strong> These issue inputs are context only; no coastal/river evidence classification or causal attribution is computed.</p><div class="station-grid">${rows}</div><section class="evidence-context" aria-label="Observational evidence context"><h3>Evidence context · not attribution</h3><dl><dt>Coastal-supporting screen</dt><dd>${esc(coastalState)}</dd><dt>River-supporting context</dt><dd>${esc(riverState)}</dd><dt>Simultaneous evidence</dt><dd>Not assessed: the issue record does not run the complete Phase 4 screens across a shared valid-time window.</dd><dt>Classification</dt><dd>Indeterminate until screen inputs and coverage are sufficient; screens do not establish cause.</dd></dl></section>${maulThreshold}<p class="research-footnote">Freshness is recalculated from observation valid time when this page is viewed. Source QC and retrieval times are shown when recorded. The compact archive is an issuance snapshot, not a continuous live gauge feed.</p>`;
  }
  async function start(document, fetcher) {
    const target = document.getElementById('research-current');
    if (!target) return;
    target.innerHTML = '<p class="research-empty">Loading the latest authentic source snapshot…</p>';
    try {
      const latestResponse = await fetcher('data/prospective/latest.json');
      if (!latestResponse.ok) throw new Error('Latest issue unavailable');
      const latest = await latestResponse.json();
      let record = latest;
      if (latest.mode === 'authentic') {
        const indexResponse = await fetcher('data/prospective/history/index.json');
        if (indexResponse.ok) {
          const entries = await indexResponse.json();
          const entry = (Array.isArray(entries) ? entries : []).find(item => item.mode === 'authentic' && item.issuance_id === latest.issuance_id);
          if (entry?.forecast_file) {
            const fullResponse = await fetcher(`data/prospective/history/${entry.forecast_file}`);
            if (fullResponse.ok) record = await fullResponse.json();
          }
        }
      }
      target.innerHTML = renderCurrentConditions(record);
    } catch (_) {
      target.innerHTML = '<p class="research-empty">Prospective source snapshot is unavailable. No current value is inferred from historical charts.</p>';
    }
  }
  return {renderCurrentConditions, start};
});
