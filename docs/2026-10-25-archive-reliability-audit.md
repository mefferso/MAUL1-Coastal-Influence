# Archive sustainability and automation reliability audit

Audit run: October 26, 2026. Live `main` at inspection: `54bd3bcf6489dd4df4c18f6b2356fa612ec72f01`. Scope is research and shadow evaluation only. Phase 6 forecast values, authentic issuance records, verification revisions, raw evidence hashes, and frozen model artifacts remain unchanged.

## Measured size and growth

| Measure | At audit | Meaning |
| --- | ---: | --- |
| GitHub repository size | 254,346 KB (248.38 MiB) | GitHub repository metadata, not a checkout |
| Local Git pack | 241.67 MiB | Packed Git history and reachable objects |
| Tracked working tree | 267.67 MiB | Current files only, excluding `.git` |
| Current research/data files | 262.53 MiB | `site/data/` plus the forcing archive |
| Trailing seven-day new data-blob payload | 415.48 MiB | New unique data blobs on first-parent history; this repo's full observed life is about seven days |

The seven-day window includes large one-time historical archive and report commits, especially October 20–22. A straight-line scenario at that measured rate adds **10.61 GiB in six months** and **21.16 GiB in twelve months** of new data-blob payload. Adding those figures to today's pack gives uncompressed planning ceilings of **10.84 GiB** and **21.39 GiB**; Git pack delta-compression reduces actual storage, so these are deliberately conservative bounds, not GitHub's projected size meter. This projection must not be mistaken for a forecast of routine hourly growth.

Current Phase 6 archive inventory:

- 42 authentic issue records: 38 v2 compact records (603,406 bytes total; about 15.9 KB each) and four original v1 records (23,250,204 bytes total). The v1 files remain readable and untouched.
- 38 v2 gzip snapshots (4,693,796 bytes total; about 123.5 KB each). All 38 hashes are distinct, so this sample has no duplicate payloads to eliminate; content addressing still makes exact repeat writes idempotent.
- The original 2026-10-22 observation capture remains as a 4,887,729-byte v1 JSON file. Other observation captures are gzip-compressed; these timestamp-named files are not content-addressed.
- Compact `latest.json`: 9,601 bytes. `performance.json`: 43,973 bytes. Verification: 113 append-only files, 420,174 bytes total (about 3.7 KB each).
- Across the 42 issue commits, new Git data-blob payload is 332.86 KiB median and 958.17 KiB mean per cycle. The mean is lifted by the first large v1 issues; the median is more representative of the compressed era, but includes attempts, verification updates, and dashboard projections as well as issue and snapshot files.

Forcing archive inventory and cost:

- Seven archived batches contain 208 receipts and 110 content-addressed raw JSON payloads (189,237 bytes). Multiple receipt rows may reference one raw provider response.
- The seven collector commits introduced 813,460 bytes of new data-blob payload, or 116.2 KB per batch on average. At one batch each hour, that is about 2.66 MiB/day, 0.48 GiB in six months, and 0.95 GiB in twelve months of blob payload.
- A routine hourly Phase 6 plus forcing scenario at the observed medians/mean is roughly 10.5 MiB/day (about 1.8 GiB/six months and 3.7 GiB/year of blob payload). Actual schedules have been far less regular, and these are not server pack-size estimates.

## Compression and reconstruction checks

The compression work requested in Issue #25 is already on `main`: Phase 6 v2 issues retain the original forecast fields, put the exact source snapshot in a SHA-256-addressed gzip JSON file, and expose its path and digest. The recovery function reads both v1 inline evidence and v2 references and verifies the decompressed byte hash. `latest.json` is a compact dashboard projection. Verification snapshots are small, append-only revision files; no revision is replaced.

All 42 issue records reconstructed successfully during the audit. Each v2 reference decompressed and hashed to its referenced digest; all v1 inline snapshots reconstructed. The focused regression test confirms create-only issue writes, v1 compatibility, v2 round-trip, and one gzip blob for repeated identical source data. The collector's existing tests confirm raw-payload SHA validation and cross-run deduplication. Audit-only checks also verified every forcing receipt's raw file exists and matches its SHA-256. No production archive was rewritten for these checks.

## Forcing schedule and run health

`.github/workflows/forcing-archive.yml` declares `43 * * * *` UTC. The seven archived batch times are Oct 25 15:11:16, 16:36:48, 18:33:12, 21:14:20, 23:32:40, Oct 26 01:42:32, and 07:01:20 UTC. Actions history identifies two `workflow_dispatch` runs and five `schedule` runs among them. Inter-batch gaps are 1:25:32, 1:56:24, 2:41:08, 2:18:20, 2:09:52, and 5:18:48.

All seven batches completed collection successfully: each archived health report has no critical or shadow source failures. Thus those long intervals are gaps in observed workflow/collection cadence, not evidence of provider collection errors. Actions records successful invocations but does not expose an explicit record for every cron tick that did not run; this audit cannot assign a specific missing tick to scheduler delay, skip, or concurrency cancellation.

Before this branch, PR validation and production collection shared one concurrency group. GitHub concurrency permits one running and one pending job in a group; PR traffic could occupy the pending slot. The forcing workflow now gives each PR its own group and keeps all production triggers serialized together. This removes avoidable PR contention without asserting that it explains any particular historic gap.

## Workflow interactions and inventory

