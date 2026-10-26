# Phase 6.17 prospective evidence readiness

**Scope:** research / shadow evaluation only. This view summarizes existing authentic prospective issues and verification output. It is not an operational forecast, warning, advisory, or promotion decision. It excludes historical hindcasts from prospective counts.

## What the current records support

The initial latest-main snapshot was evaluated from `site/data/prospective/history/index.json`, `performance.json`, `latest.json`, and the immutable issue and verification files as of `2026-10-26T12:24:53Z`.

- There are 43 authentic issue records. The three horizons each have 43 issued target slots. Per model, the 6h horizon has 42 matured and verified pairs, 12h has 40, and 24h has 37. There are no due-but-unverified pairs in this snapshot. One 6h, three 12h, and six 24h issue targets are not yet due; those are target slots, while totals across five model-target pairs are 5, 15, and 30.
- These target pairs overlap in time across hourly issues and model variants. They are paired forecast outcomes, not 42/40/37 independent samples, independent storms, or independent event groups.
- The existing outcome rule finds one qualifying group of native-stage rise targets at or above 0.50 ft in a 24h window, merging consecutive qualifying target windows no more than 24h apart. The existing five-group display/suppression rule therefore withholds event detection and significant-rise event misses. A grouped outcome target is not a physical onset time or proof of statistical independence.
- Current model-vs-persistence paired errors are computed only when the model and persistence records match on issuance, horizon, observation valid time, and observed value. The dashboard displays paired N, MAE, RMSE, bias, and model-minus-persistence differences. Negative MAE/RMSE differences mean lower error on the matched pairs. These descriptive values do not establish prospective skill.
- Existing outputs count threshold false alarms by individual issue-target pair. They do not define a false-alert episode grouping, so the readiness panel labels episode counts “not computed.”
- Latest issue input availability reports DENL1, MDLL1, MAUL1 00065 and 63160, and NWCL1 as eligible; MCHL1 is missing. The recorded ages at that issue were about 0.664h for DENL1, MDLL1, and both MAUL1 parameters, and 0.514h for NWCL1. Availability of direct 63160 is reported separately; 63160 remains outside model features. Target observation capture delay, where the valid and ingestion timestamps are both present, is summarized separately: median/P90 71/259 minutes for 6h (`n=42`), 149/273 minutes for 12h (`n=40`), and 74/154 minutes for 24h (`n=37`). This is valid-time-to-ingestion delay, not source-specific latency.

For that initial snapshot, 6h Phase 5A coastal had MAE 0.180 ft versus persistence 0.199 ft, but RMSE 0.572 ft versus persistence 0.565 ft and bias +0.113 ft. At 12h, Phase 5A MAUL1-only had MAE 0.102 ft versus persistence 0.138 ft. At 24h, Phase 5B coastal+tide had MAE 0.187 ft versus persistence 0.231 ft, with six pairwise ≥0.50-ft false alarms. Those are descriptive results for that snapshot, not a basis to select or promote a model.

## Latest-main update

The repository's latest main now contains later authentic issue and verification records. Recomputing from that state (`performance.json` as of `2026-10-26T13:32:37Z`, latest actual issue `2026-10-26T13:32:35Z`) gives 45 authentic issuances. Verified model-persistence pairs per horizon are 42 at 6h, 41 at 12h, and 37 at 24h. There are zero due-but-unverified model-pairs. Three, four, and eight issue windows respectively are not yet due (15, 20, and 40 model-target pairs across five models). These overlapping targets remain dependent.

The latest summary records zero qualifying ≥0.50-ft/24h target groups. Event detection and significant-rise misses therefore remain suppressed below the existing five-group rule. The prior 12:24 snapshot reported one group; the later immutable verification revisions and refreshed performance summary supersede that count for current evaluation. No earlier issue or verification revision is rewritten.

The latest issue records DENL1, MDLL1, MAUL1 00065 and 63160 as eligible at about 0.793h age, NWCL1 eligible at 0.743h, and MCHL1 missing. Target observation capture delay median/P90 is 77/325 minutes at 6h (`n=42`), 145/273 minutes at 12h (`n=41`), and 74/154 minutes at 24h (`n=37`). These are valid-time-to-ingestion delays, not source-specific latency.

Current exact paired model/persistence values (ft; model/persistence; same observation valid time and value) are:

