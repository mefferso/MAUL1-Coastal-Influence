"""Independent, descriptive historical validation for Phase 3B.

The analysis uses the continuous Phase 3A hourly archive and its declared
first-signal detector. It evaluates timing and observation sufficiency; it
does not infer causes, calibrate forecast probabilities, or claim skill.
"""
import argparse
import csv
import datetime as dt
import gzip
import json
import math
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze
import build


SCHEMA_VERSION = '3B.1'
UTC = dt.timezone.utc
TARGET = ('MAUL1', 'stage')
PREDICTORS = (
    ('DENL1', 'discharge', 'river_timing', 72, 50.0),
    ('NWCL1', 'residual', 'lake_residual_timing', 18, 0.05),
    ('MDLL1', 'stage', 'independent_lake_timing', 18, 0.05),
)
SUPPORT_SERIES = (('MCHL1', 'stage', 'pass_manchac_context', 0.05),)
SIGMAS = (1.5, 2.0, 2.5)
SEPARATIONS = (48, 72, 96)
CASES = ('flood-2016', 'beta-2020', 'front-2024-11', 'front-2025-04')
NCEI_CONTEXT = {
    'source': 'NOAA NCEI Storm Events Database detail CSV, independent documentary context only',
    'dataset_url': 'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/',
    'revisions': {'2016': 'StormEvents_details-ftp_v1.0_d2016_c20260323.csv.gz',
                  '2020': 'StormEvents_details-ftp_v1.0_d2020_c20260323.csv.gz',
                  '2024': 'StormEvents_details-ftp_v1.0_d2024_c20260728.csv.gz',
                  '2025': 'StormEvents_details-ftp_v1.0_d2025_c20260819.csv.gz'},
    'sha256': {'2016':'d8e1389897df3557e74ba36820357f6962a7c0ca922595400fe74d883f7a5036',
               '2020':'895c56fd46991c4d9a135d67558dc4b447a02a2314efac0ace645135b98f9c9d',
               '2024':'2070b83eccab041b36360ab73645b9a249c3eefc5b92b5b3fc0cbba4d9fcc09c',
               '2025':'d9b46b4c6aae554723cadbb9691f3d5258371c02e530ba815d6fe41e4550149f'},
    'case_records': {
      'flood-2016': [
        {'event_id':'657049','episode_id':'109514','local_time':'13-AUG-16 21:00:00',
         'parish':'Ascension','type':'Flood','source':'Emergency Manager',
         'reported_context':'NCEI narrative states two days of heavy rain drained into the Amite River, record river levels, and backwater flooding; it reports about 16,000 homes/businesses with varying damage.'},
        {'event_id':'657054','episode_id':'109514','local_time':'15-AUG-16 07:00:00',
         'parish':'St. James','type':'Flood','source':'Emergency Manager',
         'reported_context':'NCEI narrative links record Amite River levels to upstream flow/backwater flooding along the Blind River.'}],
      'beta-2020': [
        {'event_id':'921987','episode_id':'153106','local_time':'22-SEP-20 19:00:00 CDT',
         'parish':'Livingston','type':'Storm Surge/Tide','source':'Other Federal Agency',
         'reported_context':'NCEI narrative reports 4.04 ft NAVD88 at USGS MAUL1 and 5.47 ft NAVD88 at USACE TSPL1 at 19:00 CDT; its episode narrative describes persistent moderate/strong onshore east and northeast winds and impacts Sep 19–23.'},
        {'event_id':'921979','episode_id':'153106','local_time':'21-SEP-20 06:00:00 CST',
         'parish':'Orleans','type':'Storm Surge/Tide','source':'Other Federal Agency',
         'reported_context':'NCEI narrative reports 3.83 ft MHHW at NOS New Canal NWCL1 and a separate 4.66 ft NAVD88 at USACE PRSL1. The NWCL1 MHHW value is not directly interchangeable with NAVD88.'}],
      'front-2024-11': [
        {'event_id':'1224701','episode_id':'198062','local_time':'19-NOV-24 07:20:00 CST',
         'parish':'St. Tammany','type':'Flash Flood','source':'Public',
         'reported_context':'NCEI narrative reports Gause Boulevard was impassable due to heavy rainfall.'},
        {'event_id':'1224686','episode_id':'198062','local_time':'19-NOV-24 06:35:00 CST',
         'parish':'St. Tammany','type':'Flash Flood','source':'Broadcast Media',
         'reported_context':'NCEI narrative reports flooded roads and stalled vehicles in Mandeville.'},
        {'event_id':'1224687','episode_id':'198062','local_time':'19-NOV-24 06:37:00 CST',
         'parish':'Orleans','type':'Flash Flood','source':'Public',
         'reported_context':'NCEI narrative reports street flooding in New Orleans.'}],
      'front-2025-04': []
    },
    'reviewed_corridor_parishes': ['Ascension','East Baton Rouge','Iberville','Jefferson','Livingston','Orleans','St. Charles','St. James','St. John the Baptist','St. Tammany','Tangipahoa'],
    'limits': 'Storm-event reports document reported hazards and context, not station data provenance or causal ground truth. Local timestamps are preserved as published and are not mixed with UTC observation onsets.'
}
NEEDED = {
    TARGET, ('MAUL1', 'elevation'), ('DENL1', 'discharge'), ('DENL1', 'stage'),
    ('NWCL1', 'water'), ('NWCL1', 'prediction'), ('NWCL1', 'residual'),
    ('NWCL1', 'wind'), ('NWCL1', 'wind_direction'), ('NWCL1', 'wind_u'),
    ('NWCL1', 'wind_v'),
    ('MDLL1', 'stage'), ('MCHL1', 'stage'),
    ('NWCL1-NDBC', 'wind'), ('NWCL1-NDBC', 'wind_direction'),
    ('NWCL1-NDBC', 'wind_u'), ('NWCL1-NDBC', 'wind_v'),
    ('NWCL1-NDBC', 'gust'),
}


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)


def iso(stamp):
    return stamp.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ') if stamp else None


def load_hourly(root):
    """Load only scientific inputs used below; missing hours remain explicit."""
    records = []
    for path in sorted((pathlib.Path(root) / 'hourly').glob('*.json.gz')):
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            month = json.load(stream)
        records.extend(row for row in month.get('records', [])
                       if (row.get('station'), row.get('variable')) in NEEDED)
    # The archive stores the two native New Canal products (observed water
    # level and astronomical prediction) separately. Derive the non-tidal
    # residual only for coincident, valid observations on the same datum.
    # Keep explicit hourly rows, including unavailable pairs, so coverage and
    # gaps remain auditable rather than disappearing from the denominator.
    by_key = {(row.get('station'), row.get('variable'), parse_time(row['time'])): row
              for row in records if row.get('time')}
    residuals = []
    water_times = sorted(stamp for station, variable, stamp in by_key
                         if station == 'NWCL1' and variable == 'water')
    for stamp in water_times:
        water = by_key[('NWCL1', 'water', stamp)]
        prediction = by_key.get(('NWCL1', 'prediction', stamp))
        same_datum = bool(prediction and water.get('datum') and
                          water.get('datum') == prediction.get('datum'))
        both_valid = valid(water) and valid(prediction) and same_datum
        residuals.append({'time': iso(stamp), 'station': 'NWCL1', 'variable': 'residual',
                          'value': round(water['value'] - prediction['value'], 6) if both_valid else None,
                          'coverage': min(water.get('coverage', 0), prediction.get('coverage', 0)) if prediction else 0,
                          'missing': not both_valid, 'unit': water.get('unit'),
                          'datum': water.get('datum') if same_datum else None,
                          'source': 'derived same-time observed water minus astronomical prediction'})
    records.extend(residuals)
    return records


def series_index(records):
    result = defaultdict(dict)
    for row in records:
        result[(row.get('station'), row.get('variable'))][parse_time(row['time'])] = row
    return result


def valid(row):
    return bool(row and row.get('value') is not None and row.get('coverage', 0) >= 1)


def contiguous_intervals(stamps, missing_stamps):
    """Collapse explicit hourly gaps into UTC interval records."""
    missing = sorted(missing_stamps)
    if not missing:
        return []
    result = []
    start = previous = missing[0]
    for stamp in missing[1:]:
        if stamp != previous + dt.timedelta(hours=1):
            result.append({'start_utc': iso(start), 'end_utc': iso(previous),
                           'hours': int((previous-start).total_seconds()/3600)+1})
            start = stamp
        previous = stamp
    result.append({'start_utc': iso(start), 'end_utc': iso(previous),
                   'hours': int((previous-start).total_seconds()/3600)+1})
    return result


