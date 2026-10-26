# MCHL1 evidence determination

**Disposition: shadow-only and forecast-ineligible.** MCHL1 observations remain separate research context. They are not predictors in an existing frozen Phase 5A/5B model, do not alter Phase 6 forecasts, and must not be converted to MAUL1 datum or treated as validated warning evidence.

## Evidence reviewed

- **Phase 7 sentinel contamination:** The January 2016–October 2026 hourly archive has MCHL1 coverage only from December 2022. Of 34,344 possible hourly slots, 30,684 were usable (89.34%); 744 hours were not recorded and the longest gap between usable observations was 1,527 hours. The archive contains two exact `9,999,999.0 ft` sentinel values and 19 near-five-million-foot hourly means contaminated by sentinel averaging. There are 206 derived stage-change rows with magnitude at least one million feet. Phase 4 independently recorded 594 adjacent jump flags, which are repeated pairwise flags rather than 594 distinct observations. Phase 7’s separate cleaner marks these values missing and records original input hashes; it does not repair the source archive or frozen model artifacts.
- **Phase 6 source audit:** The normalized source archive contains 315 exact 9,999,999-ft HADS sentinel rows. Original source evidence and authentic Phase 6 records remain unchanged; sentinel filtering applies to newly parsed inputs and the separate cleaner only.
- **Phase 8 missingness and timing:** MCHL1 context appeared before onset in 24 of 179 known-onset events, with a retrospective median lead of 56.5 hours (range 41.3–70 hours). Its mean pre-onset missing fraction was 68.47%. It also appeared in 19 of 63 selected nonresponse controls (39 screen episodes, 391 signal-present hours). The same screen sequence was strictly ordered through MCHL1 and MAUL1 in only two events. These are retrospective timestamp screens, not proof of source receipt-time lead, sensor validity, or coastal causation.
- **Identity and vertical reference:** The archived record is Iowa Environmental Mesonet’s copy of NWS HADS station `CE678A12`, SHEF product `HGIRGZZ`. Its archive label does not establish a continuous physical sensor identity, gauge-zero history, or certified vertical datum. HADS, USGS station `073802302`, and USACE gauges `85420` and `85420LA` are distinct sources; none can be silently substituted for another. The hourly archive also does not retain all original provider response bodies, qualifier semantics, or equipment-change records.
- **Retrospective sensitivity:** The Phase 7 cleaned Phase 5A candidates did not improve the already-inspected holdout overall. This correction therefore does not support promotion, and the holdout cannot serve as a new independent validation set.

## Reopening criteria

Reopen the disposition only after all of these gates are met and reviewed. Passing them permits a new shadow research evaluation; it does not automatically make MCHL1 forecast-eligible.

1. **Identity evidence:** Obtain agency records linking the HADS station and SHEF product to a physical site and instrument for each claimed period. Document coordinates, sensor type, deployment/removal dates, and any source transitions. Reconcile HADS, USGS, and USACE records independently; do not splice them.
2. **Datum evidence:** Obtain authoritative benchmark or maintenance documentation for gauge zero, units, vertical datum, and every offset change across the evaluation period. A provider label or statistical correlation is insufficient. Until then, use only explicitly labeled native relative changes and keep absolute cross-station comparisons unavailable.
3. **Source-level quality evidence:** Recover provider observations with original timestamps, receipt/retrieval timestamps, QC qualifiers, and revision metadata for sentinel and gap periods. Demonstrate that sentinel and nonfinite values are removed before aggregation; retain raw evidence and its SHA-256 manifest unchanged.
4. **Prospective completeness evidence:** Collect at least 30 consecutive days of shadow-only samples with expected interval and source receipt times recorded. Publish valid-bin coverage, missing-gap distribution, retrieval latency, QC counts, range/resolution, and sensor-change flags. Require at least 90% valid expected 15-minute bins, no unexplained gap longer than six hours, and 95% of valid samples received within 60 minutes of their source timestamp; report provider outages separately. If the source does not offer an expected 15-minute cadence, establish and document its authoritative cadence before applying a completeness threshold.
5. **Independent model evaluation:** Pre-register hypotheses, predictors, event/control definitions, exclusions, and metrics before examining new outcomes. Evaluate event-blocked and forward-only on newly accrued events with independent coastal/river evidence. Any model that uses MCHL1 must be a separately versioned candidate; preserve frozen Phase 5A/5B artifacts and do not describe retrospective holdout results as independent validation.
6. **Human review:** Have a qualified hydrologist review instrument identity, datum evidence, QC rules, source changes, and the pre-registered evaluation before any eligibility discussion. The repository owner must explicitly approve any later change to forecast eligibility.

## Source references

- [Phase 7 data-quality audit](phase7-data-quality.md)
- [Phase 8 retrospective lead results](phase8-lead-results.md)
- [Phase 6.16 source and QC audit](phase6-16-scientific-correctness-audit.md)
