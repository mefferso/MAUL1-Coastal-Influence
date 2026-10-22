# MCHL1 source-validation gate

The NWS HADS station directory identifies MCHL1 as Pass Manchac near Highway 51, DCP CE678A12, reporting HG. IEM documents a HADS/SHEF query interface at `https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py` with `stations`, `sts`, `ets`, and `what` parameters. IEM warns about a per-client request throttle introduced October 5, 2026. Keep probe requests limited, manual, and narrow.

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