def coverage_audit(root, hourly_coverage, manifest, index):
    """Retain full monthly source states and report hourly gaps only when queried."""
    months = manifest.get('months', {})
    result = {}
    gap_intervals = {}
    source_states = {}
    coverage_report = json.loads((pathlib.Path(root) / 'coverage.json').read_text())
    # The Phase 3A hourly coverage report counts the native water and tide
    # predictions separately. Add their same-datum intersection as the
    # derived NWCL1 residual denominator used by this validation.
    residual_expected = residual_valid = residual_reported = 0
    for month in coverage_report.get('months', []):
        hourly = month.get('hourly_coverage', {}).get('NWCL1', {})
        water = hourly.get('water')
        prediction = hourly.get('prediction')
        if not water or not prediction:
            continue
        count = min(water.get('reporting_hours', water.get('expected_hours', 0)),
                    prediction.get('reporting_hours', prediction.get('expected_hours', 0)))
        year, mon = map(int, month['month'].split('-'))
        begin = dt.datetime(year, mon, 1, tzinfo=UTC)
        residual_expected += count
        residual_reported += count
        residual_valid += sum(valid(index.get(('NWCL1', 'residual'), {}).get(begin + dt.timedelta(hours=i)))
                              for i in range(count))
    if residual_reported:
        hourly_coverage = dict(hourly_coverage)
        hourly_coverage['NWCL1:residual'] = {
            'valid_hours': residual_valid, 'missing_hours': residual_reported - residual_valid,
            'not_yet_observed_hours': 0, 'expected_hours': residual_expected,
            'reported_hours': residual_reported}
    for key, values in sorted(hourly_coverage.items()):
        station, variable = key.split(':', 1)
        if (station, variable) not in NEEDED or '_change_' in variable or variable == 'wind_vector_trailing':
            continue
        available_months = []
        unqueried = Counter()
        for month, sources in months.items():
            source = sources.get(station)
            if not source and station == 'NWCL1-NDBC':
                source = sources.get('NWCL1-NDBC')
            status = (source or {}).get('status', 'not_reported')
            if status in {'retrieved', 'skipped'} and (source or {}).get('row_count', 0) > 0:
                available_months.append(month)
            elif status != 'retrieved' and status != 'skipped':
                unqueried[status] += 1
        row = dict(values)
        row['monthly_source_states'] = dict(sorted(unqueried.items()))
        row['station_source_months_with_rows'] = len(available_months)
        result[key] = row

        # Use the generated per-month expected counts: source-empty/error months
        # are not recast as zero-observation periods.
        missing = []
        interval_months = []
        for month in coverage_report.get('months', []):
            monthly = month.get('hourly_coverage', {}).get(station, {}).get(variable)
            if station == 'NWCL1' and variable == 'residual':
                water_cov = month.get('hourly_coverage', {}).get('NWCL1', {}).get('water')
                pred_cov = month.get('hourly_coverage', {}).get('NWCL1', {}).get('prediction')
                if not water_cov or not pred_cov:
                    continue
                monthly = {'reporting_hours': min(water_cov.get('reporting_hours', water_cov.get('expected_hours', 0)),
                                                  pred_cov.get('reporting_hours', pred_cov.get('expected_hours', 0)))}
            if not monthly:
                continue
            interval_months.append(month['month'])
            report_hours = monthly.get('reporting_hours', monthly.get('expected_hours', 0))
            year, mon = map(int, month['month'].split('-'))
            begin = dt.datetime(year, mon, 1, tzinfo=UTC)
            for hour in range(report_hours):
                stamp = begin + dt.timedelta(hours=hour)
                if not valid(index.get((station, variable), {}).get(stamp)):
                    missing.append(stamp)
        gap_intervals[key] = contiguous_intervals([], missing)
        row['months_with_hourly_denominator'] = len(interval_months)
        row['missing_interval_count'] = len(gap_intervals[key])
    # Make acquisition statuses discoverable at the same granularity as the
    # station list, including independent support sources.
    for station in sorted({s for sources in months.values() for s in sources}):
        source_states[station] = dict(Counter((sources.get(station) or {}).get('status', 'not_reported')
                                              for sources in months.values()))
    return {'hourly_variables': result, 'missing_intervals': gap_intervals,
            'monthly_source_status_counts': source_states,
            'note': 'Hourly missing intervals cover months with a generated hourly denominator. Retrieval errors, empty successful queries, and not-queried sources remain separate manifest states.'}


def _episode_end(item):
    start = parse_time(item['_cluster_start'])
    if item.get('duration_hours'):
        return start + dt.timedelta(hours=item['duration_hours'] - 1)
    if item.get('peak_utc'):
        return parse_time(item['peak_utc'])
    return start


def split_datum_segments(rows):
    """Do not let detector changes bridge records carrying different datums."""
    segments = []
    for row in sorted(rows,key=lambda item:item['time']):
        if not segments or row.get('datum') != segments[-1][-1].get('datum'):
            segments.append([row])
        else:
            segments[-1].append(row)
    return segments


def detect_all(index, sigma=2.0):
    """Run the fixed Phase 2B detector over continuous series, with stable IDs."""
    raw = []
    configs = [(TARGET[0], TARGET[1], 'target', None, 0.25)] + [
        (station, variable, pathway, lead, minimum)
        for station, variable, pathway, lead, minimum in PREDICTORS
    ] + [(station, variable, 'support', None, minimum)
         for station, variable, _, minimum in SUPPORT_SERIES]
    for station, variable, role, lead, minimum_rise in configs:
        rows = [row for _, row in sorted(index.get((station, variable), {}).items())]
        if not rows:
            raw.append({'episode_id': f'{station.lower()}-{variable}-unavailable',
                        'station': station, 'variable': variable, 'role': role,
                        'status': 'unavailable_baseline', 'onset_utc': None,
                        'onset_known': False, 'reason': 'no hourly series in archive',
                        'qualifying_signal': False})
            continue
        for segment_number, segment in enumerate(split_datum_segments(rows),1):
            episodes = analyze.detect_episodes(segment, station, variable,
                        min_rise=minimum_rise, sigma_threshold=sigma, baseline_hours=72,
                        min_baseline_points=48, min_coverage=1, min_duration_hours=3,
                        reset_hours=6)
            for number, episode in enumerate(episodes, 1):
                item = dict(episode)
                item.update(episode_id=f'{station.lower()}-{variable}-d{segment_number:02d}-{number:04d}',
                            role=role, station=station, variable=variable,
                            datum_segment=segment_number,
                            qualifying_signal=episode.get('status') == 'detected')
                if lead is not None:
                    item['maximum_lead_hours'] = lead
                if item.get('onset_utc'):
                    item['_cluster_start'] = item['onset_utc']
                elif item.get('status') == 'already_underway':
                    item['_cluster_start'] = segment[0]['time']
                    if segment_number > 1:
                        item['onset_censoring'] = 'datum_change_boundary_left_censored'
                        item['reason'] = 'datum segment begins during a sustained rise; onset censored at datum transition'
                    else:
                        item['onset_censoring'] = 'archive_boundary_left_censored'
                else:
                    item['_cluster_start'] = None
                raw.append(item)
    return raw


def eligible_episode(item):
    return item.get('qualifying_signal') and item.get('onset_utc') is not None


