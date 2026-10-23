# MAUL1 Coastal Influence Research v1.0.0

A static, public research application for NWS LIX shadow evaluation of authentic prospective MAUL1 forecast guidance and coastal-versus-river observation context. **Research only; not operationally certified.** The local project threshold is **4.0 ft NAVD88**, and native USGS `00065` is not automatically comparable to it. This repository does not issue warnings, estimate flood probabilities, or recommend advisories.

**MAUL1 Coastal Influence Research v1.0.0 — Shadow Evaluation / Not Operational.** The v1.0.0 tag is held pending interactive live-site verification. See the [release changelog](CHANGELOG.md) and [Research v1.0 guide](docs/research-v1.md) for intended use, application interpretation, Phase 7–8 findings, prospective verification status, safeguards, troubleshooting and limitations.

## Network and source decisions

| Role | Identifier | Source in event archive | Vertical reference |
| --- | --- | --- | --- |
| Upstream river | DENL1 / USGS 07378500 | USGS discharge 00060 and gage height 00065 | Native cfs and gage height |
| Lake | NWCL1 / CO-OPS 8761927 | 6-minute observed water level, 6-minute astronomical prediction and wind | Station MLLW for both water series; residual is observed minus predicted |
| Midlake | MDLL1 / USGS 301200090072400 | USGS Crossover 4 gage height from 2016 onward | Native gage height; do not equate with NWCL1 MLLW |
| Pass Manchac | MCHL1 / HADS CE678A12 | Iowa Environmental Mesonet archive of NWS HADS SHEF HGIRGZZ for three later windows | Native gage height; datum not certified for absolute comparisons |
| Target | MAUL1 / USGS 07380215 | 00065 gage height and direct 63160 NAVD88 elevation where available | 00065 is unverified historically; 63160 is direct NAVD88 |

The current HADS MDLL1 identification is “Lake Pontchartrain at Crossover 4 near Mandeville 11SSW.” The historic Midlake/Causeway USGS 073802330 is a separate instrument; records are never spliced. A separate USGS station 073802302 near Pass Manchac and older USACE/PMPL1 records are **not** silently treated as MCHL1. MCHL1's site and datum history are open research questions.

## Datum hard gate

Contemporaneous MAUL1 00065 and 63160 measurements in PETSS-Plots support a present-day difference of 1.38 ft. That does **not** certify the offset for 2016–2021. The archive retains 00065 in its own gage-height reference and only marks a 4.0-ft NAVD88 line if direct 63160 measurements are present. Published NWS storm-report peaks are evidence to cross-check, not a reason to relabel historical 00065 values. NWCL1 water and predictions are fetched on the same MLLW datum and subtracted only at exact matching valid times.

## Build and inspect

Requires Python 3.10+ and network access; no Python packages.

```bash
python scripts/build.py                    # all configured historical and recent windows
python scripts/build.py beta-2020          # one event
python -m unittest discover -s tests -v
python scripts/analyze.py
python -m json.tool site/data/verification.json > /dev/null
python -m http.server 8000 --directory site
```

Open `http://localhost:8000`. Historical backfill is manual in Actions; site validation/deployment runs on main. Data are committed as compressed event JSON, not a fabricated gap-free time grid. All valid times are UTC. CO-OPS wind direction is meteorological FROM; `wind_u` and `wind_v` are converted per raw observation before any averaging. Wind direction is never averaged numerically. Replay filters observations by valid time, **not** original receipt time, which is unavailable for these archives.

## Known limits

* The first archive covers the seven requested storm windows, three exploratory non-tropical windows, and one 2026 direct-NAVD88 observation window. Storm windows include at least 72 hours around their core periods. It does not yet constitute complete continuous 2016–2026 coverage or a validated event census.
* MCHL1 retrieval is attempted for every event window. HADS MCHL1, USACE 85420, and USACE 85420LA are reported as separate sources with per-period retrieval status; no USACE record is relabeled or spliced into MCHL1. Its vertical-datum history remains unresolved.
* MAUL1 direct 63160 NAVD88 begins in 2026; the pre-2026 event windows show native gage-height changes, not verified threshold exceedances. The October 2026 window exercises the direct-NAVD88 display. The 2016 archive has substantial gaps at MAUL1.
* Phase 4 adds experimental observation-based evidence classes in a separate section and dataset. These are supporting physical screens, not independently verified causal labels; the legacy event explorer retains its conservative interpretation.
* No lag estimate is accepted as universal. A 2020 published peak time difference does not by itself establish advance detection. Historical MAUL1 00065 datum chronology remains unresolved; only direct 63160 NAVD88 values qualify for the 4.0-ft threshold. Phase 2A onset results are experimental research diagnostics, not validated forecasts.
* The browser loads Plotly, Leaflet and OpenStreetMap tiles from public third-party CDNs; those resources and GitHub Pages must be reachable.

See [methodology](docs/methodology.md) for the physical logic, Phase 2A onset diagnostics, independent Phase 2B event verification, and research gates. The generated `site/data/verification.json` keeps target episodes, predictor episodes, one-to-one timing matches, unmatched signals, coverage, datum safeguards, sensitivity checks, and the six required case-study windows separate from the raw/hourly datasets. The event page separates experimental onset timestamps from legacy correlations and labels both as research-only. To publish, set repository **Settings → Pages → Build and deployment → Source: GitHub Actions**. The workflow uses the GitHub Pages environment and the `site/` artifact.

## Phase 4 evidence research

Run `python scripts/phase4.py` to evaluate the existing archived observations without downloads. The dedicated **Phase 4 evidence evaluation** Actions job runs the full analysis twice, verifies deterministic output, and commits results before Pages deployment. See [rules and limitations](docs/phase4-methodology.md) and `site/data/history/phase4/report.md` for event/control counts, frozen sensitivity, holdout safeguards, four priority cases and separate completed-bin valid-time replay. Phase 4 produces no forecasts, probabilities, attribution percentages or advisory recommendations. Phase 5 has not begun.
