# Design B visual and interaction system

Design B is a separate research-folio composition. It reuses the semantic colors and focus conventions introduced by Design A where useful, while keeping the page’s independent paper-and-ink presentation. It does not add a production theme or alter the shared production stylesheet.

## Tokens

The standalone tokens are defined in `../design-b.css`: paper and surface colors, ink and muted text, river blue, lake teal, target-gauge vermilion, shadow amber, spacing, card radius, shadow, content width and visible keyboard focus. At narrow widths cards stack, wide tables scroll within their own region, and motion is reduced when requested by the user’s system.

## Page structure

- **Now** groups the current archived issuance, source context and station coordinate plot.
- **Is it working?** puts prospective maturity beside paired model scores and leaves retrospective performance exploration available below.
- **What did we learn?** groups historical station analysis, independent verification, limitations, and Model Lab diagnostics.

The existing forecast, verification, historical research and Model Lab DOM panels and renderer scripts are retained. Hash aliases for the four existing panel IDs remain supported. The act tabs expose arrow, Home, and End navigation.

## Evidence colors and labels

River blue identifies inland river context; lake teal identifies lake/coastal context; target vermilion identifies MAUL1; amber identifies the reported MCHL1 point. Labels state that MCHL1 is shadow-only and that datum and sensor identity are unresolved. The coordinate figure explicitly does not imply flow, travel time, or causality.

## Data boundary

`assets/data-router.js` maps page-local `data/...` GETs to the immutable `57e4517f353d38056c761125c78331308d67e317` source commit. It rejects write methods. There is no live sync, schedule, production route, or copied archive. If the pinned snapshot becomes unavailable, the UI reports missing evidence rather than silently switching to current data.

## Scientific boundary

This presentation does not compute or alter forecasts, models, thresholds, verification metrics, event grouping, source records, or Phase 6 issuances. The prospective overview displays existing metric and completeness fields as published. Historic and prospective evidence remain separately identified, and absent values stay unavailable rather than becoming zero.