def cluster_episodes(episodes, separation_hours=72):
    """Create transitive cross-station event groups before any temporal split."""
    timed = [item for item in episodes if item.get('_cluster_start')]
    ordered = sorted(timed, key=lambda item: (item['_cluster_start'], item['episode_id']))
    groups = []
    for episode in ordered:
        start = parse_time(episode['_cluster_start'])
        end = _episode_end(episode)
        previous = groups[-1] if groups else None
        if previous and start <= previous['_end'] + dt.timedelta(hours=separation_hours):
            previous['episodes'].append(episode)
            previous['_end'] = max(previous['_end'], end)
            previous['_start'] = min(previous['_start'], start)
        else:
            groups.append({'episodes': [episode], '_start': start, '_end': end})
    result = []
    for number, group in enumerate(groups, 1):
        records = group['episodes']
        target_signals = [e for e in records if e['role'] == 'target' and eligible_episode(e)]
        target_uncertain = [e for e in records if e['role'] == 'target' and e.get('status') in {'uncertain','gap','already_underway'}]
        detected_predictors = [e for e in records if e['role'] not in {'target','support'} and eligible_episode(e)]
        detected_support = [e for e in records if e['role'] == 'support' and eligible_episode(e)]
        group_id = f'g{separation_hours}-{number:04d}'
        first_target = min((parse_time(e['onset_utc']) for e in target_signals), default=None)
        matches = []
        later = []
        coincident = []
        if first_target:
            for station, variable, pathway, window, _ in PREDICTORS:
                candidates = [e for e in detected_predictors if e['station'] == station and
                              e['variable'] == variable and
                              0 < (first_target - parse_time(e['onset_utc'])).total_seconds()/3600 <= window]
                if candidates:
                    predictor = max(candidates, key=lambda e: parse_time(e['onset_utc']))
                    lead = (first_target - parse_time(predictor['onset_utc'])).total_seconds()/3600
                    matches.append({'event_group_id': group_id,
                                    'target_episode_id': next(e['episode_id'] for e in target_signals
                                        if parse_time(e['onset_utc']) == first_target),
                                    'predictor_episode_id': predictor['episode_id'],
                                    'target_station': 'MAUL1', 'predictor_station': station,
                                    'predictor_variable': variable, 'timing_evidence': pathway,
                                    'lead_hours': round(lead, 3), 'maximum_window_hours': window,
                                    'status': 'timing_match_descriptive_only',
                                    'forecast_utility_validated': False})
            coincident = [e for e in detected_predictors if parse_time(e['onset_utc']) == first_target]
            later = [e for e in detected_predictors if parse_time(e['onset_utc']) > first_target]
        if not target_signals:
            status = 'target_onset_uncertain' if target_uncertain else 'predictor_only_or_no_detected_target'
        elif matches:
            status = 'target_with_advance_timing_signals'
        elif later:
            status = 'predictors_detected_after_target_onset'
        elif coincident:
            status = 'coincident_signals_without_advance'
        else:
            status = 'target_without_detected_advance_signal'
        row = {'event_group_id': group_id, 'separation_hours': separation_hours,
               'start_utc': iso(group['_start']), 'end_utc': iso(group['_end']),
               'duration_hours': round((group['_end']-group['_start']).total_seconds()/3600, 3),
               'episode_count': len(records), 'target_episode_ids': [e['episode_id'] for e in records if e['role']=='target'],
               'predictor_episode_ids': [e['episode_id'] for e in records if e['role']!='target'],
               'detected_target_episode_count': len(target_signals),
               'uncertain_target_episode_count': len(target_uncertain),
               'detected_predictor_episode_count': len(detected_predictors),
               'detected_support_episode_count': len(detected_support),
               'support_episode_ids': [e['episode_id'] for e in detected_support],
               'status': status, 'timing_match_count': len(matches),
               'coincident_predictor_episode_ids': [e['episode_id'] for e in coincident],
               'post_target_predictor_episode_ids': [e['episode_id'] for e in later],
               'uncertainty_flags': sorted({flag for e in records for flag in (
                   (['onset_uncertain'] if e.get('status') in {'uncertain','gap','already_underway'} else []) +
                   (['left_censored_at_archive_start'] if e.get('onset_censoring') else []))}),
               'matches': matches,
               'interpretation': 'Algorithmically separated event group; timing evidence only, not an independently established storm, cause, or forecast case.'}
        result.append(row)
    return result


def interval_rows(index, key, start, end):
    rows = index.get(key, {})
    cursor = start
    while cursor < end:
        yield rows.get(cursor)
        cursor += dt.timedelta(hours=1)


def window_coverage(index, key, start, end):
    expected = max(0, int((end-start).total_seconds()/3600))
    values = list(interval_rows(index, key, start, end))
    count = sum(valid(row) for row in values)
    return {'expected_hours': expected, 'valid_hours': count,
            'missing_hours': expected-count,
            'valid_fraction': round(count/expected, 4) if expected else None}


def _quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered)-1)*fraction
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low]*(high-position)+ordered[high]*(position-low)


def lead_summaries(matches):
    grouped = defaultdict(list)
    for match in matches:
        grouped[match['predictor_station']].append(match['lead_hours'])
    result = {}
    for station, values in sorted(grouped.items()):
        result[station] = {'n_event_group_matches': len(values),
                           'median_hours': round(statistics.median(values), 3),
                           'p25_hours': round(_quantile(values, .25), 3),
                           'p75_hours': round(_quantile(values, .75), 3),
                           'min_hours': min(values), 'max_hours': max(values),
                           'strictly_positive_advance_matches': len([v for v in values if v > 0]),
                           'note': 'Descriptive onset difference conditional on detected signal and MAUL1 episode; not actionable forecast lead.'}
    return result


def temporal_split(groups, boundary='2023-01-01T00:00:00Z', embargo_hours=72):
    """Assign complete event groups to a fixed time split with seam embargo."""
    cut = parse_time(boundary)
    embargo = dt.timedelta(hours=embargo_hours)
    output = []
    for group in groups:
        start = parse_time(group['start_utc'])
        end = parse_time(group['end_utc'])
        if end < cut - embargo:
            subset = 'calibration_2016_2022'
        elif start >= cut + embargo:
            subset = 'holdout_2023_2026'
        else:
            subset = 'excluded_split_seam'
        output.append({'event_group_id': group['event_group_id'], 'subset': subset,
                       'start_utc': group['start_utc'], 'end_utc': group['end_utc'],
                       'rule': 'fixed 2023-01-01 temporal boundary; whole 72-hour-separated groups stay together; 72-hour seam embargo.'})
    return output


def negative_control_months(monthly_coverage, manifest_months, episodes, minimum_fraction=.9):
    """Select observable months without any detector candidate as quiet controls."""
    required = [TARGET, *((station, variable) for station, variable, _, _, _ in PREDICTORS)]
    controls = []
    excluded = []
    for month_record in monthly_coverage:
        month = month_record['month']
        month_signals = []
        for episode in episodes:
            if episode.get('role') not in {'target','river_timing','lake_residual_timing','independent_lake_timing'}:
                continue
            if episode.get('status') not in {'detected','uncertain','gap','already_underway'} or not episode.get('_cluster_start'):
                continue
            start = parse_time(episode['_cluster_start'])
            finish = _episode_end(episode)
            year, number = map(int, month.split('-'))
            month_start = dt.datetime(year,number,1,tzinfo=UTC)
            month_end = (month_start.replace(year=year+1,month=1) if number==12 else month_start.replace(month=number+1))
            if start < month_end and finish >= month_start:
                month_signals.append(episode['episode_id'])
        reasons = []
        metrics = {}
        for station, variable in required:
            entry = month_record.get('hourly_coverage',{}).get(station,{}).get(variable)
            key = f'{station}:{variable}'
            if not entry:
                reasons.append(f'{key}: no monthly hourly denominator/source unavailable')
                continue
            reporting = entry.get('reporting_hours',entry.get('expected_hours',0))
            fraction = entry.get('valid_hours',0)/reporting if reporting else 0
            metrics[key] = {'valid_hours':entry.get('valid_hours',0),'reporting_hours':reporting,
                            'valid_fraction':round(fraction,4)}
            if fraction < minimum_fraction:
                reasons.append(f'{key}: monthly valid coverage below {minimum_fraction:.0%}')
        if month_signals:
            reasons.append(f'{len(month_signals)} target/core predictor detector candidate(s) overlap month')
        source_states = manifest_months.get(month,{})
        if reasons:
            excluded.append({'month':month,'status':'excluded','reasons':reasons,
                             'candidate_episode_ids':month_signals,'coverage':metrics,
                             'source_statuses':{name:source.get('status') for name,source in source_states.items()}})
        else:
            controls.append({'control_id':f'quiet-{month}','month':month,
                             'status':'quiet_observed_control_month','coverage':metrics,
                             'source_statuses':{name:source.get('status') for name,source in source_states.items()},
                             'interpretation':'No target/core predictor candidate under the fixed detector and all required series met the coverage screen. This does not prove no hydrologic forcing.'})
    return {'minimum_monthly_valid_coverage':minimum_fraction,
            'required_series':[f'{station}:{variable}' for station,variable in required],
            'quiet_control_months':controls,'excluded_months':excluded,
            'quiet_control_count':len(controls),'excluded_month_count':len(excluded)}


