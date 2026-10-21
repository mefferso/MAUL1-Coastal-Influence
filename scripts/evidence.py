"""Frozen, interpretable Phase 4 physical evidence screens, not attribution.

All timestamps denote completed hourly aggregate bins. No event catalogue,
peak, storm name, future observation, or centered filter enters assess().
"""
import datetime as dt
import math
import statistics

UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)
SERIES = (
    ('DENL1','discharge','native','cfs'),
    ('NWCL1','residual','MLLW','ft'),
    ('NWCL1','water','MLLW','ft'),
    ('NWCL1','prediction','MLLW','ft'),
    ('MDLL1','stage','gage height','ft'),
    ('MCHL1','stage','gage height','ft'),
    ('MAUL1','stage','gage height','ft'),
    ('NWCL1','wind_u','none','knots'),
    ('NWCL1','wind_v','none','knots'),
)
DEFAULTS = dict(discharge_high_cfs=20000., discharge_rise_cfs=5000.,
                discharge_ratio=1.25, residual_ft=.5, residual_rise_ft=.25,
                lake_rise_ft=.25, wind_projection_knots=5., wind_axis_degrees=270.,
                baseline_fraction=.8, persistence_hours=6)
CATEGORIES = ('River-supported','Coastal-supported','Compound-supported','Indeterminate')


def iso(stamp):
    return stamp.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def valid(row, unit):
    return bool(row and isinstance(row.get('value'), (int,float))
                and math.isfinite(row['value']) and row.get('coverage',0)>=1
                and not row.get('missing') and not row.get('phase4_quality_excluded')
                and row.get('unit')==unit and row.get('datum'))


def window(index, key, end, hours, unit):
    """Half-open [end-hours,end); never admit the current unfinished bin."""
    raw = [index.get(key,{}).get(end-HOUR*h) for h in range(hours,0,-1)]
    rows = [r for r in raw if valid(r,unit)]
    datums = sorted({r['datum'] for r in rows})
    return dict(values=[r['value'] for r in rows], fraction=len(rows)/hours,
                datums=datums, quality_excluded_hours=sum(bool(r and r.get('phase4_quality_excluded')) for r in raw))


def _state(condition, known):
    return ('present' if condition else 'absent') if known else 'unknown'


def _combine(states):
    # A failed physical requirement contradicts support even if another is missing.
    if 'absent' in states: return 'absent'
    if 'unknown' in states: return 'unknown'
    return 'present'


def category(river, coastal):
    if river=='present' and coastal=='present': return 'Compound-supported'
    if river=='present': return 'River-supported'
    if coastal=='present': return 'Coastal-supported'
    return 'Indeterminate'


def metrics(index, issue, persistence_hours=6):
    """Threshold-free metrics reusable by prespecified sensitivity variants."""
    p = persistence_hours
    result = {}
    for station, variable, datum, unit in SERIES:
        key = station,variable
        current = window(index,key,issue,p,unit)
        baseline = window(index,key,issue-dt.timedelta(hours=24),48,unit)
        old = window(index,key,issue-dt.timedelta(hours=72),p,unit)
        union = set(current['datums']+baseline['datums'])
        result[f'{station}:{variable}'] = {
            'current': current, 'baseline': baseline, 'antecedent_72h':old,
            'datum_consistent': len(union)==1,
            'expected_unit':unit,
        }
    return result


