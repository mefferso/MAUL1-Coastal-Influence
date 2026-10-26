(function (scope) {
  'use strict';
  const MODEL_ORDER = ['persistence','phase5a_maul1_only','phase5a_coastal','phase5b_coastal_tidal','phase5b_full_multivariable'];
  const HORIZONS = [6,12,24];
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const finite = value => value != null && Number.isFinite(Number(value));
  const compareText=(a,b)=>String(a??'')<String(b??'')?-1:String(a??'')>String(b??'')?1:0;
  const revisionOrder=(a,b)=>compareText(a?.issuance_id,b?.issuance_id)||Number(a?.horizon_hours||0)-Number(b?.horizon_hours||0)||compareText(a?.model,b?.model)||Number(a?.revision||0)-Number(b?.revision||0)||compareText(a?.observation_valid_time_utc,b?.observation_valid_time_utc)||Number(a?.observed_native_stage_ft||0)-Number(b?.observed_native_stage_ft||0)||Number(a?.predicted_native_stage_ft||0)-Number(b?.predicted_native_stage_ft||0);
  const range = values => {
    const valid = values.filter(finite).map(Number);
    return valid.length ? {min:Math.min(...valid),max:Math.max(...valid)} : null;
  };
  const rangeText = value => !value ? 'not recorded' : value.min === value.max ? String(value.min) : `${value.min}–${value.max}`;
  const fmt = value => finite(value) ? Number(value).toFixed(3) : '—';
  const key = (issue,horizon,model) => `${issue}|${Number(horizon)}|${model}`;
  function latestVerificationRows(revisions, authenticIds) {
    const latest = new Map();
    for (const row of [...(revisions || [])].sort(revisionOrder)) {
      if (!row || !row.issuance_id || (authenticIds && !authenticIds.has(row.issuance_id)) || !finite(row.horizon_hours) || !row.model) continue;
      if (!finite(row.predicted_native_stage_ft) || !finite(row.observed_native_stage_ft) || !row.observation_valid_time_utc) continue;
      const id=key(row.issuance_id,row.horizon_hours,row.model), previous=latest.get(id);
      if (!previous || Number(row.revision || 0) > Number(previous.revision || 0)) latest.set(id,row);
    }
    return new Map([...latest.entries()].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0));
  }
  function stats(errors) {
    return errors.length ? {
      n:errors.length,
      maeFt:errors.reduce((sum,x)=>sum+Math.abs(x),0)/errors.length,
      rmseFt:Math.sqrt(errors.reduce((sum,x)=>sum+x*x,0)/errors.length),
      biasFt:errors.reduce((sum,x)=>sum+x,0)/errors.length,
    } : {n:0,maeFt:null,rmseFt:null,biasFt:null};
  }
  function pairedComparisons(report, revisions, authenticIds) {
    const latest=latestVerificationRows(revisions,authenticIds), ordered=[...latest.values()].sort((a,b)=>key(a.issuance_id,a.horizon_hours,a.model)<key(b.issuance_id,b.horizon_hours,b.model)?-1:1), persistence=new Map(), groups=new Map();
    for (const row of ordered) if (row.model==='persistence') persistence.set(key(row.issuance_id,row.horizon_hours,'persistence'),row);
    for (const row of ordered) {
      const horizon=Number(row.horizon_hours), baseline=persistence.get(key(row.issuance_id,horizon,'persistence'));
      if (!baseline || baseline.observation_valid_time_utc!==row.observation_valid_time_utc || Number(baseline.observed_native_stage_ft)!==Number(row.observed_native_stage_ft)) continue;
      const groupKey=`${row.model}:${horizon}h`;
      if (!groups.has(groupKey)) groups.set(groupKey,{model:row.model,horizon,modelErrors:[],persistenceErrors:[]});
      const group=groups.get(groupKey), observed=Number(row.observed_native_stage_ft);
      group.modelErrors.push(Number(row.predicted_native_stage_ft)-observed);
      group.persistenceErrors.push(Number(baseline.predicted_native_stage_ft)-observed);
    }
    const metrics=report?.model_horizon_metrics || {};
    return [...groups.values()].map(group=>{
      const modelStats=stats(group.modelErrors), persistenceStats=stats(group.persistenceErrors),
        metric=metrics[`${group.model}:${group.horizon}h`], rise=metric?.rises?.['0.50'], event=group.horizon===24?metric?.qualifying_24h_events:null;
      return {model:group.model,horizon:group.horizon,pairedN:modelStats.n,modelStats,persistenceStats,
        delta:{maeFt:modelStats.maeFt-persistenceStats.maeFt,rmseFt:modelStats.rmseFt-persistenceStats.rmseFt,biasFt:modelStats.biasFt-persistenceStats.biasFt},
        falseAlarmPairs:finite(rise?.false_alarms)?Number(rise.false_alarms):null,
        pairMisses:finite(rise?.misses)?Number(rise.misses):null,
        eventGroups:finite(event?.event_count)?Number(event.event_count):null,
        eventStatus:event?.status || 'not_computed',
        eventMisses:event?.status==='computed' && finite(event?.missed_events)?Number(event.missed_events):null};
    }).sort((a,b)=>HORIZONS.indexOf(a.horizon)-HORIZONS.indexOf(b.horizon) || MODEL_ORDER.indexOf(a.model)-MODEL_ORDER.indexOf(b.model));
  }
  function summarizeReadiness(history, report, latest, gates, revisions) {
    const authentic=(Array.isArray(history)?history:[]).filter(row=>row?.mode==='authentic');
    const completeness=report?.verification_completeness || {}, metrics=report?.model_horizon_metrics || {};
    const horizons=HORIZONS.map(horizon=>{
      const entries=MODEL_ORDER.map(model=>completeness[`${model}:${horizon}h`]).filter(Boolean);
      const slots=range(entries.map(x=>x.forecast_slots)), matured=range(entries.map(x=>x.matured)), verified=range(entries.map(x=>x.verified)),
        notDue=range(entries.map(x=>x.not_yet_due));
      return {horizon,modelCount:entries.length,issueTargetSlots:slots?.min??0,slotRange:slots,maturedSlots:matured,verifiedPerModel:verified,
        dueUnverifiedModelPairs:entries.reduce((sum,x)=>sum+Number(x.due_unverified||0),0),
        notYetDueModelPairs:entries.reduce((sum,x)=>sum+Number(x.not_yet_due||0),0),
        abstainedModelSlots:entries.reduce((sum,x)=>sum+Number(x.abstained||0),0),
        unavailableModelSlots:entries.reduce((sum,x)=>sum+Number(x.other_unavailable||0),0),
        latency:metrics[`persistence:${horizon}h`]?.observation_latency_minutes || null};
    });
    const eventReports=MODEL_ORDER.map(model=>metrics[`${model}:24h`]?.qualifying_24h_events).filter(Boolean);
    const eventCounts=range(eventReports.map(x=>x.event_count));
    const eventComputed=eventReports.some(x=>x.status==='computed');
    const thresholds=gates?.thresholds || {};
    const minimumPairs=finite(thresholds.minimum_verified_issue_target_pairs_per_horizon)?Number(thresholds.minimum_verified_issue_target_pairs_per_horizon):null;
    const minimumEvents=finite(thresholds.minimum_predeclared_rise_groups)?Number(thresholds.minimum_predeclared_rise_groups):null;
    const volumeMet=minimumPairs!=null && horizons.every(h=>h.verifiedPerModel && h.verifiedPerModel.min>=minimumPairs);
    const groupsMet=minimumEvents!=null && eventCounts && eventCounts.min>=minimumEvents;
    const approval=gates?.owner_approval || {};
    const approvalTime=Date.parse(approval.approved_at_utc || ''), evaluationTime=Date.parse(report?.evaluation_time_utc || '');
    const approved=approval.status==='approved' && Boolean(String(approval.approved_by||'').trim()) && Number.isFinite(approvalTime) && (!Number.isFinite(evaluationTime) || approvalTime<=evaluationTime);
    const authenticIds=new Set(authentic.map(row=>row.issuance_id));
    const comparisons=pairedComparisons(report,revisions,authenticIds);
    const sources=Object.entries(latest?.snapshot?.availability || {}).map(([name,value])=>({name,status:value?.status || 'not recorded',ageHours:finite(value?.age_hours)?Number(value.age_hours):null})).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0);
    return {
      authenticIssuanceCount:authentic.length,
      evaluationTimeUtc:report?.evaluation_time_utc || null,
      latestActualIssueTimeUtc:latest?.actual_issue_time_utc || null,
      latestFeatureAnchorTimeUtc:latest?.feature_anchor_time_utc || latest?.model_anchor_time_utc || null,
      horizons,comparisons,sources,
      eventReadiness:{thresholdFt:0.5,windowHours:24,groupSeparationHours:24,eventGroupCount:eventCounts?.min??0,eventGroupRange:eventCounts,
        status:eventComputed?'computed':'insufficient_independent_events',eventMisses:eventComputed?eventReports.map(x=>x.missed_events).filter(finite):null},
      falseAlertEpisodes:{status:'not_computed',reason:'Existing outputs count issue-target false-alarm pairs; no predeclared alert-episode grouping is stored.'},
      gateApproval:{status:approved?'approved':'pending',approvedBy:approved?approval.approved_by:null,approvedAtUtc:approved?approval.approved_at_utc:null},
      gateAssessment:{minimumPairs,minimumEvents,volumeMet,groupsMet,status:volumeMet&&groupsMet?'sample_counts_met':'insufficient_sample_counts',
        underSampledHorizons:horizons.filter(h=>minimumPairs!=null&&(!h.verifiedPerModel||h.verifiedPerModel.min<minimumPairs)).map(h=>h.horizon)},
      gates:thresholds,
      challengerEvaluation:'not_run_frozen_models_are_controls',
    };
  }
  function renderReadiness(summary) {
    if (!summary) return '<section class="phase6-readiness research-empty" aria-label="Prospective evidence readiness">Evidence readiness summary unavailable.</section>';
    const assessment=summary.gateAssessment, gates=summary.gates || {};
    const status=assessment.status==='insufficient_sample_counts'?'INSUFFICIENT FOR CHALLENGER PROMOTION':'SAMPLE COUNTS MEET PROPOSED MINIMUMS';
    const issueAge=age=>finite(age)?`${Number(age).toFixed(2)} h at latest issue`:'age not recorded';
    const horizonRows=summary.horizons.map(h=>`<tr><th>${h.horizon} h</th><td>${rangeText(h.slotRange)}</td><td>${rangeText(h.maturedSlots)}</td><td>${rangeText(h.verifiedPerModel)}</td><td>${h.dueUnverifiedModelPairs}</td><td>${h.notYetDueModelPairs}</td><td>${h.latency?.median==null?'not recorded':`${Number(h.latency.median).toFixed(0)} min median; ${finite(h.latency.p90)?`${Number(h.latency.p90).toFixed(0)} min P90`:''}`}</td></tr>`).join('');
    const comparisonRows=summary.comparisons.map(row=>{const eventText=row.horizon!==24?'not grouped':row.eventStatus==='computed'?`${row.eventMisses} event misses`:row.eventStatus==='insufficient_independent_events'&&row.eventGroups!=null?`${row.eventGroups} groups; withheld (<5)`:'not available';return `<tr><th>${escapeHtml(row.model.replaceAll('_',' '))} / ${row.horizon} h</th><td>${row.pairedN}</td><td>${fmt(row.modelStats.maeFt)} / ${fmt(row.persistenceStats.maeFt)} / ${fmt(row.delta.maeFt)}</td><td>${fmt(row.modelStats.rmseFt)} / ${fmt(row.persistenceStats.rmseFt)} / ${fmt(row.delta.rmseFt)}</td><td>${fmt(row.modelStats.biasFt)} / ${fmt(row.persistenceStats.biasFt)} / ${fmt(row.delta.biasFt)}</td><td>${row.falseAlarmPairs==null?'not recorded':row.falseAlarmPairs} pairs</td><td>${eventText}</td></tr>`;}).join('');
    const sourceRows=summary.sources.map(source=>`<li><strong>${escapeHtml(source.name)}</strong>: ${escapeHtml(source.status)} · ${escapeHtml(issueAge(source.ageHours))}</li>`).join('');
    const gateLines=[
      [`Verified issue-target pairs per horizon`,gates.minimum_verified_issue_target_pairs_per_horizon],
      [`Predeclared ≥0.50-ft rise groups`,gates.minimum_predeclared_rise_groups],
      [`Minimum MAE improvement vs each baseline`,finite(gates.minimum_mae_improvement_fraction_vs_each_baseline)?`${(100*Number(gates.minimum_mae_improvement_fraction_vs_each_baseline)).toFixed(0)}%`:null],
      [`Paired block-interval confidence`,finite(gates.paired_block_interval_confidence)?`${(100*Number(gates.paired_block_interval_confidence)).toFixed(0)}%`:null],
      [`Maximum absolute bias`,finite(gates.maximum_absolute_bias_ft)?`${Number(gates.maximum_absolute_bias_ft).toFixed(2)} ft`:null],
      [`Maximum RMSE regression vs best baseline`,finite(gates.maximum_rmse_regression_fraction_vs_best_baseline)?`${(100*Number(gates.maximum_rmse_regression_fraction_vs_best_baseline)).toFixed(0)}%`:null],
      [`Minimum cases per availability stratum`,gates.minimum_pairs_per_availability_stratum],
      [`Maximum stratum MAE regression`,finite(gates.maximum_mae_regression_fraction_within_strata)?`${(100*Number(gates.maximum_mae_regression_fraction_within_strata)).toFixed(0)}%`:null],
      [`80% interval coverage target`,finite(gates.interval_coverage_target)?`${(100*Number(gates.interval_coverage_target)).toFixed(0)}%`:null],
      [`Interval coverage tolerance / minimum pairs`,finite(gates.interval_coverage_tolerance)?`±${(100*Number(gates.interval_coverage_tolerance)).toFixed(0)} points / ${gates.minimum_interval_pairs??'not set'}`:null],
    ].filter(row=>row[1]!=null).map(row=>`<li>${escapeHtml(row[0])}: <strong>${escapeHtml(row[1])}</strong></li>`).join('');
    const currentGroup=summary.eventReadiness.eventGroupRange ? rangeText(summary.eventReadiness.eventGroupRange) : 'not available';
    const approvedText=summary.gateApproval.status==='approved'?`Approved by ${escapeHtml(summary.gateApproval.approvedBy)} at ${escapeHtml(summary.gateApproval.approvedAtUtc)}`:'Owner approval required; proposed thresholds are inactive.';
    return `<section class="phase6-readiness" aria-labelledby="phase6-readiness-title"><div class="phase6-readiness-heading"><div><p class="phase6-readiness-kicker">AUTHENTIC PROSPECTIVE EVIDENCE</p><h3 id="phase6-readiness-title">Evidence readiness</h3></div><span class="phase6-readiness-status">${status}</span></div><p class="phase6-readiness-alert"><strong>Research / shadow only.</strong> These are authentic prospective issue-target pairs, separate from retrospective Phase 5 hindcasts. Forecast windows overlap; pair counts are not independent samples or storms. Summary as of ${escapeHtml(summary.evaluationTimeUtc||'not recorded')}. The immutable first issue retains the Phase 6.16 +53m11s timing erratum; no historical issue is retimed. MAUL1 00065 is native gage height; only verified direct 63160 is NAVD88-comparable.</p><p class="phase6-readiness-meta">Authentic issuances: <strong>${summary.authenticIssuanceCount}</strong> · Latest actual issuance: <strong>${escapeHtml(summary.latestActualIssueTimeUtc||'not recorded')}</strong> · Feature anchor: <strong>${escapeHtml(summary.latestFeatureAnchorTimeUtc||'not recorded')}</strong></p><div class="phase6-readiness-grid"><article><h4>Maturity and paired evidence</h4><div class="table-wrap" role="region" tabindex="0" aria-label="Prospective target maturity by horizon"><table><thead><tr><th>Horizon</th><th>Issued target slots</th><th>Matured targets by model</th><th>Verified pairs per model</th><th>Due unverified model-pairs</th><th>Not yet due model-pairs</th><th>Observation capture delay</th></tr></thead><tbody>${horizonRows}</tbody></table></div><p class="phase6-readiness-note">Ranges show the minimum–maximum across five models. Due-unverified and not-yet-due totals sum model-target pairs. Target-time windows overlap across issues and are not independent evidence.</p></article><article><h4>Latest issue input availability</h4><ul class="phase6-readiness-sources">${sourceRows||'<li>Source availability not recorded.</li>'}</ul><p class="phase6-readiness-note">Age is the archived input age at the latest authentic issue. Observation capture delay is verification observation valid time to recorded ingestion time; it is not source-specific latency.</p></article></div><article><h4>Paired model versus persistence errors (ft)</h4><div class="table-wrap" role="region" tabindex="0" aria-label="Exact paired model versus persistence errors"><table><thead><tr><th>Model / horizon</th><th>Paired N</th><th>MAE: model / persistence / Δ</th><th>RMSE: model / persistence / Δ</th><th>Bias: model / persistence / Δ</th><th>0.50-ft false alarms</th><th>Observed event misses</th></tr></thead><tbody>${comparisonRows||'<tr><td colspan="7">No exact paired prospective comparisons are available.</td></tr>'}</tbody></table></div><p class="phase6-readiness-note">Pairs require the same authentic issuance, horizon, observation valid time, and observed value for the model and persistence forecast. Δ is model minus persistence; negative MAE/RMSE is lower error. False alarms are issue-target pairs, not false-alert episodes. Episode counts are not computed because no predeclared episode grouping is stored.</p></article><div class="phase6-readiness-event"><h4>Predeclared substantial-rise evidence</h4><p>Observed native-stage rise ≥0.50 ft over a 24-hour target window; qualifying target windows separated by no more than 24 hours use the existing group rule. Current grouped outcomes: <strong>${escapeHtml(currentGroup)} group${summary.eventReadiness.eventGroupCount===1?'':'s'}</strong>. These are outcome-defined independent event groups under the existing target-window rule; grouping does not establish physical or statistical independence. ${summary.eventReadiness.eventGroupCount<5?'Event detection and significant-rise miss counts remain suppressed below the existing five-group minimum.':'Event counts follow the existing metric output; these outcome-defined groups are not physical onset times or proof of independence.'}</p><p>False-alert episodes: <strong>not computed</strong>. The archived evaluation supports pairwise false-alarm counts only. No event misses are inferred while the five-group suppression rule applies.</p></div><article><h4>Proposed future challenger-readiness gates</h4><p><strong>${approvedText}</strong> Current gate status: ${assessment.status==='insufficient_sample_counts'?'insufficient sample counts': 'sample-count minimums met; other evaluation criteria remain'}. These configurable criteria are research-readiness checks, not evidence of validated operational performance. Frozen Phase 5 models remain controls; no challenger is being tested.</p><ul class="phase6-readiness-gates">${gateLines||'<li>Proposed thresholds are not configured.</li>'}</ul><p class="phase6-readiness-note">Passing sample-volume gates does not establish independent skill or authorize model promotion. Paired uncertainty, robustness, missingness, and interval-coverage checks must also be completed on a separately reviewed prospective shadow evaluation.</p><p class="phase6-readiness-note"><a href="https://github.com/mefferso/MAUL1-Coastal-Influence/blob/main/docs/phase6-17-evidence-readiness.md">Phase 6.17 evidence definitions and gate rationale</a></p></article></section>`;
  }
  async function loadVerificationRevisions(history, fetcher=fetch) {
    const paths=[...new Set((Array.isArray(history)?history:[]).filter(x=>x?.mode==='authentic').flatMap(x=>x.verification_files||[]))];
    const rows=[]; let next=0;
    const worker=async()=>{ while(next<paths.length){const path=paths[next++];try{const response=await fetcher(`data/prospective/history/${path}`);if(!response.ok)continue;const data=await response.json();rows.push(...(data.revisions||[]));}catch(_){/* unavailable evidence stays missing */}}};
    await Promise.all(Array.from({length:Math.min(8,paths.length)},worker));
    return rows.sort(revisionOrder);
  }
  const api={summarizeReadiness,renderReadiness,loadVerificationRevisions,pairedComparisons};
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  if (scope) scope.MAUL1EvidenceReadiness=api;
})(typeof window!=='undefined'?window:null);
