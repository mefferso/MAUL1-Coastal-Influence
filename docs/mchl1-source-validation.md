# MCHL1 source-validation gate

The NWS HADS station directory identifies MCHL1 as Pass Manchac near Highway 51, DCP CE678A12, reporting HG. IEM documents a HADS/SHEF query interface at `https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py` with `stations`, `sts`, `ets`, and `what` parameters. IEM warns about a per-client request throttle introduced October 5, 2026. Keep probe requests limited, manual, and narrow.

HADS `HGIRGZZ` responses can contain `9999999.0` as a missing-value sentinel. It is finite as a floating-point number, so ingestion and overlap analysis must explicitly reject it before stage changes are calculated. The parser now drops this value while the overlap provenance records its raw count; historical feature tables and frozen models remain unchanged.

Run the exploratory, **read-only** candidate check with:

```bash
python scripts/probe_mchl1.py --hours 48
```

This script cannot activate MCHL1 as a model input, and a successful 200 response **does not establish** real-time eligibility. The parser only reports station identity, SHEF HG columns, time-field presence, and record count. Do not conflate raw stage HG values with elevations referenced to NAVD88.

Before enabling MCHL1 in the prospective issuance, demonstrate: (1) consistent station identity MCHL1 / CE678A12 and not USACE 85420/85420LA or PMPL1; (2) correct stage type and units with the native datum explicitly labeled unverified; (3) authentic observation valid-time and separately recorded retrieval time, source latency and QC; (4) observations for the full 72-hour change horizon and completed-hour bin coverage; (5) multiple live checks on different issuance cycles with no retrospective substitution; (6) source outages or empty responses produce missing-data statuses. Capture response hashes, negative fixtures, and live examples. Merge a live source only after a separate review demonstrating these conditions.

Sources:
- https://hads.ncep.noaa.gov/states/LA_dcps.shtml
- https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py?help=
- https://mesonet.agron.iastate.edu/request/dcp/fe.phtml

**Status:** source candidate only, not validated for live forecasting.

## Additional independent evidence: LIX HADS SHEF products

IEM's archived RRSLIX text products on 2026-08-06 at 14:40 and 15:40 UTC contain original MCHL1 SHEF `.E MCHL1 .../HGIRG/DIN15/...` reports, confirming that at least some 15-minute MCHL1 stage data were relayed through HADS (not just station metadata). Example pages: https://mesonet.agron.iastate.edu/wx/afos/p.php?e=202608061540&pil=RRSLIX and https://mesonet.agron.iastate.edu/wx/afos/p.php?e=202608061440&pil=RRSLIX. IEM LA_DCP station metadata independently lists MCHL1 and PEDTS HGIRG with first history entry 2022-12-20: https://mesonet.agron.iastate.edu/sites/networks.php?network=LA_DCP&station=NLGL1.

These historical reports confirm an actual stage product and approximate reporting cadence, **not** a verified current feed, receipt-time availability, or datum. The data-source evaluation should compare IEM LA_DCP request output and the original RRSLIX product during a current issuance, verify identical observation valid times and sensible latency, and preserve product ingest/receipt times. Do not enable automatically based on historical product matches.
