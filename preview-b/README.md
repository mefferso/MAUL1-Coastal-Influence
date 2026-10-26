# MAUL1 Coastal Influence — Design B static preview

This is a standalone, unmerged research UX preview. It preserves the existing forecast, prospective verification, historical research and Model Lab renderers inside a three-act layout. It does not modify production data, forecast values, scientific methods, or the production site.

**RESEARCH / SHADOW EVALUATION / NOT OPERATIONAL**

The UI source baseline is `e236d8946fe7acbfb764f1ba60960f9bb806881e`. All repository data requests are pinned to immutable source snapshot `57e4517f353d38056c761125c78331308d67e317` (2026-10-26 14:00:50 UTC), the same data snapshot recorded for Design A. See `snapshot.json`.

Serve this directory over HTTP (for example `python -m http.server` from this directory). Data and charts require network access to the pinned raw GitHub files, Plotly, Leaflet, and OpenStreetMap tiles. No latest/main data endpoint or periodic refresh is used. Opening `index.html` as a `file://` URL may block data requests in some browsers.

The preview retains existing authentic records and historical diagnostics without copying archives. Its pinned data overlay permits GET and HEAD only. To host at a path such as `/MAUL1-Preview-B/`, publish this directory as the root of a dedicated Pages repository; that repository and Pages configuration were unavailable to this task, so this artifact is not represented as live-hosted.
