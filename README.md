# MAUL1 Coastal Influence — historical research

A static, public event explorer for investigating how upper-Amite runoff and Lake Pontchartrain setup relate to water-level rises at MAUL1. **Research only.** The local project threshold is **4.0 ft NAVD88**. This repository does not forecast flooding, estimate causal percentages, or recommend advisories.

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
python scripts/build.py                    # all seven first-pass historical events
python scripts/build.py beta-2020          # one event
python -m unittest discover -s tests -v
python -m http.server 8000 --directory site
```

Open `http://localhost:8000`. Historical backfill is manual in Actions; site validation/deployment runs on main. Data are committed as event JSON, not a fabricated gap-free time grid. All valid times are UTC. CO-OPS wind direction is meteorological FROM; `wind_u` and `wind_v` are converted per raw observation before any averaging. Wind direction is never averaged numerically. Replay filters observations by valid time, **not** original receipt time, which is unavailable for these archives.

## Known limits

* The first archive covers the seven requested storm windows and three exploratory non-tropical windows, each with at least 72 hours around the core storm. It does not yet constitute complete continuous 2016–2026 coverage or a validated event census.
* MCHL1 HADS observations were recovered for the 2024–2025 windows. No MCHL1 data were found for the seven early event windows. Its vertical-datum history remains unresolved and the instrument must not be merged with PMPL1 or nearby USGS records.
* MAUL1 direct 63160 NAVD88 begins in 2026; these historical event windows show native gage-height changes, not verified threshold exceedances. The 2016 archive has substantial gaps at MAUL1.
* No river-versus-coastal classification has passed independent event review. The site conservatively labels every event indeterminate.
* No lag estimate is accepted as universal. A 2020 published peak time difference does not by itself establish advance detection.
* The browser loads Plotly, Leaflet and OpenStreetMap tiles from public third-party CDNs; those resources and GitHub Pages must be reachable.

See [methodology](docs/methodology.md) for the physical logic and research gates. To publish, set repository **Settings → Pages → Build and deployment → Source: GitHub Actions**. The workflow uses the GitHub Pages environment and the `site/` artifact.