All scheduled times below are UTC. Data-writing workflows generally checkout `main`, commit only when their selected files changed, and retry a fetch/rebase/push; none rewrites history. Phase 5A/5B use the triggering branch (so a manual run on `main` writes to `main`, while a PR run can write to its head branch). PR validation jobs are read-only for the audited workflows except Phase 5B's branch-scoped evaluation output. Separate concurrency groups serialize each writer family, while Phase 6, forcing archive, and observation-context writers can overlap because they write distinct paths; their retry/rebase loops handle concurrent main advances.

| Workflow | Trigger / purpose | Main writes |
| --- | --- | --- |
| Historical archive backfill | Manual and selected source changes; rebuild/persist hourly history | Yes |
| Research forcing observation archive | Hourly at :43, manual; PR runs tests/live smoke | Yes for schedule/manual; isolated PR checks |
| Refresh MAUL1 observed-stage context | Daily 00:37, manual, context-code changes | Yes |
| Phase 3B historical validation | Manual and selected code changes | Yes |
| Phase 4 evidence evaluation | Manual and selected code changes | Yes |
| Phase 5A hindcast evaluation | Manual and selected code changes | Yes, configured branch |
| Phase 5B tidal-aware robustness | PR, manual, selected code changes | Yes, configured branch |
| Phase 6 prospective verification | Hourly at :17; manual; PR validation; selected main pushes | Yes for schedule, authentic dispatch, and matching main pushes; simulation dispatch is isolated |
| Validate and deploy | Every push, PR, manual run, and successful completion of listed data workflows | No; publishes Pages |
| Manual historical event refresh | Manual | Yes |
| MCHL1 one-time source probe | PR/manual | No |
| MCHL1 USGS historical overlap probe | PR/manual | No |
| Phase 7 cleaned historical experiment | PR/manual | No |
| Phase 8 retrospective lead analysis | PR/manual | No |
| Publish v1.1.0 research release | Main push changing its workflow file; validates the immutable v1.1.0 tag | Release asset only, and only if the release does not already exist |

`Validate and deploy` runs full historical/model reproducibility and all tests before each Pages deployment. Its `workflow_run` trigger is the path that allows Actions data writers' `GITHUB_TOKEN` commits to lead to a Pages update; those commits do not reliably trigger another workflow through `push`. This means an hourly Phase 6 cycle can cause a full historical validation/rebuild. Recent history shows four such site runs failed at the full Python suite on one age-sensitive collector fixture; deployment was consequently skipped. The actual Phase 6 and forcing collector runs succeeded. A separate deployment-only job could avoid repeating historical reproduction, but changing that workflow would alter deployment validation policy and is left for owner review.

The site workflow also runs on every ordinary main push, regardless of changed paths. Commits limited to research inputs that Pages does not publish can therefore cause needless verification work when made by a user or another token. Restricting push paths and splitting Pages deployment from expensive reproducibility checks are recommended follow-ups; this PR does not change Pages validation policy.

## Safe fixes in this branch

- Added archive-growth measurements to the forcing workflow summary: current tracked tree and archive bytes, Git pack size, seven-day unique data-blob payload, Phase 6 median/mean per-cycle additions, and six/twelve-month rate scenarios. It reads existing history and adds no stored archive files.
- Separated PR validation from the forcing collector's production concurrency group so PR traffic cannot displace its pending production run.
- Fixed the collector's injected-time contract: when tests pass `now=`, fetched receipts now use that supplied clock instead of the host clock. This fixes a deterministic fixture that became stale after October 25 and had failed four consecutive full site validation runs. Live collection still uses the system clock.

## Free storage options and recommendation

| Option | Benefits | Costs and limits |
| --- | --- | --- |
| Compressed/content-addressed files in this repo | Already implemented; simplest provenance and Pages paths; free public GitHub hosting | Git history and ordinary clones grow with every immutable cycle; Git delta compression cannot remove history already published |
| Separate public GitHub data repo | Keeps application checkout small and separates retention/write permissions; still free Git versioning | A data repo still accumulates Git history; extra checkout/fetch and cross-repo Pages plumbing; public artifact URLs and access policy must be designed |
| GitHub Releases assets | Keeps large evidence out of Git objects and can publish immutable digest-named files | Additional release/upload/download workflow and Pages retrieval logic; per-asset and bandwidth constraints/policies should be checked against actual planned artifacts |

Recommendation: keep the present content-addressed layout while the archive remains research-only, instrument it, and set a review trigger before the repository approaches 500 MiB in GitHub's size meter. At the measured routine cycle rate, owners should compare the repository size again after 14 days. Before steady hourly archiving becomes long-term policy, evaluate a separate data repo or release assets with a small end-to-end Pages prototype. Do not migrate the existing records as part of this PR.

Recommended CI guardrails to approve before enforcement: warn when repository size reaches 350 MiB; pause new routine archive commits for owner review at 500 MiB; warn when a normal hourly run adds more than 1 MiB of new data blobs and fail closed for review above 5 MiB. The median Phase 6 cycle is 333 KiB and forcing batch average is 116 KiB, grounding these thresholds above typical cycles while catching runaway snapshots. Manual backfills should report separately rather than bypass immutable-evidence rules.

## Owner decisions

1. Approve or revise the 350/500 MiB repository thresholds and 1/5 MiB per-run limits before enforcement.
2. Choose whether long-term storage should stay in this repo, use a separate public data repo, or use Release assets. Any migration needs an explicit preservation and Pages URL plan.
3. Decide whether to split expensive Pages validation from deployment and constrain push triggers to relevant published files.
4. Confirm whether hourly Phase 6 main writes remain appropriate for research/shadow evaluation, since matching main pushes also issue authentic records.