| Horizon | Model | Paired N | MAE | RMSE | Bias | ≥0.50-ft false-alarm pairs |
|---|---|---:|---:|---:|---:|---:|
| 6h | Phase 5A MAUL1-only | 42 | 0.088 / 0.083 | 0.129 / 0.111 | -0.005 / -0.045 | 0 |
| 6h | Phase 5A coastal | 42 | 0.093 / 0.083 | 0.132 / 0.111 | +0.065 / -0.045 | 0 |
| 6h | Phase 5B coastal+tide | 42 | 0.096 / 0.083 | 0.136 / 0.111 | +0.066 / -0.045 | 0 |
| 6h | Phase 5B full | 42 | 0.096 / 0.083 | 0.136 / 0.111 | +0.069 / -0.045 | 0 |
| 12h | Phase 5A MAUL1-only | 41 | 0.104 / 0.135 | 0.140 / 0.158 | -0.048 / -0.083 | 0 |
| 12h | Phase 5A coastal | 41 | 0.182 / 0.135 | 0.250 / 0.158 | +0.114 / -0.083 | 8 |
| 12h | Phase 5B coastal+tide | 41 | 0.184 / 0.135 | 0.253 / 0.158 | +0.107 / -0.083 | 8 |
| 12h | Phase 5B full | 41 | 0.183 / 0.135 | 0.251 / 0.158 | +0.121 / -0.083 | 8 |
| 24h | Phase 5A MAUL1-only | 37 | 0.207 / 0.219 | 0.251 / 0.270 | -0.206 / -0.199 | 0 |
| 24h | Phase 5A coastal | 37 | 0.176 / 0.219 | 0.242 / 0.270 | +0.019 / -0.199 | 7 |
| 24h | Phase 5B coastal+tide | 37 | 0.174 / 0.219 | 0.250 / 0.270 | +0.004 / -0.199 | 6 |
| 24h | Phase 5B full | 37 | 0.179 / 0.219 | 0.250 / 0.270 | +0.036 / -0.199 | 7 |

These small, overlapping samples show mixed results: 6h candidates have higher error than persistence, 12h MAUL1-only has lower error while coastal/tidal models have higher error, and 24h candidates have lower MAE while retaining pairwise false alarms. No horizon has 50 pairs, the existing event count is below five, and all remain far below the proposed 100-pair and 20-group gates. The readings are not independent-skill evidence or a promotion result.

MAUL1 USGS 00065 remains native gage height, not NAVD88. Only verified direct 63160 can be compared with 4.0 ft NAVD88. The 63160 value remains outside model features. The Phase 6.16 timing erratum is retained: the first immutable authentic issue’s targets are 53m11s later than the Phase 5 hourly target grid. The panel does not retime it; its actual issue time and feature anchor remain distinct.

## Deterministic update path

The page derives the panel from the workflow-maintained `history/index.json`, `performance.json`, `latest.json`, the linked immutable verification revisions, and the separate gate configuration. New verification revisions update the existing performance summary; a page load then deterministically selects each pair’s latest revision and rebuilds the display. The panel does not write to the archive or replace any evidence file. Exact paired model/persistence metrics are calculated from identical valid-time and observed-value references. Missing or unreadable records lower the available paired N; they are never filled in.

Paired MAE/RMSE/bias values are calculated in the browser from the linked immutable verification revisions. No additional fields are written into `performance.json` for this panel.

## Proposed challenger-readiness gates

`site/phase6-readiness-gates.json` holds editable thresholds. Its owner approval status is explicitly `pending`; the panel reports that state and does not claim the gates are active. These thresholds are proposed research-readiness criteria and require owner approval before activation.

1. At least 100 exact verified issue-target pairs per horizon for a candidate and each comparator. This is a minimum coverage volume; overlapping targets remain correlated.
2. At least 20 observed ≥0.50-ft/24h groups under the existing grouping rule. The existing five-group suppression threshold remains unchanged; 20 is a stricter proposed promotion-readiness floor, not a changed detector.
3. At least 5% paired MAE improvement versus both persistence and the frozen Phase 5A MAUL1-only baseline on every horizon, with a 95% paired block-bootstrap interval for model-minus-baseline error excluding zero. The proposed interval uses fixed, non-overlapping UTC calendar-week blocks (Monday 00:00 through the next Monday 00:00); this method is specified for future evaluation and is not applied to the current summary.
4. Absolute bias no greater than 0.05 ft per horizon and RMSE no more than 5% above the best baseline.
5. At least 20 paired cases in each predeclared source-availability and MAUL1 input-age stratum, with no more than 10% MAE regression versus the best baseline within a stratum.
6. If an interval is reported, at least 50 paired targets and observed coverage between 70% and 90% for the nominal 80% interval. This is coverage evidence, not a flood probability.
7. A separately reviewed prospective shadow evaluation, immutable provenance, and explicit owner approval before any promotion discussion. No automated gate pass authorizes deployment or operation.

The gates do not define storm independence from hourly pairs and do not count a repeated hourly false alarm as a separate episode. Candidate-specific performance, paired uncertainty intervals, and event-stratified checks remain uncomputed until a challenger is independently specified and reviewed.

## Reproduction and limits

- Python metric tests: `python -m unittest tests.test_phase6_core -v`
- Browser summary tests: `node tests/phase6-readiness-smoke.cjs`
- Integrated Phase 6 smoke: `node --check site/phase6-readiness.js && node --check site/phase6.js && node tests/phase6-site-smoke.cjs`

The panel can summarize only the recorded issue, verification, source-age, and ingestion fields. It cannot recover absent receipt times, missing MCHL1 observations, or independent event information that the archive does not contain. No historical authentic issuance, verification revision, source capture, model artifact, or computed historical performance file was edited for this view.
