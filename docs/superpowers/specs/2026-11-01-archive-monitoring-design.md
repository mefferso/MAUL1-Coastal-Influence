# Automated archive monitoring design

## Intent

Provide low-cost, repeatable daily archive health and weekly scientific-readiness reports for the Research / Shadow Evaluation / Not Operational archive. The reports should distinguish eventual observation coverage from values actually acquired by authentic Phase 6 issue time, and should describe scheduled workflow execution separately from provider health.

## Goals and safeguards

- Reuse `scripts/archive_completeness.py`, archived health reports, immutable receipts, Phase 6 issuance/verification files, and the existing safe publisher.
- Keep reports small, deterministic for a report date, and outside the Pages build path.
- Preserve all receipts, raw payloads, Phase 5 artifacts, and Phase 6 forecasts.
- Do not interpolate long gaps, mix station datums, or claim forecast validation from counts alone.
- Run a daily health report and a weekly readiness report using GitHub Actions only; archive only changed report files.

## Approaches

1. **Extend the collector workflow only.** This would avoid another workflow but run the historical/API/storage audit hourly and mix monitoring with source collection. It also cannot report dates when the collector did not execute.
2. **Add a separate daily/weekly monitor that reuses archive code (chosen).** It can inspect Actions history even when collection did not run, keep the provider workflow focused, and write one small report per day/week. GitHub Actions API access uses its free `GITHUB_TOKEN`; failure to read history is reported as insufficient evidence.
3. **Use an external monitoring service.** This adds an external dependency and is unnecessary for the requested cadence.

## Design choices

- Add `scripts/archive_monitoring.py` for Actions schedule counts, source health, storage measurements, wind/history feature windows, context availability, event grouping, and JSON/Markdown output.
- Keep cadence values in a documented policy table. NOAA CO-OPS wind and water levels use the documented six-minute observation interval; KNEW METAR is hourly with special reports; USGS continuous series cadence is reported as a provisional 15-minute criterion until station-specific metadata is available. Rain and tributary cadence remains source-specific/provisional and is surfaced as such.
- Predictor windows require paired wind vectors, actual valid and retrieval times no later than the issue cutoff, at least 80% of expected slots, no gap exceeding three nominal intervals, and freshness within three intervals. These are provisional research gates, not model-validity standards.
- Significant rises require native MAUL1 stage only and adequate 24-hour temporal coverage. Overlapping threshold windows are merged, and a count requires a matured Phase 6 prospective verification target inside the event window. Three distinct grouped episodes is a provisional “candidate for review” threshold, not a statistical sufficiency claim; human review must determine whether actual events are independent.
- Produce dated JSON and Markdown under `research/prospective-forcing-archive/monitoring/`. The workflow has no push trigger, stages only monitoring reports, and publishes only when files differ. Existing site workflow ignores the whole archive path.

## Non-goals

- No model, forecast, event attribution, or predictor calculation for operational use.
- No receipt cleanup, archive rewrite, datum conversion, interpolation, dashboard redesign, paid service, or AI API.

## Open limits

- GitHub schedule records do not include a scheduled-for timestamp; the report can compare actual scheduled runs with nominal hourly slots but cannot identify which exact slots were dropped or prove a platform cause.
- Several USGS and optional local series do not carry a reliable cadence contract in the stored receipts. Their provisional 15-minute/60-minute criteria must remain labeled and adjustable when metadata is verified.
- A grouped significant-rise episode is candidate observational evidence; overlapping forecast targets and episodes are not independent samples by default.
