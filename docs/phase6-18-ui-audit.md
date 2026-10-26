# Phase 6.18 UX and visualization audit

**Audit baseline:** `main` at `57e4517f353d38056c761125c78331308d67e317` (2026-10-26).  
**Scope:** Forecast Verification, Historical Research, and Model Lab markup, rendering code, CSS, committed data contracts, methodology, and existing smoke tests. This is a source/data review, not a rendered browser or assistive-technology study.  
**Disposition:** Recommendations only. No shared UI, scientific outputs, forecast values, metrics, thresholds, or immutable records are changed by this audit.

The items below are ordered by risk to correct interpretation and task completion. For each, the acceptance criterion is for a later implementation PR.

## Ten prioritized improvements

### 1. Make the prospective scorecard scannable without hiding its evidence

- **Where:** Forecast Verification, `site/phase6.js` `showMetrics()` and the `#phase6-content` scorecard; `.table-wrap` in `site/research-dashboard.css`; `tests/phase6-site-smoke.cjs`.
- **Problem / benefit:** Thirteen columns combine point error, persistence comparison, three rise thresholds, interval diagnostics, input age, latency, maturity, and grouped-event results. Horizontal scrolling keeps the page width contained, but makes model-to-model reading and remembering the header difficult, especially on a phone.
- **Plan:** Present one horizon at a time or group rows by horizon, keep the core comparison (model, verified N, MAE, RMSE, bias, persistence comparison) in the first view, and place secondary diagnostics in clearly labeled detail rows/panels. Keep all existing fields available.
- **Preserve:** Do not recalculate, filter, rank, or suppress any metric or model. Keep the existing matched issue-target cohort semantics.
- **Acceptance:** At 375 CSS px, no page-level horizontal overflow; all 13 existing fields remain reachable with their labels and units; keyboard users can reach and operate each detail region. Add assertions to `tests/phase6-site-smoke.cjs` for labels and the retained data fields.

### 2. Distinguish immature, missing, and unscored prospective evidence

- **Where:** Forecast Verification `site/phase6.js` (`showMetrics`, `showVerification`); readiness summary `site/phase6-readiness.js` and `site/phase6-readiness-gates.json`; `site/data/prospective/history/index.json`, `site/data/prospective/performance.json`; `tests/phase6-dashboard-smoke.cjs` and `tests/phase6-readiness-smoke.cjs`.
- **Problem / benefit:** The scorecard packs verified/matured, due-unverified, and not-yet-due counts into one cell. When an aggregate is absent, its row says “no matured archived outcomes yet,” which can conflate zero mature outcomes with a metric that is unavailable or withheld. A researcher needs to know whether to wait, inspect source coverage, or interpret a computed score.
- **Plan:** Give the evidence lifecycle its own compact, dated status summary per horizon (issued, matured, verified, due but unverified, not yet due, and score withheld/unavailable). Keep “not yet due” separate from a missed source and from a suppressed event metric.
- **Preserve:** Statuses must derive only from existing archive/index/report fields. Do not impute a reason for due-but-unverified observations or change maturity rules.
- **Acceptance:** Fixtures for zero mature, mature-but-unverified, verified, metric withheld, and unavailable report states render distinct plain-language labels and counts; the sum and labels reconcile to the source fixture without changing any score. A “last updated/as of” time is visible and UTC-labeled.

### 3. Keep overlapping hourly cases separate from independent event evidence

- **Where:** Forecast Verification `site/phase6.js` scorecard and event text; Historical Research `site/app.js` `renderVerification()`; Model Lab `site/model-lab.js` event sections; `docs/phase6-methodology.md`, `docs/model-lab-methodology.md`.
- **Problem / benefit:** The views contain both issue-target pair counts and grouped rise/event counts. Current explanatory paragraphs note overlap, but the denominators sit far apart from the numbers. Readers can mistake thousands of correlated hourly forecasts or repeated qualifying targets for independent storms.
- **Plan:** Pair each row-level N with “overlapping issue-target pairs” and each event result with its event/group N and grouping definition. Keep event lead described as lead to the first qualifying target, not physical onset.
- **Preserve:** Retain outcome-defined group rules, the five-group withholding rule, existing event IDs and all current computed values. No new independence claim.
- **Acceptance:** A fixture containing multiple hourly forecasts in one group shows the pair count and group count separately; screen and accessible text state that the pair rows overlap and that target-time groups are not necessarily independent physical events. Existing five-group withholding tests remain green.

### 4. Make an issuance’s verification revisions auditable in the UI

