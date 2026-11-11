# Design B — Rebuild the Experience

**Status:** proposal and panel map; implementation is on the independent branch `codex/ui-revamp-b-experience`.  
**Production UI baseline inspected:** `e236d8946fe7acbfb764f1ba60960f9bb806881e` (2026-10-26T15:03:15Z).  
**Frozen data snapshot:** `57e4517f353d38056c761125c78331308d67e317` (2026-10-26T14:00:50Z), the exact source/data snapshot identified by Design A’s screenshot provenance in `docs/phase6-18-ui-redesign.md`.  
**Preview goal:** standalone, static Design B at `/MAUL1-Preview-B/`; no production publication, workflow, or data writes.

## Intent and experience

Tell the existing research as one question in three acts: **What is MAUL1 doing now? Is prospective guidance demonstrating skill? What do historical studies say about river versus coastal influence?** Keep those questions visible in the navigation and preserve the unresolved attribution.

Use a refined light research-folio theme: warm paper background, dark ink, restrained lake/river tones, editorial serif section titles, sans-serif labels and values, generous whitespace around scientific interpretation. The presentation should feel like a field atlas and research narrative, not a conventional dashboard. Statuses use text plus shape/icon and color; colors never carry meaning alone. No animation beyond reduced-motion-safe interface transitions.

### Approaches

1. **Recompose the existing UI renderers inside a new three-act shell (selected).** Preserve the existing forecast, verification, historical, performance, and Model Lab rendering/calculation code. Move the view containers conceptually into three acts and supply the expected IDs. Use a small B-only navigation/data-URL adapter and a new B stylesheet. This changes presentation while keeping the tested scientific renderers and values.
2. **Reimplement every chart and scorecard in a new renderer.** Rejected because it duplicates mature scientific display/eligibility logic and increases divergence risk.
3. **Copy the whole production site and all repository data.** Rejected because it needlessly duplicates the archive and brings production workflows and automatic updates into the preview.

## Content and interaction design

- **Act I — Now:** persistent research-only band; native MAUL1 00065 stage, source freshness and valid/retrieved times; supported six-hour tendency; 6/12/24-hour forecast cards with actual issue, valid time, effective lead, model identities and recorded withheld states. Keep the trajectory visible without disclosure. Show an uncluttered, coordinate-based station map using only the existing verified station positions; no connecting arrows, travel times, or causal flow lines. MCHL1 is a hollow/outlined HADS-reported location labeled **shadow-only; sensor identity and datum unverified**. The map caption says locations alone do not establish hydrologic pathways or cause.
- **Act II — Is it working?:** lead with sample maturity, paired verified issue-target N by horizon, due-but-unverified and not-yet-due counts, qualifying groups, and unmet evidence gates. Show prospective model versus persistence scores and all adverse/mixed values up front. Label each score with paired N and evidence stage. Clearly separate the reused historical Phase 5A/5B benchmark summaries from prospective results; identify temporal holdout, issue-window overlap, and source receipt-time limitations.
- **Act III — What did we learn?:** historical event atlas with one UTC replay control and synchronized station charts; event response/onset, lag, archive coverage, quality/missingness, Phase 3B/Phase 4/Phase 5 reports, and linked source/methodology documents. Give the strict Phase 8 screen result a prominent evidence card: 3 of 179 known-onset events with unique strict-composite credit, zero within 24 hours; present its retrospective/non-causal limits adjacent to the count. Place Model Lab and significant-rise explorations in subsections, preserving selectors, paired comparisons, cases, event failures, predictor diagnostics, and the explicit explanation of why the challenger remains unpromoted.

### Complete existing-panel map

Every existing section remains present, linked, and usable. The preview preserves all current IDs as anchors so old hashes resolve to the corresponding act/section.