def _series_window_summary(index, key, start, end):
    values = [(stamp, row) for stamp, row in index.get(key, {}).items()
              if start <= stamp < end and valid(row)]
    expected = max(0, int((end-start).total_seconds()/3600))
    if not values:
        return {'valid_hours': 0, 'expected_hours': expected, 'coverage_fraction': 0,
                'maximum': None, 'minimum': None, 'first': None, 'last': None,
                'largest_6h_rise': None}
    values.sort(key=lambda x: x[0])
    numeric = [(stamp, float(row['value'])) for stamp, row in values]
    look = dict(numeric)
    changes = [(look[stamp]-look[stamp-dt.timedelta(hours=6)], stamp)
               for stamp, _ in numeric if stamp-dt.timedelta(hours=6) in look]
    maximum = max(numeric, key=lambda x: x[1]); minimum = min(numeric, key=lambda x: x[1])
    largest = max(changes, default=(None, None), key=lambda x: x[0] if x[0] is not None else float('-inf'))
    return {'valid_hours': len(values), 'expected_hours': expected,
            'coverage_fraction': round(len(values)/expected, 4) if expected else None,
            'maximum': {'value': round(maximum[1], 6), 'time_utc': iso(maximum[0]),
                        'unit': maximum[1] and values[0][1].get('unit')},
            'minimum': {'value': round(minimum[1], 6), 'time_utc': iso(minimum[0]),
                        'unit': values[0][1].get('unit')},
            'first': {'value': numeric[0][1], 'time_utc': iso(numeric[0][0])},
            'last': {'value': numeric[-1][1], 'time_utc': iso(numeric[-1][0])},
            'largest_6h_rise': {'change': round(largest[0], 6), 'time_utc': iso(largest[1])}
                if largest[0] is not None else None,
            'datum': values[0][1].get('datum')}


def _wind_summary(index, station, start, end):
    u = index.get((station, 'wind_u'), {})
    v = index.get((station, 'wind_v'), {})
    pairs = [(stamp, float(row['value']), float(v[stamp]['value']))
             for stamp, row in u.items() if start <= stamp < end and valid(row) and valid(v.get(stamp))]
    expected = max(0, int((end-start).total_seconds()/3600))
    if not pairs:
        return {'station': station, 'valid_vector_hours': 0, 'expected_hours': expected,
                'mean_speed_knots': None, 'mean_from_direction_degrees': None,
                'directional_persistence': None}
    speeds = [math.hypot(east, north) for _, east, north in pairs]
    east = statistics.mean(p[1] for p in pairs); north = statistics.mean(p[2] for p in pairs)
    bearings = [(math.degrees(math.atan2(-u0, -v0))+360) % 360
                for _, u0, v0 in pairs if math.hypot(u0,v0) > 1e-9]
    persistence = math.hypot(statistics.mean(math.sin(math.radians(x)) for x in bearings),
                             statistics.mean(math.cos(math.radians(x)) for x in bearings)) if bearings else None
    direction = (math.degrees(math.atan2(-east,-north))+360)%360 if east or north else None
    return {'station': station, 'valid_vector_hours': len(pairs), 'expected_hours': expected,
            'coverage_fraction': round(len(pairs)/expected,4) if expected else None,
            'mean_speed_knots': round(statistics.mean(speeds),3),
            'mean_from_direction_degrees': round(direction,1) if direction is not None else None,
            'directional_persistence': round(persistence,3) if persistence is not None else None,
            'note': 'Meteorological direction is descriptive only; no favorable-wind cutoff was selected.'}


def navd88_threshold_audit(index, threshold_ft=4.0):
    """Only direct MAUL1 NAVD88 observations can establish the level threshold."""
    elevations = [row for row in index.get(('MAUL1','elevation'), {}).values()
                 if valid(row) and row.get('datum') == 'NAVD88']
    exceedances = sorted((row for row in elevations if float(row['value']) >= threshold_ft),
                         key=lambda row: row.get('time', ''))
    native_stage = [row for row in index.get(TARGET, {}).values()
                    if valid(row) and row.get('datum') != 'NAVD88' and float(row['value']) >= threshold_ft]
    return {'station': 'MAUL1', 'threshold_ft': threshold_ft, 'datum': 'NAVD88',
            'eligible_direct_observation_count': len(elevations),
            'eligible_observations_at_or_above_threshold': len(exceedances),
            'first_eligible_exceedance_utc': exceedances[0].get('time') if exceedances else None,
            'maximum_direct_navd88_ft': max((float(row['value']) for row in elevations), default=None),
            'native_00065_values_at_or_above_4ft_excluded_from_threshold_test': len(native_stage),
            'rule': 'Only MAUL1 elevation rows explicitly carrying datum NAVD88 are threshold eligible. Native 00065 gage height is never converted or counted.'}


def datum_transition_audit(index):
    result = {}
    for (station,variable), rows in sorted(index.items()):
        ordered = sorted(rows.items())
        transitions = []
        for (previous_time,previous),(current_time,current) in zip(ordered,ordered[1:]):
            if previous.get('datum') != current.get('datum'):
                transitions.append({'time_utc':iso(current_time),
                    'previous_datum':previous.get('datum'),'current_datum':current.get('datum'),
                    'previous_value':previous.get('value'),'current_value':current.get('value'),
                    'time_gap_hours':round((current_time-previous_time).total_seconds()/3600,3),
                    'cross_datum_change_used':False})
        if transitions:
            result[f'{station}:{variable}'] = transitions
    return result


def boundary_detector_audit(index, months):
    """Compare month-local detector output to continuous output near month starts."""
    cases = []
    configs = [(TARGET[0], TARGET[1], .25), *((s,v,r) for s,v,_,_,r in PREDICTORS)]
    for station, variable, minimum_rise in configs:
        full = [row for _, row in sorted(index.get((station, variable), {}).items())]
        continuous = analyze.detect_episodes(full, station, variable, min_rise=minimum_rise,
                    sigma_threshold=2.0, baseline_hours=72, min_baseline_points=48,
                    min_coverage=1, min_duration_hours=3, reset_hours=6)
        continuous_events = [(parse_time(e['onset_utc']), parse_time(e['onset_utc']) +
                              dt.timedelta(hours=max(0,(e.get('duration_hours') or 1)-1)))
                             for e in continuous if e.get('onset_utc') and e.get('status') == 'detected']
        continuous_times = [start for start, _ in continuous_events]
        local_left_censored = []
        local_early_detections = []
        omitted_continuous_detections = []
        for month in months:
            month_rows = [row for row in full if row['time'].startswith(month)]
            if not month_rows:
                continue
            local = analyze.detect_episodes(month_rows, station, variable, min_rise=minimum_rise,
                        sigma_threshold=2.0, baseline_hours=72, min_baseline_points=48,
                        min_coverage=1, min_duration_hours=3, reset_hours=6)
            month_start = parse_time(month+'-01T00:00:00Z')
            first_72_end = month_start + dt.timedelta(hours=72)
            for episode in local:
                if episode.get('status') == 'already_underway' and episode.get('reason') == 'archive begins during a sustained positive rise':
                    peak = parse_time(episode['peak_utc']) if episode.get('peak_utc') else month_start
                    truly_active = any(start <= month_start <= finish or start <= peak <= finish
                                       for start, finish in continuous_events)
                    if not truly_active:
                        local_left_censored.append({'month':month,'peak_utc':episode.get('peak_utc')})
                if episode.get('status') == 'detected' and episode.get('onset_utc'):
                    onset = parse_time(episode['onset_utc'])
                    if month_start <= onset < first_72_end and not any(abs((onset-stamp).total_seconds()) <= 3600 for stamp in continuous_times):
                        local_early_detections.append({'month':month,'onset_utc':episode['onset_utc']})
            for stamp in continuous_times:
                if month_start <= stamp < first_72_end:
                    matching = [e for e in local if e.get('status') == 'detected' and e.get('onset_utc') and
                                abs((parse_time(e['onset_utc'])-stamp).total_seconds()) <= 3600]
                    if not matching:
                        omitted_continuous_detections.append({'month':month,'onset_utc':iso(stamp)})
        cases.append({'station':station,'variable':variable,
                      'month_local_left_censored_candidates':local_left_censored,
                      'month_local_early_onsets_without_continuous_counterpart':local_early_detections,
                      'continuous_first_72h_onsets_absent_from_month_local_detection':omitted_continuous_detections,
                      'left_censored_candidate_count':len(local_left_censored),
                      'false_or_boundary_sensitive_local_onset_count':len(local_early_detections),
                      'missed_or_reclassified_boundary_onset_count':len(omitted_continuous_detections),
                      'interpretation':'Counterfactual month-reset audit at the fixed detector settings. A disagreement is boundary-sensitive detector behavior, not proof of a real event or absence.'})
    return cases