- **Where:** Forecast Verification `site/phase6.js` `showVerification()`, `#phase6-selected`; archive entries in `site/data/prospective/history/index.json` and files in `site/data/prospective/verification/`; `tests/phase6-site-smoke.cjs`.
- **Problem / benefit:** The selected-issuance table shows model/horizon, forecast time, observed time/stage, error, and revision number, but not the archived observation-ingestion delay or a clear distinction between the forecast target time and the matched observation time. Provenance/QC fields are not present in this verification record shape, so their absence can be mistaken for verified source quality.
- **Plan:** Label target time and observed valid time distinctly; show stored ingestion/revision timestamps and a simple delay where available. Mark source/QC as “not recorded in this verification record” rather than inferring it. Make revision history easy to scan.
- **Preserve:** Display the archived values verbatim; never merge revisions, replace an observation, or infer missing provenance. Forecast and verification files remain separate and immutable.
- **Acceptance:** A multi-revision fixture displays every revision in order, exposes target/observed/ingested timestamps distinctly, and explicitly identifies unavailable source/QC metadata without inventing fields or changing error values.

### 5. Make historical replay genuinely UTC and align the chart window to the cutoff

- **Where:** Historical Research toolbar in `site/index.html` (`#replay` “Replay through UTC”); `site/app.js` `render()`; `tests/site-smoke.cjs` and a focused replay test.
- **Problem / benefit:** A `datetime-local` control is labeled UTC, and `app.js` appends `Z` to its value. The control is displayed in browser-local time, so users outside UTC can enter a wall time that is interpreted as UTC. Replay filters observations by valid time, but the charts retain the full event’s x-axis range, leaving an unexplained empty future tail.
- **Plan:** Use a UTC-explicit entry/display convention or convert browser-local input correctly and show the resolved UTC timestamp. When replay is active, end the synchronized chart range at the cutoff while retaining the full event range after reset.
- **Preserve:** Replay remains valid-time limited. Never claim historical source receipt time or use replay as an operational hindcast; do not alter the underlying event data.
- **Acceptance:** Tests with UTC and non-UTC browser timezones resolve the same explicitly entered UTC instant; no plotted point is later than the cutoff; all synchronized panels end at the same cutoff; reset restores the full event extent.

### 6. Improve historical chart series identity, units, and datum separation

- **Where:** Historical Research chart builders/layouts in `site/app.js` (`line()`, `traces()`, `render()`); panel labels in `site/index.html`; `tests/site-smoke.cjs` and a focused chart-contract test.
- **Problem / benefit:** The generic hover template shows time and value but omits units and datum/source context. The NWCL1 plot places observed and astronomical MLLW levels beside the observed-minus-predicted residual on one axis, making the much smaller residual harder to inspect. MAUL1 combines native gage height and direct NAVD88 on separate axes, an important distinction that currently depends on surrounding explanatory prose.
- **Plan:** Include station, variable, units, datum, and valid time in hover/accessible descriptions; give the residual a clearly labeled zero reference and a legible scale or separate aligned panel; identify the native and NAVD88 axes and threshold applicability directly at the chart.
- **Preserve:** Do not convert datums, infer gradients, bridge gaps, or change threshold eligibility. Keep the existing 90-minute gap breaks and the direct-NAVD88-only 4.0-ft rule.
- **Acceptance:** A chart-contract test verifies each trace has a scientifically correct unit/datum label; residual zero is visible; the 4.0-ft line is only on the direct NAVD88 axis; a gap over 90 minutes still renders as a break.

### 7. Reduce navigation and comparison friction in the long Historical Research view

- **Where:** Historical Research structure in `site/index.html` (`#historical-research-view`, `details.history-group`, six chart panels, verification and coverage sections); `site/app.js`; `site/navigation.js`.
- **Problem / benefit:** The view places station plots, a map, onset diagnostics, event verification, coverage, discovery, and Phase 3B/4/5 reports in one long sequence. The single event selector and replay control apply globally, but their effect and the transition from observation display to analytical summaries are easy to lose while scrolling.
- **Plan:** Add a compact event-context/navigation summary with in-page links to observations, timing diagnostics, coverage, and historical model evidence. Keep event and replay selection visibly persistent or repeatable. Use progressive disclosure for secondary methodology/report detail, consistent with the existing disclosure pattern.
- **Preserve:** Keep all current observations, panels, report links, event definitions, and caveats reachable. Do not elevate exploratory lag or onset matches to validated skill.
- **Acceptance:** From the top of the view, keyboard and pointer users can jump to and identify each evidence section; changing the event or cutoff updates every relevant panel and summary; the selected event/cutoff remains visibly identified.

### 8. Clarify Model Lab model families, paired denominators, and comparison direction

