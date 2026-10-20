"""Descriptive event discovery for the continuous Phase 3A archive.

This module identifies candidate episodes and quiet controls from the derived
hourly archive. It deliberately does not assign causes, forecast skill, or
probabilities. A match means only that two first-signal timestamps fall in a
predeclared window.
"""
import argparse
import datetime as dt
import gzip
import json
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze


SCHEMA_VERSION = '3A.1'
PREDICTORS = (
    ('DENL1', 'discharge', 'river', 72, 50.0),
    ('NWCL1', 'residual', 'coastal', 18, 0.05),
    ('MDLL1', 'stage', 'coastal', 18, 0.05),
)


def _dt(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(dt.timezone.utc)


def _month_bounds(value):
    stamp = _dt(value).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if stamp.month == 12:
        end = stamp.replace(year=stamp.year + 1, month=1)
    else:
        end = stamp.replace(month=stamp.month + 1)
    return stamp, end


def _episode_end(episode):
    if episode.get('end_utc'):
        return _dt(episode['end_utc'])
    if episode.get('onset_utc') and episode.get('duration_hours'):
        return _dt(episode['onset_utc']) + dt.timedelta(hours=episode['duration_hours'] - 1)
    return _dt(episode.get('onset_utc')) if episode.get('onset_utc') else None


def merge_dependent(episodes, gap_hours=6):
    """Group overlapping/nearby episodes within one declared pathway."""
    grouped_by_pathway = defaultdict(list)
    ordered = sorted(
        episodes,
        key=lambda item: (item.get('pathway', ''), item.get('onset_utc') or '9999', item.get('episode_id', '')),
    )
    for episode in ordered:
        onset = _dt(episode['onset_utc']) if episode.get('onset_utc') else None
        end = _episode_end(episode)
        groups = grouped_by_pathway[episode.get('pathway')]
        if not onset or not end:
            groups.append({'pathway': episode.get('pathway'), 'episode_ids': [episode.get('episode_id')],
                            'start_utc': episode.get('onset_utc'), 'end_utc': episode.get('end_utc')})
            continue
        previous = groups[-1] if groups else None
        if (previous and previous['pathway'] == episode.get('pathway') and previous.get('end_utc') and
                onset <= _dt(previous['end_utc']) + dt.timedelta(hours=gap_hours)):
            previous['episode_ids'].append(episode.get('episode_id'))
            if end > _dt(previous['end_utc']):
                previous['end_utc'] = end.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            groups.append({'pathway': episode.get('pathway'), 'episode_ids': [episode.get('episode_id')],
                            'start_utc': onset.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'end_utc': end.strftime('%Y-%m-%dT%H:%M:%SZ')})
    grouped = [group for groups in grouped_by_pathway.values() for group in groups]
    return sorted(grouped, key=lambda group: group.get('start_utc') or '9999')


def _with_ids(episodes, prefix):
    result = []
    for index, episode in enumerate(episodes, 1):
        item = dict(episode)
        item['episode_id'] = f'{prefix}-{index:04d}'
        result.append(item)
    return result


def classify_matches(targets, predictors):
    """Return descriptive pathway candidates and explicit nonresponses."""
    all_matches = []
    unmatched_predictors = []
    for pathway in ('river', 'coastal'):
        pathway_predictors = [item for item in predictors if item.get('pathway') == pathway]
        max_lead = 72 if pathway == 'river' else 18
        matching = analyze.match_episodes(targets, pathway_predictors, max_lead_hours=max_lead)
        for match in matching['matches']:
            match['pathway'] = pathway
            all_matches.append(match)
        for item in matching['unmatched_predictors']:
            item['category'] = f'{pathway}_nonresponse'
            item['note'] = 'Predictor timing signal without a matched MAUL1 first signal; descriptive nonresponse only.'
            unmatched_predictors.append(item)

    by_target = defaultdict(list)
    for match in all_matches:
        by_target[match['target_episode_id']].append(match)
    target_categories = []
    for target in targets:
        matches = by_target.get(target.get('episode_id'), [])
        pathways = sorted({item['pathway'] for item in matches})
        if set(pathways) == {'river', 'coastal'}:
            category = 'compound_candidate'
        elif pathways:
            category = pathways[0]
        else:
            category = 'unmatched_response'
        target_categories.append({
            'target_episode_id': target.get('episode_id'),
            'category': category,
            'pathways': pathways,
            'predictor_episode_ids': [item.get('predictor_episode_id') for item in matches],
            'note': 'Candidate timing grouping only; not verified prediction skill, causal attribution, or classification.',
        })
    return {'matches': all_matches, 'target_categories': target_categories,
            'unmatched_predictors': unmatched_predictors}


def build_controls(hourly_records, signal_episodes, minimum_valid_hours=24):
    """Build month-level quiet controls from actual valid MAUL1 hours."""
    grouped = defaultdict(list)
    for row in hourly_records:
        if row.get('station') != 'MAUL1' or row.get('variable') != 'stage':
            continue
        grouped[_dt(row['time']).strftime('%Y-%m')].append(row)
    controls = []
    for month, rows in sorted(grouped.items()):
        start, end = _month_bounds(f'{month}-01T00:00:00Z')
        valid = [row for row in rows if row.get('value') is not None and row.get('coverage', 0) >= 1]
        has_signal = any(
            episode.get('onset_utc') and start <= _dt(episode['onset_utc']) < end
            for episode in signal_episodes
        )
        if len(valid) >= minimum_valid_hours and not has_signal:
            controls.append({
                'control_id': f'quiet-{month}',
                'category': 'quiet_control',
                'month': month,
                'start_utc': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end_utc': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'valid_hours': len(valid),
                'note': 'No detected target signal in this available month; quiet is a selection label, not proof of no forcing.',
            })
    return controls


def context_for_interval(start_utc, end_utc):
    """Record independent contextual sources without silently ingesting labels."""
    return {
        'start_utc': start_utc,
        'end_utc': end_utc,
        'status': 'not_queried',
        'references': [
            {'source': 'NOAA National Centers for Environmental Information storm events',
             'url': 'https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00617',
             'status': 'reference_only'},
            {'source': 'National Weather Service weather and coastal alerts',
             'url': 'https://www.weather.gov/', 'status': 'reference_only'},
            {'source': 'National Hurricane Center tropical cyclone archive',
             'url': 'https://www.nhc.noaa.gov/data/', 'status': 'reference_only'},
        ],
        'note': 'Independent context is not automatically queried or used as an event cause/classification.',
    }


def _load_hourly(root):
    """Load only the hourly series used by continuous discovery.

    Retaining every derived variable from every station in memory is unnecessary:
    event detection uses these four native series, and controls use MAUL1 stage.
    """
    needed = {(station, variable) for station, variable, *_ in PREDICTORS}
    needed.add(('MAUL1', 'stage'))
    records = []
    for path in sorted((pathlib.Path(root) / 'hourly').glob('*.json.gz')):
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            records.extend(row for row in json.load(stream).get('records', [])
                           if (row.get('station'), row.get('variable')) in needed)
    return records


def _series(records, station, variable):
    return [row for row in records if row.get('station') == station and row.get('variable') == variable]


def discover_events(hourly_records, coverage=None):
    """Discover continuous-archive episodes at three robust-sigma settings."""
    target_series = _series(hourly_records, 'MAUL1', 'stage')
    sensitivity = {}
    for sigma in (1.5, 2.0, 2.5):
        episodes = analyze.detect_episodes(target_series, 'MAUL1', 'stage', min_rise=0.25,
                                           sigma_threshold=sigma, baseline_hours=72,
                                           min_baseline_points=48, min_coverage=1)
        sensitivity[str(sigma)] = {
            'episode_count': len(episodes),
            'detected_onsets': [item.get('onset_utc') for item in episodes if item.get('status') == 'detected'],
            'statuses': [item.get('status') for item in episodes],
        }
    targets = _with_ids(analyze.detect_episodes(target_series, 'MAUL1', 'stage', min_rise=0.25,
                                                 sigma_threshold=2.0, baseline_hours=72,
                                                 min_baseline_points=48, min_coverage=1), 'maul1')
    predictors = []
    sensitivity_predictors = {}
    for station, variable, pathway, max_lead, minimum_rise in PREDICTORS:
        series = _series(hourly_records, station, variable)
        episodes = analyze.detect_episodes(series, station, variable, min_rise=minimum_rise,
                                           sigma_threshold=2.0, baseline_hours=72,
                                           min_baseline_points=48, min_coverage=1)
        identified = _with_ids(episodes, station.lower())
        for item in identified:
            item['pathway'] = pathway
            item['max_lead_hours'] = max_lead
        predictors.extend(identified)
        sensitivity_predictors[f'{station}:{variable}'] = {
            str(sigma): [item.get('status') for item in analyze.detect_episodes(
                series, station, variable, min_rise=minimum_rise, sigma_threshold=sigma,
                baseline_hours=72, min_baseline_points=48, min_coverage=1
            )] for sigma in (1.5, 2.0, 2.5)
        }
    match_targets = [item for item in targets if item.get('status') in {'detected', 'already_underway'}]
    match_predictors = [item for item in predictors if item.get('status') == 'detected']
    matching = classify_matches(match_targets, match_predictors)
    signal_episodes = match_targets + match_predictors
    groups = merge_dependent(signal_episodes)
    controls = build_controls(hourly_records, match_targets)
    if hourly_records:
        stamps = sorted(row['time'] for row in hourly_records if row.get('time'))
        context = context_for_interval(stamps[0], stamps[-1])
    else:
        context = context_for_interval(None, None)
    return {
        'schema_version': SCHEMA_VERSION,
        'method': 'Continuous hourly first-signal discovery from native observations; descriptive timing only.',
        'baseline': {'hours': 72, 'minimum_valid_change_points': 48, 'minimum_hourly_coverage': 1,
                     'sigma_sensitivities': [1.5, 2.0, 2.5], 'selected_sigma': 2.0,
                     'positive_changes_only': True},
        'targets': targets,
        'predictors': predictors,
        'matches': matching['matches'],
        'categories': matching['target_categories'] + matching['unmatched_predictors'],
        'dependent_groups': groups,
        'quiet_controls': controls,
        'sensitivity': {'MAUL1:stage': sensitivity, **sensitivity_predictors},
        'coverage': coverage or {},
        'context': context,
        'limitations': [
            'A detected first signal is not proof of a useful precursor to MAUL1 later rise.',
            'River, coastal, compound-candidate, nonresponse, and quiet-control labels are descriptive selection categories, not causes.',
            'No classification, forecast probability, causal attribution, or verified prediction skill is inferred.',
            'Missing observations, unavailable baselines, gaps, uncertain onsets, and archive-start episodes remain explicit.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='site/data/history')
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)
    records = _load_hourly(root)
    coverage = {}
    path = root / 'coverage.json'
    if path.exists():
        coverage = json.loads(path.read_text())
    result = discover_events(records, coverage)
    (root / 'discovery.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'hourly_records': len(records), 'target_episodes': len(result['targets']),
                      'categories': len(result['categories']), 'quiet_controls': len(result['quiet_controls'])},
                     sort_keys=True))
    return result


if __name__ == '__main__':
    main()