def priority_case_reviews(index, discovery, verification, support_episodes=()):
    discovery_targets = discovery.get('targets', [])
    discovery_predictors = discovery.get('predictors', [])
    by_id = {item['event_id']: item for item in verification.get('events', [])}
    cases = []
    for event_id in CASES:
        title, start_date, end_date = build.EVENTS[event_id]
        start = parse_time(start_date+'T00:00:00Z')
        end = parse_time(end_date+'T00:00:00Z')
        # The event archive end dates are inclusive UTC dates.
        end += dt.timedelta(days=1)
        target_events = [e for e in discovery_targets if
                         ((e.get('onset_utc') and start-dt.timedelta(hours=72) <= parse_time(e['onset_utc']) < end) or
                          (not e.get('onset_utc') and e.get('peak_utc') and start <= parse_time(e['peak_utc']) < end))]
        predictor_events = [e for e in discovery_predictors if e.get('onset_utc') and
                            start-dt.timedelta(hours=72) <= parse_time(e['onset_utc']) < end]
        supporting_events = [e for e in support_episodes if
                            ((e.get('onset_utc') and start-dt.timedelta(hours=72) <= parse_time(e['onset_utc']) < end) or
                             (not e.get('onset_utc') and e.get('peak_utc') and start <= parse_time(e['peak_utc']) < end))]
        summaries = {}
        for key in ((('MAUL1','stage')), (('MAUL1','elevation')), (('DENL1','discharge')),
                    (('NWCL1','residual')), (('NWCL1','water')), (('MDLL1','stage')),
                    (('MCHL1','stage'))):
            summaries[f'{key[0]}:{key[1]}'] = _series_window_summary(index, key, start, end)
        wind = [_wind_summary(index, station, start, end) for station in ('NWCL1','NWCL1-NDBC')]
        timeline = []
        for episode in target_events:
            response_time = episode.get('onset_utc') or episode.get('peak_utc')
            timeline.append({'time_utc': response_time, 'type': 'MAUL1_candidate_response',
                             'station': 'MAUL1', 'status': episode['status'],
                             'onset_known': bool(episode.get('onset_utc')),
                             'rise_native_units': episode.get('rise'),
                             'peak_utc': episode.get('peak_utc'),
                             'datum': episode.get('datum')})
            if episode.get('onset_utc'):
                response_stamp = parse_time(episode['onset_utc'])
                timeline.append({'time_utc': episode['onset_utc'], 'type': 'six_hour_wind_context',
                                 'independent_sources': [_wind_summary(index, s, response_stamp-dt.timedelta(hours=6), response_stamp)
                                                         for s in ('NWCL1','NWCL1-NDBC')],
                                 'interpretation':'Observed vector wind context only; no direction/speed threshold implies support.'})
        for episode in predictor_events:
            timeline.append({'time_utc': episode['onset_utc'], 'type': 'predictor_signal',
                             'station': episode['station'], 'variable': episode['variable'],
                             'status': episode['status'], 'rise_native_units': episode.get('rise'),
                             'peak_utc': episode.get('peak_utc')})
        for episode in supporting_events:
            timeline.append({'time_utc': episode.get('onset_utc') or episode.get('peak_utc'),
                             'type': 'MCHL1_support_episode', 'station': 'MCHL1', 'variable': 'stage',
                             'status': episode['status'], 'onset_known': bool(episode.get('onset_utc')),
                             'rise_native_units': episode.get('rise'), 'peak_utc': episode.get('peak_utc'),
                             'interpretation': 'Potential propagation context only; no matching window or causal label assigned.'})
        timeline.sort(key=lambda item: item['time_utc'])
        canonical = by_id.get(event_id, {})
        summary = canonical.get('summary', {})
        cases.append({'event_id': event_id, 'name': title, 'start_utc': iso(start),
                      'end_utc_exclusive': iso(end), 'known_target_episodes_in_extended_window': len(target_events),
                      'predictor_signals_in_extended_window': len(predictor_events),
                      'MCHL1_support_episodes_in_extended_window': len(supporting_events),
                      'canonical_event_window_summary': summary,
                      'canonical_target_statuses': Counter(e.get('status') for e in canonical.get('target_episodes', [])),
                      'observed_series_summaries': summaries, 'wind_context': wind,
                      'external_storm_context': NCEI_CONTEXT['case_records'].get(event_id, []),
                      'timeline_utc': timeline,
                      'interpretation': 'Event title/context is not causal ground truth. An onset that is unknown or left-censored cannot support a measured precursor lead. Native MAUL1 stage is not NAVD88.'})
    return cases