- **Where:** Model Lab controls/tables in `site/index.html`; `site/model-lab.js` (`LABELS`, `metricTable()`, `render()`); `site/model-lab.css`; `site/data/research/model-lab.json`; `tests/model-lab-smoke.cjs`.
- **Problem / benefit:** Six model rows span persistence, Phase 5A, Phase 5B, and a challenger. Their names differ from the labels in prospective verification, while the main table combines eligible count, scored N, abstentions, MAE/RMSE/bias, persistence skill, and two improvement intervals. The reader must infer which comparisons use common cases and what positive interval values mean.
- **Plan:** Group models by baseline/Phase family/challenger; provide a compact, consistent model glossary shared across the three views. State paired cohort, N, excluded/abstained count, lower-is-better direction, and the signed definition of each improvement interval adjacent to the table. Keep the current horizon and regime selectors.
- **Preserve:** Do not reorder based on outcome, re-score rows, change model names in source records, or alter paired cohort calculations and uncertainty.
- **Acceptance:** Each model maps to one consistent display label while preserving its schema key; table explanation defines the sign of improvement intervals and the paired cohort; tested N and all values match the report fixture exactly after each selector change.

### 9. Keep retrospective evidence and outcome-selected illustrations unmistakable during interaction

- **Where:** Model Lab `site/index.html` (`#model-lab-status`, evidence banner, selectors and selected-case section); `site/model-lab.js` (`render()`, `renderCase()`); `docs/model-lab-methodology.md`; `tests/model-lab-smoke.cjs`.
- **Problem / benefit:** The view correctly describes the reused 2023-onward sample as not pristine and labels cases outcome/error selected, but those caveats are distributed between introduction, status text, case note, and separate methodology. After changing horizon, regime, or case, a chart can be read without the evidence boundary in view.
- **Plan:** Keep a compact persistent “Retrospective / reused development evidence” label with the selected horizon/regime and the case’s selection basis adjacent to outputs. Distinguish retrospective NOAA-valid-time sensitivity from issue-time-available predictors at the point of comparison.
- **Preserve:** Do not imply prospective skill, source receipt-time availability, causal pathway, or promotion. Do not change challenger gates or the frozen Phase 6 models.
- **Acceptance:** After every selector change, the visible and screen-reader status still identifies the result as reused retrospective evidence; selected case text states why it was selected; any NOAA astronomical sensitivity is marked retrospective-only in its table/legend.

### 10. Set explicit mobile and accessibility acceptance for tables, charts, and tabs

- **Where:** Cross-view markup in `site/index.html`; chart renderers `site/app.js`, `site/phase6.js`, `site/model-lab.js`; `site/style.css`, `site/research-dashboard.css`, `site/model-lab.css`; tests `tests/navigation-forecast-smoke.cjs`, `tests/site-smoke.cjs`, `tests/phase6-site-smoke.cjs`, `tests/model-lab-smoke.cjs`.
- **Problem / benefit:** Tabs have keyboard support and several wide tables are scroll regions, but historical Plotly chart containers have no data-summary fallback, and the historical verification episode table is rendered without the scroll-region wrapper used elsewhere. Important series identity can therefore be visual-only, and that table can widen a narrow viewport.
- **Plan:** Give each chart a concise text/table equivalent describing plotted series, units/datum, time range, and missing-data state; make every wide table a labeled, keyboard-scrollable region with semantic headers; retain visible focus and tab announcements. Confirm responsive behavior with Agent 1’s shared patterns.
- **Preserve:** Accessible summaries must report the same committed/rendered values and status, not derive new science. Do not create parallel colors, spacing, typography, or breakpoints.
- **Acceptance:** At 320, 375, 768, and desktop widths, the document itself has no horizontal overflow (intentional table scrollers may scroll); keyboard-only navigation reaches tabs, controls, charts’ text equivalents, and every table; automated checks find labeled regions and header scopes; a screen reader can distinguish no data, missing source, and plotted zero.

## Implementation coordination and guardrails

Agent 1 is redesigning the shared design system and Current Forecast. This audit does not prescribe new colors, type, spacing, chart palette, components, or breakpoints. **Before implementation**, rebase the selected recommendations onto Agent 1’s merged branch and inspect the exact shared tokens, component patterns, focus treatment, and responsive conventions established there. Reuse those tokens and patterns across these views; do not add a second visual system. Resolve shared-file ownership with Agent 1 before touching `site/index.html`, `site/style.css`, `site/research-dashboard.css`, or any Current Forecast markup.

All proposed work is presentation and interaction only. Keep source schemas read-only; use only fields already archived and label absent provenance as absent. Do not edit `site/data/`, models, forecast/verification calculations, thresholds, authentic issue files, verification revisions, or methodology conclusions. Apply the acceptance criteria in a separately reviewed implementation PR after Agent 1’s conventions are merged.