def decide(m, issue, thresholds=None):
    t = DEFAULTS | (thresholds or {})
    def known(item, part, fraction):
        return item[part]['fraction'] >= fraction and len(item[part]['datums'])==1
    def mean(values): return statistics.mean(values) if values else None
    def median(values): return statistics.median(values) if values else None
    q = m['DENL1:discharge']
    now, old = q['current']['values'], q['antecedent_72h']['values']
    current_known = known(q,'current',1)
    old_known = known(q,'antecedent_72h',1) and q['current']['datums']==q['antecedent_72h']['datums']
    elevated = current_known and min(now)>=t['discharge_high_cfs']
    rise = min(now)-max(old) if current_known and old_known else None
    ratio = min(now)/max(old) if rise is not None and max(old)>0 else None
    rising = rise is not None and rise>=t['discharge_rise_cfs'] and ratio is not None and ratio>=t['discharge_ratio']
    river = _state(elevated or rising, current_known and (elevated or old_known))
    q_metrics = dict(current_median_cfs=median(now), antecedent_median_cfs=median(old),
                     conservative_72h_rise_cfs=rise, rise_rate_cfs_per_hour=rise/72 if rise is not None else None,
                     conservative_ratio=ratio, elevated_discharge=bool(elevated), rising_discharge=bool(rising))
    changes = {}
    flags = {'river':river}
    for key, flag, minimum in [('NWCL1:residual','residual',t['residual_rise_ft']),
                                ('MDLL1:stage','lake',t['lake_rise_ft']),
                                ('MCHL1:stage','pass_context',t['lake_rise_ft'])]:
        item = m[key]
        cv,bv = item['current']['values'], item['baseline']['values']
        complete = known(item,'current',1) and known(item,'baseline',t['baseline_fraction']) and item['datum_consistent']
        delta = min(cv)-median(bv) if complete else None
        positive = delta is not None and delta>=minimum
        if flag=='residual': positive = positive and min(cv)>=t['residual_ft']
        flags[flag] = _state(positive,complete)
        changes[key] = dict(current_median_ft=median(cv), baseline_median_ft=median(bv),
                            conservative_rise_native_ft=delta, current_minimum_ft=min(cv) if cv else None)
    u,v = m['NWCL1:wind_u'],m['NWCL1:wind_v']
    wind_known = known(u,'current',1) and known(v,'current',1)
    angle = math.radians(t['wind_axis_degrees'])
    projection = [x*math.sin(angle)+y*math.cos(angle) for x,y in zip(u['current']['values'],v['current']['values'])] if wind_known else []
    wind_present = wind_known and min(projection)>=t['wind_projection_knots']
    flags['wind'] = _state(wind_present,wind_known)
    pairs = list(zip(u['current']['values'],v['current']['values'])) if wind_known else []
    unit_vectors = [(x/math.hypot(x,y),y/math.hypot(x,y)) for x,y in pairs if math.hypot(x,y)>1e-9]
    mean_u,mean_v = mean(u['current']['values']),mean(v['current']['values'])
    wind_speed = math.hypot(mean_u,mean_v) if wind_known else None
    persistence = math.hypot(mean([x for x,y in unit_vectors]),mean([y for x,y in unit_vectors])) if unit_vectors else None
    direction = (math.degrees(math.atan2(-mean_u,-mean_v))+360)%360 if wind_speed and wind_speed>1e-9 else None
    observed_water = {key:dict(current_median_ft=median(m[key]['current']['values']),
                               current_valid_fraction=m[key]['current']['fraction'],datum=m[key]['current']['datums'])
                      for key in ('NWCL1:water','NWCL1:prediction')}

    flags['coastal'] = _combine([flags['residual'], flags['lake'],flags['wind']])
    target = m['MAUL1:stage']
    target_known = known(target,'current',1) and known(target,'baseline',t['baseline_fraction']) and target['datum_consistent']
    target_change = median(target['current']['values'])-median(target['baseline']['values']) if target_known else None
    flags['response'] = ('detected' if target_change>=.25 else 'not_detected') if target_known else 'uncertain'
    support = [f'{k}: persistent observational support' for k in ('river','residual','lake','wind','pass_context') if flags[k]=='present']
    missing = [f'{k}: insufficient valid coverage, quality or datum continuity' for k in ('river','residual','lake','wind','pass_context') if flags[k]=='unknown']
    contradictory = []
    if flags['residual']=='present':
        for k in ('lake','wind'):
            if flags[k]=='absent': contradictory.append(f'Positive residual lacks {k} support in the same six-hour interval')
    if flags['river']=='absent': contradictory.append('No qualifying DENL1 discharge level/rise; this does not exclude downstream river inputs')
    required = ('river','residual','lake','wind')
    coverage = {k:{part:{name:val for name,val in item[part].items() if name!='values'} for part in ('current','baseline','antecedent_72h')}
                for k,item in m.items()}
    selected = category(flags['river'],flags['coastal'])
    return dict(issue_time_utc=iso(issue), latest_completed_bin_end_utc=iso(issue),
                max_observation_bin_start_utc=iso(issue-HOUR),
                feature_start_utc=iso(issue-dt.timedelta(hours=72+t['persistence_hours'])),
                category=selected, flags=flags, coverage_sufficient=all(flags[k]!='unknown' for k in required),
                metrics=dict(discharge=q_metrics, lake_changes=changes, observed_water_and_prediction=observed_water,
                             wind=dict(u_mean_knots=mean(u['current']['values']),v_mean_knots=mean(v['current']['values']),
                                       projected_minimum_knots=min(projection) if projection else None,
                                       axis_toward_degrees=t['wind_axis_degrees'],
                                       speed_of_mean_vector_knots=wind_speed,direction_from_degrees=direction,
                                       directional_persistence=persistence),
                             target_change_native_ft=target_change), coverage=coverage,
                supporting=support, contradictory=contradictory, missing=missing,
                explanation=f'{selected}: river={flags["river"]}; coastal={flags["coastal"]} requires residual={flags["residual"]}, independent lake={flags["lake"]}, wind={flags["wind"]}.',
                uncertainty=['Evidence supports forcing consistency, not hydrodynamic attribution or a predicted response.',
                             'DENL1 cannot observe all downstream tributary and local runoff; absent upstream evidence does not exclude river influence.',
                             'Native station changes only; historical MAUL1 stage is not NAVD88.',
                             'Valid-time-only replay; original receipt timestamps and operational availability are unverified.'])


def assess(index, issue, thresholds=None):
    t = DEFAULTS | (thresholds or {})
    return decide(metrics(index,issue,t['persistence_hours']),issue,t)