def _render_markdown(result, cases):
    leads = result['lead_time_distributions_hours']
    lines = ['# Phase 3B — Independent historical validation', '',
             '**Status: exploratory historical validation. No forecast model, causal classifier, or skill claim.**', '',
             '## Main finding', '',
             'The archive contains descriptive timing associations, but it does not establish that the five-station network provides demonstrably useful advance warning. Event onsets, matching thresholds, and observation coverage remain uncertain; no independent causal ground truth or pre-issued forecast opportunities exist. Probability of detection, false-alarm ratio, and critical success index are therefore reported as unavailable.', '',
             '## Data and detection audit', '',
             f"The analysis used {result['archive']['month_count']} UTC months ({result['archive']['first_month']} through {result['archive']['last_month']}) and retained source-level unresolved months in the coverage audit. The selected target detector produced {result['detector']['maul1_detected_episode_count']} detected MAUL1 rise episodes, grouped into {result['independence']['primary_target_group_count']} target-containing time clusters with a fixed {result['independence']['primary_separation_hours']}-hour cross-station separation rule. These are algorithmic clusters, not verified independent storms.", '',
             '| Station | Variable | Valid hours | Missing hours | Not yet observed | Expected hours |',
             '|---|---|---:|---:|---:|---:|']
    for key, item in result['coverage_audit']['hourly_variables'].items():
        station, variable = key.split(':',1)
        lines.append(f"| {station} | {variable} | {item['valid_hours']} | {item['missing_hours']} | {item['not_yet_observed_hours']} | {item['expected_hours']} |")
    lines += ['', 'Monthly retrieval errors, empty successful queries, and not-queried sources are shown separately in `coverage.json`; a source month without rows is not labeled as an observed hourly gap. Gap interval timestamps are machine-readable in that file.', '',
             '| Detector sigma | MAUL1 detected episodes | Target-containing groups | Groups with advance timing association | Descriptive group matches | All target detector records |', '|---:|---:|---:|---:|---:|---:|']
    for sigma, info in result['sensitivity']['sigma'].items():
        lines.append(f"| {sigma} | {info['maul1_detected']} | {info['target_groups']} | {info['target_groups_with_advance_timing_association']} | {info['descriptive_group_match_count']} | {info['maul1_records']} |")
    lines += ['', 'The sensitivity results show that episode counts change materially with the pre-existing 1.5/2.0/2.5 robust-sigma setting. The 72-hour baseline, minimum 48 baseline changes, 3-hour minimum persistence, fixed station-specific minimum rise, positive consecutive changes, and 6-hour reset were kept fixed. Thresholds were not reselected on the same archive to claim skill.', '',
              f"Quality review retained {result['quality_audit']['finding_count']} automated flag(s) as candidates, chiefly {', '.join(f'{k} ({v})' for k,v in result['quality_audit']['finding_counts_by_station_variable'].items())}. Direct MAUL1 NAVD88 archive observations above 4.0 ft: {result['navd88_threshold_audit']['eligible_observations_at_or_above_threshold']}; native 00065 values are excluded from that count.", '',
              'The month-reset counterfactual in `validation.json` reports local left-censor, early-onset, and reclassified/missed-onset counts by detector series. Each disagreement is an audit flag, not a scientifically verified false event.', '',
              '## Precursor timing', '',
              '| Predictor | Matched event groups | Median lead | Interquartile range | Range |', '|---|---:|---:|---:|---:|']
    for station in ('DENL1','NWCL1','MDLL1'):
        item = leads.get(station)
        if item:
            lines.append(f"| {station} | {item['n_event_group_matches']} | {item['median_hours']} h | {item['p25_hours']}–{item['p75_hours']} h | {item['min_hours']}–{item['max_hours']} h |")
        else:
            lines.append(f'| {station} | 0 | unavailable | unavailable | unavailable |')
    lines += ['', 'The lead table includes detected time groups with available onset records. The coverage-qualified subset (0.9 hourly completeness in each station-specific matching window) is summarized separately in `validation.json`; all retained/excluded groups remain in `events.csv` and `exclusions.csv`.']
    lines += ['', 'These are retrospective onset differences conditional on the detector finding a signal and a MAUL1 episode within the fixed 0–72 h DENL1 or 0–18 h NWCL1/MDLL1 window. Simultaneous signals are not advance notice. They do not account for real-time data latency or demonstrate actionable warning. NWCL1 residual alone is not coastal evidence; MDLL1 and independent wind context are reported separately.', '',
              '## Nonresponse, missed events, and metrics', '',
             f"The event table retains {result['outcomes']['target_without_qualifying_advance_signal']} detected MAUL1 groups without a qualifying earlier signal, {result['outcomes']['predictor_only_groups']} predictor-only groups, {result['outcomes']['post_target_only_groups']} groups with detected predictors only after target onset, {result['outcomes']['coincident_without_advance_groups']} coincident groups with no positive lead, and {result['outcomes']['onset_uncertain_groups']} groups with uncertain target onset. The 0.9-coverage screen leaves {result['independence']['coverage_qualified_target_groups']['0.9']} target groups for descriptive network-availability summaries.", '',
              f"The control audit retained {result['negative_control_selection']['quiet_control_count']} well-observed quiet month(s) under a 90% coverage screen for MAUL1 stage, DENL1 discharge, NWCL1 residual, and MDLL1 stage; {result['negative_control_selection']['excluded_month_count']} months are retained with source/coverage/signal exclusion reasons. Quiet means no detector candidate in those series, not no forcing.", '',
              'These are descriptive response/nonresponse counts, not false alarms or missed forecasts: the archive does not encode forecast issuance times, independent forcing labels, or all intervening runoff. Event-level POD, FAR, and CSI are `unavailable` because prediction opportunities, response labels, event independence, and uniform coverage requirements are not established.', '',
              '## Event independence and future split', '',
              f"Episodes were grouped across stations before splitting. The primary rule connects records whose active intervals overlap or are separated by at most {result['independence']['primary_separation_hours']} hours; {', '.join(str(x) for x in SEPARATIONS)}-hour sensitivity counts are in the JSON report. This rule cannot prove meteorological independence. A fixed Jan 1, 2023 calibration/holdout boundary and 72-hour seam embargo are recorded for future work; they do not constitute Phase 4 holdout results. The available archive and current labels do not support a statistically defensible independent forecast holdout claim.", '',
              '## Priority cases', '']
    for case in cases:
        canonical = case['canonical_event_window_summary']
        lines.append(f"### {case['name']}")
        lines.append(f"UTC window {case['start_utc']} to {case['end_utc_exclusive']} (end exclusive). Canonical Phase 2B verification: {canonical.get('target_signal_episode_count', 'n/a')} target episode(s), {canonical.get('matches', 'n/a')} timing match(es), {canonical.get('unmatched_predictors', 'n/a')} unmatched predictor record(s).")
        target = case['observed_series_summaries'].get('MAUL1:stage', {})
        lines.append(f"MAUL1 native stage coverage: {target.get('valid_hours',0)}/{target.get('expected_hours',0)} hours; datum {target.get('datum') or 'unavailable'}. The detailed UTC observation/signal timeline and other station coverage are in `cases.json`.")
        signal_times = [f"{item['time_utc']} {item['station']} {item['type']} ({item['status']})"
                        for item in case.get('timeline_utc', [])
                        if item['type'] in {'MAUL1_candidate_response','predictor_signal','MCHL1_support_episode'}][:8]
        lines.append('Observed continuous-archive UTC signal timeline: '+('; '.join(signal_times) if signal_times else 'no detected timestamped signal in the extended window; unknown onsets remain in the case record')+'.')
        context = case.get('external_storm_context', [])
        for record in context[:2]:
            lines.append(f"Independent context: NOAA NCEI Storm Events {record['event_id']} ({record['local_time']}, {record['parish']}, {record['type']}; source `{record['source']}`) — {record['reported_context']}")
        if case['event_id'] in {'flood-2016','beta-2020'}:
            lines.append('The canonical target episode begins already underway with unknown onset; retrospective signals cannot resolve a prior lead or establish cause. MCHL1 availability is incomplete for this period.')
        elif case['event_id'] == 'front-2024-11':
            lines.append('The previously preliminary timing association is not treated as validation; NWCL1 residual, independent MDLL1 response, winds, and target onset uncertainty must be considered jointly. No causal conclusion follows from residual timing alone.')
        else:
            lines.append('The April response is compared with all archived predictors and independent wind observations; missing periods and native datums remain explicit. Timing evidence alone cannot distinguish river, coastal, and compound mechanisms.')
        if case['event_id'] == 'beta-2020':
            lines.append('NCEI’s event narrative is a documented external report of 4.04 ft NAVD88 at MAUL1 on Sep 22 local time (source field “Other Federal Agency”). It is not a direct archived 63160 row and is kept as contextual evidence pending instrument/report provenance; the historical gage-height series is still not converted or used to claim the threshold.')
        if case['event_id'] == 'front-2025-04':
            lines.append('The reviewed NCEI detail release has no event rows in the selected Lake Maurepas/Pass Manchac corridor counties for this window; it contains Louisiana events elsewhere. No local entry is not evidence that local runoff or coastal forcing was absent.')
        lines.append('')
    lines += ['## Datum and source safeguards', '',
              'MAUL1 00065 remains native gage height. Only direct 63160 NAVD88 observations are eligible for the 4.0 ft NAVD88 threshold; this Phase 3B target detector does not use gage height to claim that threshold. NWCL1 positive residual is not sufficient to label coastal influence. A lack of DENL1 discharge response does not rule out downstream tributaries or local runoff. MCHL1 is not merged with either USACE station; NDBC winds remain an independent comparison.', '',
              '## Files', '',
              '- `validation.json`: audit, event groups, sensitivity, timing summaries, and split assignments.',
              '- `summary.json`: compact dashboard result.',
              '- `events.csv`: event-group level records with coverage and outcome state.',
              '- `matches.csv`: per-group predictor timing, including lead and method status.',
              '- `cases.json`: the four priority case reviews with compact UTC timelines.',
              '- `coverage.json`: hourly denominator, gaps, and monthly source acquisition states.',
              '- `exclusions.csv`: retained non-detections and explicit exclusion reasons.', '',
              'This evidence supports further independent review and better-labeled data collection. It does not support operational forecasting or causal classification.']
    return '\n'.join(lines)+'\n'