| Existing view / panel | Design B placement |
|---|---|
| Current Forecast; authentic issue/source snapshot; current conditions | Act I, immediate station-condition story |
| Current 6/12/24 experimental guidance; model details; trajectory chart | Act I, always-visible forecast summary, with all current model rows reachable in a detail table |
| Current forecast archive-cycle health and forecast provenance | Act I, issue/freshness strip and disclosure |
| Prospective Forecast Verification and per-issuance history/revisions | Act II, verification timeline and expandable issuance detail |
| Prospective performance scorecard, maturity, rise counts, intervals, input-age effects, delay, event groups | Act II, maturity first; full scorecard retained |
| Forecast Performance Explorer and its controls/charts | Act II, paired-sample comparison section |
| Historical event selector and replay-through-time control | Act III, shared UTC replay bar |
| Station network/map | Act I overview and Act III detailed station map (same verified positions and status wording) |
| DENL1 discharge; NWCL1 observed/predicted/residual water level; MDLL1; MCHL1; MAUL1 native/NAVD88; NWCL1 wind charts | Act III synchronized station-chart grid, preserving existing axes, gaps, markers, hover and unit/datum distinctions |
| Experimental event onset; independent event verification; interpretation | Act III event evidence |
| Legacy exploratory lag; coverage/quality; historical coverage; continuous discovery | Act III diagnostics and data coverage |
| Phase 3B validation, event/control summaries and report links | Act III historical response evidence |
| Phase 4 forcing evidence, case classifications and reports | Act III pathway evidence, indeterminate labels retained |
| Phase 5A hindcasts and Phase 5B tidal-aware robustness / astronomical-availability caveat | Act II compact historical benchmark context and Act III full reports; never merged with prospective metrics |
| Model Lab paired models, annual/seasonal results, ablations, rises/false alarms, missingness, trajectory, selected case, event failures | Act III Model Lab; all selectors, tables, case plots and provenance retained |
| Significant-Rise Investigation: horizon tradeoffs, event explorer, predictors, diagnosis and limitations | Act III dedicated investigation section |
| Existing methods, data/source links, frozen model artifact links, and reports | Remain reachable from the relevant Act II/III evidence section as commit-pinned GitHub links |

## Data, hosting, and scientific boundaries

- The app records both the UI source baseline and the frozen data snapshot in `preview-b/snapshot.json`. It reads only unchanged JSON and compressed event JSON from the immutable `57e4517` GitHub raw URLs. No archive is copied into or regenerated by B; there is no latest/main alias, polling, synchronization, collector, API write, or transform. Runtime requests are limited to the pinned paths used by the existing views. Reports link to commit-pinned source paths.
- All app assets use relative paths under `/MAUL1-Preview-B/`; the small data adapter maps existing `data/...` fetch calls to the pinned snapshot URLs. Navigation accepts both the three new act anchors and the existing four view hashes.
- The only external runtime libraries are the already-used Plotly and Leaflet versions; no framework/build chain, analytics, paid service, server, or new dependency is introduced. The station overview itself uses inline SVG and needs no tile service.
- Every view remains **Design B — Rebuild the Experience / Research-Only Preview** and **RESEARCH / SHADOW EVALUATION / NOT OPERATIONAL**.
- Native 00065 gage height remains separate from direct 63160 NAVD88. No 4.0-ft NAVD88 line may appear on native 00065, no conversion/gradient is inferred, and missing data stays missing.
- MCHL1 stays shadow-only; the reported HADS location must not be represented as proof of sensor identity or datum. The strict Phase 8 statistic, Phase 6 timing, independent-group caveats, model intervals, and model-spread caveats stay attached to the values.
- No forecasts, metrics, scientific thresholds, source evidence, model artifacts, verification revisions, or archive files are edited or recomputed.

## Planned validation and outputs

Before the implementation commit, the draft PR will contain this proposal and mapping. Then implement in `preview-b/` and add `site/DESIGN.md` documenting B’s tokens, components, series colors, and science boundaries. Run existing Node smoke tests and the full Python suite; add B-specific navigation, URL-root, data-pin, integrity/read-only, chart contract, and scientific-label checks. Check at desktop 1440px and mobile 390px for overflow, keyboard navigation, deep-link compatibility, reduced motion, and text equivalents. Capture desktop/mobile screenshots for all three acts, and compare exact source-file SHA-256 values for each data input against the frozen source snapshot.

**Publishing limitation:** the connected GitHub tools can create branches/files/PRs in this repository but expose no repository-creation or Pages-administration action. The local GitHub CLI has an invalid token, and direct network access is blocked in this workspace. Therefore Design B will be delivered as a downloadable standalone static artifact unless the preview repository can be created/configured through a newly available authorized path. A preview URL will be reported only after its deployment is confirmed.
