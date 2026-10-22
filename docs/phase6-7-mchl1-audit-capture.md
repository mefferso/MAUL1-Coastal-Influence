## Phase 6.7: MCHL1 audit-only prospective capture

After the 96-hour HADS probe confirmed 383/383 numeric values at 15-minute spacing, this phase captures MCHL1 from the exact-ID IEM HADS endpoint across four days. Preserve individual observation UTC valid time, retrieval time, response hash and the native unverified gauge-height datum. USACE 85420 is explicitly not substituted.

**This is audit-only capture, not feature activation.** Records retain quality 'unverified', and the existing Phase 6 quality filter rejects them from model inference. Source status is 'retrieved_unverified' with forecast_eligible false. No NAVD88 conversions, training modifications, or changes to prior forecasts.

Before model activation, independently confirm historic/prospective measurement consistency, provider QC conventions, current latency across distinct issuance cycles, and 72h native-stage continuity. Review activation separately; do not silently relabel unverified source QC as provisional.