def run(root='site/data/history', output=None):
    root = pathlib.Path(root)
    output = pathlib.Path(output or root / 'phase3b')
    output.mkdir(parents=True, exist_ok=True)
    records = load_hourly(root)
    index = series_index(records)
    coverage = json.loads((root / 'coverage.json').read_text())
    manifest = json.loads((root / 'manifest.json').read_text())
    discovery_path = root / 'discovery.json'
    discovery = json.loads(discovery_path.read_text()) if discovery_path.exists() else {}
    verification = json.loads((root.parent / 'verification.json').read_text())
    months = sorted(manifest.get('months', {}))
    monthly_coverage = coverage.get('months', [])

    primary_episodes = detect_all(index, 2.0)
    sigma_results = {}
    for sigma in SIGMAS:
        episodes = primary_episodes if sigma == 2.0 else detect_all(index, sigma)
        targets = [e for e in episodes if e['role'] == 'target']
        sigma_groups = cluster_episodes([e for e in episodes if e.get('_cluster_start')],72)
        sigma_results[str(sigma)] = {'maul1_records': len(targets),
            'maul1_detected': sum(e.get('status') == 'detected' for e in targets),
            'maul1_statuses': dict(Counter(e.get('status') for e in targets)),
            'predictor_records': sum(e.get('role') not in {'target','support'} for e in episodes),
            'predictor_detected': sum(e.get('role') not in {'target','support'} and e.get('status') == 'detected' for e in episodes),
            'support_records': sum(e.get('role') == 'support' for e in episodes),
            'support_detected': sum(e.get('role') == 'support' and e.get('status') == 'detected' for e in episodes),
            'target_groups': sum(g['detected_target_episode_count']>0 for g in sigma_groups),
            'target_groups_with_advance_timing_association': sum(g['status']=='target_with_advance_timing_signals' for g in sigma_groups),
            'descriptive_group_match_count': sum(g['timing_match_count'] for g in sigma_groups)}

    episodes = [e for e in primary_episodes if e.get('_cluster_start')]
    groups_by_separation = {gap: cluster_episodes(episodes, gap) for gap in SEPARATIONS}
    episode_lookup = {item['episode_id']:item for item in primary_episodes}
    for gap, separated in groups_by_separation.items():
        for group in separated:
            for episode_id in group['target_episode_ids']+group['predictor_episode_ids']:
                episode_lookup[episode_id].setdefault('event_group_assignments',{})[str(gap)] = group['event_group_id']
    groups = groups_by_separation[72]
    # Use the 72-hour groups as the primary sample and avoid counting an
    # episode twice when multiple input series describe one time cluster.
    lead_matches = [match for group in groups for match in group['matches']]
    target_groups = [g for g in groups if g['detected_target_episode_count']]
    outcomes = Counter(g['status'] for g in target_groups)
    controls = negative_control_months(monthly_coverage,manifest.get('months',{}),primary_episodes)
    split = temporal_split(groups)
    split_counts = Counter(row['subset'] for row in split)

    response_rows = []
    match_rows = []
    for group in groups:
        start, end = parse_time(group['start_utc']), parse_time(group['end_utc'])
        target_onsets = [parse_time(e['onset_utc']) for e in episodes if e.get('role') == 'target' and
                         e.get('onset_utc') and e['episode_id'] in group['target_episode_ids']]
        onset = min(target_onsets) if target_onsets else None
        target_window = window_coverage(index, TARGET, onset-dt.timedelta(hours=72), onset) if onset else None
        group['target_baseline_coverage'] = target_window
        group['wind_context_preceding_6h'] = ([_wind_summary(index, station, onset-dt.timedelta(hours=6), onset)
                                               for station in ('NWCL1','NWCL1-NDBC')] if onset else [])
        group['target_window_source_status'] = 'target_onset_known' if onset else 'onset_unknown_or_no_detected_target'
        group['baseline_coverage_gate_passed'] = bool(target_window and target_window['valid_hours'] >= 48)
        group['source_window_coverage'] = {}
        if onset:
            for station, variable, _, lead, _ in PREDICTORS:
                group['source_window_coverage'][f'{station}:{variable}'] = window_coverage(
                    index, (station, variable), onset-dt.timedelta(hours=lead), onset)
        source_fractions = [value['valid_fraction'] for value in group['source_window_coverage'].values()]
        for threshold in (.8, .9, 1.0):
            group.setdefault('coverage_screen', {})[str(threshold)] = bool(
                group['detected_target_episode_count'] > 0 and
                group['baseline_coverage_gate_passed'] and len(source_fractions) == len(PREDICTORS) and
                all(value is not None and value >= threshold for value in source_fractions))
        group['well_observed_for_primary_onset'] = group['coverage_screen']['0.9']
        response_rows.append(group)
        for match in group['matches']:
            match_rows.append({**match, 'event_group_status': group['status'],
                               'group_start_utc': group['start_utc'], 'group_end_utc': group['end_utc'],
                               'uncertainty_flags': group['uncertainty_flags'],
                               'coverage_qualified_90pct': group.get('coverage_screen',{}).get('0.9', False),
                               'interpretation': 'descriptive retrospective timing; not verified precursor utility'})

    # Event-window signal episodes and observed coverage are preserved so that
    # gaps, censored onsets, and weak candidate records are not discarded.
    support_episodes = [e for e in primary_episodes if e['role'] == 'support']
    case_records = priority_case_reviews(index, discovery, verification, support_episodes)
    coverage_result = coverage_audit(root, coverage.get('hourly_variable_coverage', {}), manifest, index)
    # Quality flags are retained as review candidates; flags are not automatic
    # data rejection criteria.
    quality_path = root / 'quality.json'
    quality = json.loads(quality_path.read_text()) if quality_path.exists() else {'finding_count': None, 'findings': []}
    finding_groups = Counter(':'.join(f.get('group', [])) for f in quality.get('findings', []))

    gaps_by_series = coverage_result['missing_intervals']
    month_boundaries = []
    boundary_stamps = [parse_time(f'{int(y):04d}-{int(m):02d}-01T00:00:00Z')
                       for y, m in [month.split('-') for month in months[1:]]]
    for station, variable in [TARGET, *[(x[0], x[1]) for x in PREDICTORS]]:
        values = index.get((station, variable), {})
        for boundary in boundary_stamps:
            previous = values.get(boundary-dt.timedelta(hours=1)); current = values.get(boundary)
            if valid(previous) and valid(current):
                month_boundaries.append({'station': station, 'variable': variable,
                    'boundary_utc': iso(boundary), 'previous_value': previous['value'],
                    'current_value': current['value'],
                    'change': round(float(current['value'])-float(previous['value']), 6),
                    'antecedent_24h_valid_hours': sum(valid(values.get(boundary-dt.timedelta(hours=h))) for h in range(1,25)),
                    'context_status': 'cross_boundary_observation_and_antecedent_retained'})
            else:
                month_boundaries.append({'station': station, 'variable': variable,
                    'boundary_utc': iso(boundary), 'previous_value': previous.get('value') if previous else None,
                    'current_value': current.get('value') if current else None,
                    'change': None, 'antecedent_24h_valid_hours': None,
                    'context_status': 'boundary_change_unavailable_due_to_missing_hour'})

    discovered_target = [e for e in discovery.get('targets', []) if e.get('status') == 'detected']
    predictor_status = Counter((e.get('station'), e.get('status')) for e in primary_episodes if e.get('role') != 'target')
    metrics = {'probability_of_detection': {'value': None, 'status': 'unavailable',
        'reason': 'No independent response/forcing ground truth and no defined forecast issuance opportunities.'},
        'false_alarm_ratio': {'value': None, 'status': 'unavailable',
        'reason': 'Predictor episodes are retrospective signals, not issued forecasts; predictor-only groups are descriptive nonresponses.'},
        'critical_success_index': {'value': None, 'status': 'unavailable',
        'reason': 'Event independence and binary forecast opportunity/outcome labels are not established.'}}
    result = {
      'schema_version': SCHEMA_VERSION,
      'method': 'Independent Phase 3B descriptive validation over the Phase 3A continuous UTC hourly archive. Existing fixed event detector; time-cluster groups; no causal labels or forecast skill.',
      'archive': {'first_month': months[0] if months else None, 'last_month': months[-1] if months else None,
                  'month_count': len(months), 'hourly_records_loaded': len(records),
                  'source_month_status_counts': coverage_result['monthly_source_status_counts']},
      'detector': {'method': 'positive consecutive hourly change; fixed preceding 72-hour baseline; at least 48 valid one-hour changes; minimum 3-hour rise; minimum station-specific rise; sigma 2.0 primary; 6-hour reset; no interpolation.',
                   'target_variable': 'MAUL1 native 00065 stage; gage height, not NAVD88.',
                   'maul1_detected_episode_count': sum(e.get('status') == 'detected' for e in primary_episodes if e['role']=='target'),
                   'target_detector_status_counts': dict(Counter(e.get('status') for e in primary_episodes if e['role']=='target')),
                   'predictor_detector_status_counts': {f'{s}:{status}': count for (s,status),count in predictor_status.items()},
                   'sigma_sensitivity_prespecified': list(SIGMAS), 'baseline_hours': 72,
                   'minimum_baseline_changes': 48, 'minimum_persistence_hours': 3,
                   'reset_hours': 6, 'minimum_rise': {'MAUL1': '0.25 native gage-height ft',
                       'DENL1': '50 cfs', 'NWCL1:residual': '0.05 ft', 'MDLL1:stage': '0.05 native ft'},
                   'sigma': 2.0, 'MCHL1_role':'supporting propagation observations only; no predeclared matching lead window and no causal classification.',
                   'maul1_episodes_in_prior_discovery': len(discovered_target)},
      'sensitivity': {'sigma': sigma_results,
                      'event_separation_hours': {str(gap): {'all_time_clusters': len(values),
                          'target_containing_groups': sum(g['detected_target_episode_count']>0 for g in values),
                          'multi_target_groups': sum(g['detected_target_episode_count']>1 for g in values)}
                          for gap, values in groups_by_separation.items()}},
      'independence': {'primary_separation_hours': 72,
                       'primary_all_group_count': len(groups),
                       'primary_target_group_count': len(target_groups),
                       'primary_multi_target_group_count': sum(g['detected_target_episode_count']>1 for g in target_groups),
                       'coverage_qualified_target_groups': {threshold: sum(bool(g.get('coverage_screen',{}).get(threshold)) for g in target_groups)
                                                           for threshold in ('0.8','0.9','1.0')},
                       'coverage_screen_rule': 'A detected target group is coverage-qualified when its target detector had at least 48 valid 72-hour baseline changes and all three core predictor windows (72 h DENL1; 18 h NWCL1/MDLL1) have the stated fraction of valid hourly rows. This is an observation-sufficiency screen, not evidence of true event independence or skill.',
                       'rule': 'Transitive grouping of overlapping active episode intervals and intervals separated by no more than 72 hours, across all five observation stations. This is a conservative time-separation heuristic, not a claim of scientifically independent storm events.',
                       'known_dependence': 'Named Sally and Beta 2020 event windows are retained in their existing shared independence group; priority case names are not used as ground-truth labels.'},
      'lead_time_distributions_hours': lead_summaries(lead_matches),
      'lead_time_distributions_hours_coverage_qualified': lead_summaries([
          match for group in groups if group.get('coverage_screen',{}).get('0.9') for match in group['matches']]),
      'outcomes': {'target_without_qualifying_advance_signal': outcomes.get('target_without_detected_advance_signal', 0),
                   'predictor_only_groups': sum(g['detected_predictor_episode_count']>0 and not g['detected_target_episode_count'] for g in groups),
                   'MCHL1_support_only_groups': sum(g['detected_support_episode_count']>0 and not g['detected_predictor_episode_count'] and not g['detected_target_episode_count'] for g in groups),
                   'post_target_only_groups': outcomes.get('predictors_detected_after_target_onset', 0),
                   'coincident_without_advance_groups': outcomes.get('coincident_signals_without_advance', 0),
                   'onset_uncertain_groups': outcomes.get('target_onset_uncertain', 0),
                   'target_groups_with_advance_timing_signals': outcomes.get('target_with_advance_timing_signals', 0),
                   'status_counts': dict(outcomes)},
      'verification_metrics': metrics,
      'calibration_holdout': {'split_boundary_utc': '2023-01-01T00:00:00Z',
                   'embargo_hours': 72, 'split_rule': 'Assign complete 72-hour-separated episode groups before splitting; groups touching the split seam are excluded from both partitions.',
                   'group_counts': dict(split_counts),
                   'assessment': 'This is a future-proof partition proposal only. Counts do not imply sufficient independent, well-observed, labeled target events for holdout verification; the current archive lacks independent causal labels and operational forecasts.'},
      'coverage_audit': coverage_result,
      'negative_control_selection': controls,
      'quality_audit': {'finding_count': quality.get('finding_count'),
                        'finding_counts_by_station_variable': dict(finding_groups),
                        'interpretation': 'Automated flags are candidates for human review, not proof of bad observations.'},
      'navd88_threshold_audit': navd88_threshold_audit(index),
      'datum_transition_audit': {'transitions_by_series':datum_transition_audit(index),
          'detector_segmentation_rule':'Detector series are partitioned at datum changes. No first-difference signal or antecedent baseline crosses a datum boundary; post-boundary onset is left-censored until sufficient same-datum baseline is available.'},
      'boundary_audit': {'cross_month_boundary_changes': month_boundaries,
                         'boundary_transition_count': sum(x['change'] is not None for x in month_boundaries),
                         'unavailable_boundary_transitions': sum(x['change'] is None for x in month_boundaries),
                         'month_reset_detector_comparison': boundary_detector_audit(index, months),
                         'method': 'Compare previous-month 23:00 UTC and new-month 00:00 UTC hourly values for every archived month boundary, and count valid antecedent hours. A fixed-detector counterfactual compares continuous records with month-local runs; no missing values are imputed.'},
      'event_groups': groups,
      'event_group_sensitivity_memberships': [
          {'separation_hours':gap,'event_group_id':g['event_group_id'],
           'start_utc':g['start_utc'],'end_utc':g['end_utc'],
           'episode_ids':g['target_episode_ids']+g['predictor_episode_ids']}
          for gap, separated in groups_by_separation.items() for g in separated],
      'episodes': [{k:v for k,v in e.items() if not k.startswith('_')} for e in primary_episodes],
      'matches': match_rows,
      'split_assignments': split,
      'cases_file': 'cases.json',
      'limitations': [
        'Historical time clusters are not independent storm labels; a 72-hour separation rule can join distinct forcing or split one prolonged episode.',
        'MAUL1 00065 is native gage height and is not used to infer 4.0 ft NAVD88 exceedances.',
        'A first-signal match is a retrospective timing association, not evidence of actionable warning, propagation, causality, or forecast skill.',
        'Positive NWCL1 residual alone is not coastal evidence; independent MDLL1 and wind context are shown without an unvalidated wind threshold.',
        'No DENL1 rise does not exclude tributary/local runoff; no independent event ground truth or issue-time data is available.',
        'Retrieval errors, successful empty queries, and periods with partial hourly coverage remain explicit; missing observations are not filled.'
      ]}

    case_payload = {'schema_version': SCHEMA_VERSION, 'cases': case_records,
                    'external_context_source': NCEI_CONTEXT['source'],
                    'external_context_revisions': NCEI_CONTEXT['revisions'],
                    'external_context_sha256': NCEI_CONTEXT['sha256'],
                    'reviewed_corridor_parishes': NCEI_CONTEXT['reviewed_corridor_parishes'],
                    'external_context_limits': NCEI_CONTEXT['limits'],
                    'context_status': 'Named-event windows and independent NOAA Storm Events records are context, not causal ground truth. NCEI local timestamps are intentionally separate from archive UTC timestamps.'}
    short_summary = {'schema_version': SCHEMA_VERSION,
                     'archive': result['archive'], 'independence': result['independence'],
                     'detector': result['detector'], 'outcomes': result['outcomes'],
                     'negative_control_selection': {'quiet_control_count':controls['quiet_control_count'],
                                                     'excluded_month_count':controls['excluded_month_count']},
                     'lead_time_distributions_hours': result['lead_time_distributions_hours'],
                     'lead_time_distributions_hours_coverage_qualified': result['lead_time_distributions_hours_coverage_qualified'],
                     'verification_metrics': result['verification_metrics'],
                     'cases': [{'event_id':case['event_id'],'name':case['name'],
                                'target_episode_count':case['canonical_event_window_summary'].get('target_signal_episode_count'),
                                'timing_matches':case['canonical_event_window_summary'].get('matches'),
                                'target_coverage':case['observed_series_summaries']['MAUL1:stage']}
                               for case in case_records],
                     'conclusion': 'Current archive supports retrospective timing associations, but not demonstrated actionable forecast utility or causal classification.'}
    (output / 'validation.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    (output / 'summary.json').write_text(json.dumps(short_summary, indent=2, sort_keys=True)+'\n')
    (output / 'cases.json').write_text(json.dumps(case_payload, indent=2, sort_keys=True)+'\n')
    (output / 'coverage.json').write_text(json.dumps(coverage_result, indent=2, sort_keys=True)+'\n')
    with (output / 'events.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ['event_group_id','start_utc','end_utc','duration_hours','episode_count',
                  'detected_target_episode_count','uncertain_target_episode_count',
                  'detected_predictor_episode_count','status','timing_match_count','well_observed_for_primary_onset',
                  'uncertainty_flags','target_episode_ids','predictor_episode_ids',
                  'target_baseline_coverage','source_window_coverage']
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore'); writer.writeheader()
        for group in response_rows:
            row = dict(group)
            for field in ('uncertainty_flags','target_episode_ids','predictor_episode_ids',
                          'target_baseline_coverage','source_window_coverage'):
                row[field] = json.dumps(row.get(field), sort_keys=True, separators=(',',':'))
            writer.writerow(row)
    with (output / 'matches.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ['event_group_id','target_episode_id','predictor_episode_id','target_station',
                  'predictor_station','predictor_variable','timing_evidence','lead_hours',
                  'maximum_window_hours','status','forecast_utility_validated','event_group_status',
                  'group_start_utc','group_end_utc','coverage_qualified_90pct','uncertainty_flags']
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore'); writer.writeheader()
        for match in match_rows:
            row = dict(match)
            row['uncertainty_flags'] = json.dumps(row.get('uncertainty_flags'),separators=(',',':'))
            writer.writerow(row)
    with (output / 'exclusions.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ['episode_id','station','variable','role','status','onset_utc','reason','datum_status']
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore'); writer.writeheader()
        for item in primary_episodes:
            if not item.get('qualifying_signal'):
                row = dict(item)
                row.setdefault('reason', {'no_signal': 'no qualifying signal under fixed detector',
                    'uncertain': 'candidate failed magnitude/duration/noise certainty criteria',
                    'gap': 'missing observation broke event persistence',
                    'unavailable_baseline': 'insufficient valid antecedent baseline',
                    'already_underway': 'left-censored archive-start onset'} .get(item.get('status'), 'not a qualifying detected onset'))
                writer.writerow(row)
    (output / 'report.md').write_text(_render_markdown(result, case_records))
    print(json.dumps({'months': len(months), 'hourly_records': len(records),
                      'target_episodes': result['detector']['maul1_detected_episode_count'],
                      'target_groups': len(target_groups), 'matches': len(match_rows),
                      'quality_findings': quality.get('finding_count'),
                      'output': str(output)}, sort_keys=True))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='site/data/history')
    parser.add_argument('--output', default=None)
    args = parser.parse_args(argv)
    run(args.root, args.output)


if __name__ == '__main__':
    main()
