"""Readable scientific reports from Phase 4 machine-readable evidence."""
import json


def table_counts(values):
    lines=['| Evidence class | Count |','|---|---:|']
    lines += [f'| {key} | {value} |' for key,value in values.items()]
    return lines


def render_report(s,p,ind,cases):
    lines=['# Phase 4 — observation-based evidence evaluation','',
           '**Experimental retrospective evidence, not hydrodynamic attribution, forecast skill or operational guidance.**','',
           '## Scope and provenance','',
           f"Evaluated the frozen {s['event_count']} meaningful native-stage MAUL1 response events and {s['control_count']} eligible seven-day nonresponse controls from Phase 3B. No observations were downloaded or earlier products replaced. Input SHA-256 hashes, thresholds and calibration distributions are in `provenance.json`. Base repository commit: `{p['base_repository_commit']}`.",'',
           'The five-station identities are preserved. DENL1 discharge supports the upstream pathway; NWCL1 same-hour/same-datum residual, independent MDLL1 native change and wind vector coherence support the coastal pathway. MCHL1 remains optional supporting context with explicit quality and datum uncertainty. No USACE substitution is made. Historical MAUL1 00065 is never converted to NAVD88; the established 4.0-ft NAVD88 threshold is not evaluated in Phase 4.','',
           '## Frozen physical screening hypotheses','',
           'See `methodology.md` for precise windows, units, logic and physical justifications. Thresholds are provisional evidence screens, not fitted event labels. A signal must persist through six completed hourly bins. Missing evidence and observed failure to meet a screen remain separate. A supported pathway can coexist with unavailable evidence for the other pathway; the class is never exclusive attribution.','',
           '```json',json.dumps(p['thresholds'],indent=2,sort_keys=True),'```','',
           '## Response events','']+table_counts(s['event_counts'])
    lines += ['',f"Indeterminate: {s['indeterminate_event_fraction']:.1%}. Evidence coverage qualified for {s['coverage_qualified_events']}/{s['event_count']} events (all four core flags known for at least 90% of assessed hours). This is temporal evidence availability, not a confidence score. Coverage-qualified class counts:",'']+table_counts(s['coverage_qualified_event_counts'])
    lines += ['',f"{s['events_without_supported_path']} MAUL1 events lack either supported pathway. Both pathways appear in {s['events_with_both_paths']} events; {s['sequential_signal_events']} contain disjoint signals without simultaneous support and remain indeterminate. A compound label represents coexisting signals, not demonstrated nonlinear interaction. Long excursions can collect unrelated later forcing; their explicit flags must accompany interpretation.",'',
              '## Independent nonresponse controls','']+table_counts(s['control_counts'])
    lines += ['',f"{s['coverage_qualified_controls']}/{s['control_count']} controls meet Phase 4 evidence coverage. {s['controls_with_forcing_evidence']} controls contain qualifying forcing support without a meaningful MAUL1 event under the frozen catalogue. These are observational nonresponses, not false forecast alarms. The selection excludes event buffers and uses >=90% coverage in four core water series; wind was not a Phase 3B control eligibility requirement.",'',
              'Control category memberships overlap. The prior category called elevated_lake_without_qualifying_response was selected from MAUL1 median native stage, not direct lake setup; Phase 4 independently assesses actual lake signals instead of accepting that name as truth.','']
    for name,values in s['controls_by_original_category'].items():
        lines += [f'- {name}: '+', '.join(f'{k} {v}' for k,v in values.items())]
    lines += ['', 'The Phase 3B archive contains zero eligible controls meeting its >=50,000-cfs upstream-increase category. Phase 4 can find smaller discharge signals, but does not manufacture a robust large-flow nonresponse sample.','',
              '## Rule sensitivity','',
              '| Variant | River | Coastal | Compound | Indeterminate | Changed events |','|---|---:|---:|---:|---:|---:|']
    for name,v in s['sensitivity'].items():
        c=v['event_counts'];lines.append(f"| {name} | {c['River-supported']} | {c['Coastal-supported']} | {c['Compound-supported']} | {c['Indeterminate']} | {v['changed_events']} |")
    lines += ['', 'Magnitudes change together by ±25%, wind transport axes span 240–300° toward the western lake, and coastal antecedent windows span 6–36 hours. These are fixed stress tests rather than optimization. They do not exhaust uncertainty in persistence, baseline, river travel times, thresholds or the Phase 3B event definition. Event-definition sensitivity remains in the preserved Phase 3B reports.','',
              '## Temporal split and independence','',
              f"Fixed 2023-01-01 boundary and 72-hour embargo remain. Phase 4 checks full feature history (78h before the assessment start) and observed event recovery; {len(ind['changes_from_original_split'])} records change split status compared with the original assignment. {ind['count']} record pairs have overlapping feature histories and cannot be treated as independent statistical trials. All pair IDs are in `independence.json`.",'',
              ind['limitation'],'',
              'Per-subset evidence counts (these are descriptive classifications, not accuracy):','',
              '```json',json.dumps(s['counts_by_subset'],indent=2),'```','',
              '## Retrospective versus issue-time assessment','',
              f"The separate replay contains {s['replay']['snapshot_count']} issue assessments: event offsets -24, 0, +12, +24h, control endpoints and fixed six-hour case clocks. {s['replay']['event_snapshot_differences']}/{s['replay']['event_snapshot_count']} event snapshots differ from the eventual retrospective category. These differences measure evolving evidence, not errors or warning lead time.",'',
              s['replay']['availability'],'',
              'Each assessment excludes unfinished bins, uses only trailing features and never reads event peaks, subsequent observations or centered event smoothing. The preserved Phase 3B retrospective catalogue itself uses centered smoothing and full recovery information; its event-conditioned replay sampling is not a real-time event detector. Replay recalculates the discharge upper decile from calibration-era bins completed before each issue and freezes it at the pre-2023 seam; a fixed 20,000-cfs screen applies before 1,000 prior valid hours. Replay ignores future-dependent archived adaptive QC and uses fixed causal hourly jump screens on newly completed endpoints. Parameter sample size and cutoff are recorded per assessment. This remains a research reconstruction, not a model that existed at those dates.','',
              '## Priority case findings','']
    for c in cases:
        event_text='; '.join(f"{e['record_id']}: {e['category']} (onset {e['source_event']['onset_utc']}, peak {e['source_event']['peak_utc']})" for e in c['retrospective_events'])
        lines += [f"### {c['name']}",event_text,'',c['prior_timing_context'],'',f"Within-case six-hour snapshots: {c['within_case_six_hour_summary']['hourly_class_counts']}. See `case-studies.md` for values, contradictory observations, missingness and every issue snapshot.",'']
    lines += ['## Scientific conclusion and Phase 5 gate','',s['conclusion'],'',s['phase5_readiness'],'',
              'No classification accuracy is reported: documentary flood/storm reports are independent context but do not supply reference forcing labels. No probability, contribution percentage, flood forecast or advisory recommendation is produced. Before experimental forecasting, independently review event-level labels, broaden nonresponse/large-flow controls, investigate local rainfall and downstream tributaries, assess wind and lag alternatives, and validate prospective receipt-time availability. Phase 5 has not begun.','',
              '## Reproduction','',
              'Run `python scripts/phase4.py`, then `python scripts/phase4.py --output work/phase4-repeat` and compare output bytes. The dedicated free GitHub Actions job runs these same steps with the full archive. `historical.json` holds witness observations and uncertainty; `replay.json.gz` holds separate issue assessments; CSV is a compact index.']
    return '\n'.join(lines)


def render_cases(cases):
    lines=['# Phase 4 detailed case studies','',
           'All classifications describe experimental supporting observations. Event-scale interpretations and named-case snapshots cover different intervals. Absolute native elevations are never compared across stations.','']
    for c in cases:
        lines += [f"## {c['name']}",'',f"Case window: {c['start_utc']} to {c['end_utc_exclusive']} (end exclusive for observations).",'',c['caveat'],'',c['prior_timing_context'],'']
        for context in c['external_context']:lines += [f"Independent documentary context (NCEI event {context['event_id']}): {context['reported_context']}",'']
        if not c['external_context']:lines += ['No corresponding local NCEI row in the inherited documentary review. This does not establish absence of a hazard.','']
        for e in c['retrospective_events']:
            event=e['source_event'];lines += [f"### {e['record_id']} — {e['category']}",'',
                f"Onset {event['onset_utc']} ({'known' if event['onset_known'] else 'censored/uncertain'}); peak {event['peak_utc']}; native rise {event['rise_native_gage_height']} ft; recovery ends {event['recovery_end_utc']}. Evidence-sufficient hours: {e['evidence_sufficient_fraction']:.1%}. Coexistence: {e['coexistence_hours']} h.",'',
                'Supporting: '+'; '.join(e['supporting'])+'.','',
                'Contradictory: '+('; '.join(e['contradictory']) or 'No flagged contradiction under these screens')+'.','',
                'Missing/unreliable: '+('; '.join(e['missing']) or 'None under these screens')+'.','',
                'Uncertainty: '+'; '.join(e['uncertainty']), '',
                '| Pathway | First support UTC | Last support UTC | First relative to MAUL1 onset (h) | Present / absent / unknown hours |',
                '|---|---|---|---:|---|']
            for name,t in e['pathway_timing'].items():
                lines.append(f"| {name} | {t['first_utc']} | {t['last_utc']} | {t.get('first_relative_to_onset_hours')} | {t['present_hours']} / {t['absent_hours']} / {t['unknown_hours']} |")
            for name,w in e['witnesses'].items():
                lines += ['',f"#### First {name} witness — {w['issue_time_utc']}",'',w['explanation'],'','```json',json.dumps(w['metrics'],indent=2,sort_keys=True),'```']
        lines += ['', '### Historical issue-time snapshots','',
                  'Six-hour fixed UTC clocks. Q is the trailing six-hour median cfs. Δlake is the minimum current MDLL1 stage minus its prior 48-hour median ending 24h earlier, in native feet. Wind is the minimum projection toward 270° in knots. These columns are observations/screens, not forecasts. Full flags, coverage, missing/contradictory evidence and metrics are in `cases.json` and the separate replay dataset.','',
                  '| UTC decision time | Class | River / residual / lake / wind | Q cfs | Residual ft | Δlake ft | West wind kt | MAUL1 response screen |',
                  '|---|---|---|---:|---:|---:|---:|---|']
        def fmt(x):return 'missing' if x is None else f'{x:.3f}'
        for r in c['issue_time_snapshots']:
            m=r['metrics'];f=r['flags']
            lines.append(f"| {r['issue_time_utc']} | {r['category']} | {' / '.join(f[k] for k in ('river','residual','lake','wind'))} | {fmt(m['discharge']['current_median_cfs'])} | {fmt(m['lake_changes']['NWCL1:residual']['current_median_ft'])} | {fmt(m['lake_changes']['MDLL1:stage']['conservative_rise_native_ft'])} | {fmt(m['wind']['projected_minimum_knots'])} | {f['response']} |")
        lines += ['']
    return '\n'.join(lines)
