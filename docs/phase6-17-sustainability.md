# Phase 6.17 repository and workflow sustainability

**Scope:** Research / Shadow Evaluation / Not Operational. No archive migration is performed here. Original authentic Phase 6 issues, verification revisions, source hashes, and frozen model artifacts remain immutable.

## Measured storage

Measured from the checkout at `3ae0973` on 2026-10-26, before this change:

| Measurement | Size | What it means |
|---|---:|---|
| GitHub repository metadata | 254,346 KB / 248.38 MiB | GitHub's reported repository-size field; it is not an exact working-tree measurement |
| Local Git pack/history | 241.67 MiB | Compressed Git objects reachable in this local clone |
| Tracked working tree | 268.11 MiB | Current tracked file sizes after checkout |
| Archive working-tree files | 262.81 MiB | Current files under `site/data/` and `research/prospective-forcing-archive/` |
| New unique data blobs, trailing 7 days | 415.82 MiB | First-parent data blobs first introduced during the window; includes the exceptional historical backfill |
| Phase 6 cycle additions in the window | median 333.19 KiB; mean 944.14 KiB (43 cycles) | New data blob payload attributed to cycle commits |
| Linear payload projection | +10.62 GiB / 6 months; +21.17 GiB / 12 months | Seven-day rate extended linearly; the backfill-heavy interval makes this an upper planning scenario |

The projection sums unique uncompressed blob payload. It does not predict GitHub's repository-size field or the final Git pack: Git delta-compression, duplicate content-addressed blobs, reachability, and GitHub accounting all differ. The working-tree figure excludes unreachable objects and is not repository history size. The report now emits advisory soft warnings at 350 MiB local Git pack size and owner-review notices at 500 MiB; neither threshold blocks collection or writes.

## Storage choices

| Option | Measured tradeoff | Assessment |
|---|---|---|
| Compressed/content-addressed files in this repository | Current repo reports 248.38 MiB; local pack 241.67 MiB. Existing SHA-256-addressed gzip snapshots deduplicate identical content and preserve history/provenance, but every changed blob adds Git history. | Keep for now. It has no extra service, works with the current public static site and free GitHub-hosted Actions, and remains below the proposed 350 MiB soft warning. Review growth at 350 MiB; seek owner decision by 500 MiB. |
| Separate GitHub data repository | Same Git object/history behavior and a second repository to permission, archive, and restore. Size reduction cannot be inferred without migrating a measured copy and verifying retention; no second repository is established by this change. | Possible free option if later approved, but requires owner decisions on access, retention, site fetches, and preservation manifests. |
| GitHub Releases assets | Keeps binary snapshots out of ordinary Git checkout/history and can attach immutable versioned bundles; adds release packaging, asset discovery, download/API dependency, and static-site integration. | Possible free option for frozen bundles, not a live append-only hourly collector without added release churn. Requires owner approval and a tested reproducible asset layout. |

**Recommendation:** retain the current content-addressed gzip archive in Git and use the 350/500 MiB report thresholds as review points. Do not migrate, delete history, or rewrite Git history without owner approval. No LFS or paid storage is assumed.

## Workflow inventory

| Workflow | Trigger / schedule | Writes and reliability notes |
|---|---|---|
| `backfill.yml` | Manual | Writes derived event archive on dispatch ref; now uses shared rebase/retry publisher. |
| `forcing-archive.yml` | Hourly at minute 43 UTC; manual; PR validation | Production collector writes archive to `main`; PR concurrency is isolated from production. Existing retry publisher remains. GitHub schedules may be delayed or skipped; run success alone is not evidence every scheduled slot ran. |
| `history.yml` | Manual | Acquires and rebuilds historical partitions/reports; no longer runs on every relevant `main` push. Both commits use rebase/retry publisher. |
| `maul1-observation-context.yml` | Daily at 00:37 UTC; manual; relevant code push | Writes context snapshot to `main`; retains daily schedule and single-writer concurrency; now reports rebase conflicts explicitly. |
| `mchl1-probe.yml` | Manual | Read-only, non-fatal source probe; no PR-triggered remote probe. |
| `mchl1-usgs-overlap.yml` | Manual | Read-only historical comparison; no PR-triggered remote query. |
| `phase3b.yml` | Manual | Writes Phase 3B historical validation reports to dispatch ref; push reruns removed; shared safe publisher. |
| `phase4.yml` | Manual | Writes Phase 4 historical results to dispatch ref; push reruns removed; shared safe publisher. |
| `phase5a.yml` | Manual | Writes Phase 5A hindcast reports to dispatch ref; push reruns removed; shared safe publisher. |
| `phase5b.yml` | Manual | Writes Phase 5B historical robustness reports to dispatch ref; PR/push reruns removed; shared safe publisher. |
| `phase6.yml` | Hourly at minute 17 UTC; manual; PR checks; relevant code push | Authentic Phase 6 verification writes to `main`; PR validation now has a PR-specific concurrency group, separate from the production collector. Schedule and scientific behavior remain unchanged. |
| `phase7-clean-experiment.yml` | Manual | Read-only cleaned retrospective experiment; outputs are workflow artifacts, not archive rewrites. |
| `phase8-lead-analysis.yml` | Manual | Read-only retrospective lead analysis; outputs are workflow artifacts. |
| `publish-v1.1-release.yml` | Relevant release-file push to `main` | Creates the research release/tag and release notes; no archive write. |
| `site.yml` | Main push, PR, manual, and successful writer `workflow_run` | Validates/deploys Pages. `workflow_run` still publishes commits made with `GITHUB_TOKEN`; it now skips redundant Phase 5A/5B and Model Lab historical regeneration because each writer already validated its outputs. |

## Backfill failure and collision handling

Historical run [40322298251](https://github.com/mefferso/MAUL1-Coastal-Influence/actions/runs/40322298251) completed acquisition, validation, hourly rebuild, and event discovery. It failed specifically in **Commit changed history artifacts** after creating local commit `b94550b`: plain `git push` was rejected because `main` had advanced to the Phase 6.16 merge (`5add493`). The remote retained its history; the workflow did not overwrite or partially update it. The earlier **Commit acquired partitions** step had the same plain-push defect.

Historical writers now use `.github/scripts/publish-with-rebase-retry.sh`: fetch current target, rebase, push, retry up to three times on push races, and abort with an explicit error on conflicts. It never force-pushes. A local two-clone integration test covers a successful rebase over an unrelated concurrent commit and a same-file conflict with unchanged remote history.

`site.yml` is started both by main pushes and successful `workflow_run` events because writes made with `GITHUB_TOKEN` do not start normal push workflows. Historical reports are validated by their writer; the follow-on Pages run deploys without repeating the costly Phase 5A/5B and Model Lab historical reproductions. Phase 6 and hourly forcing collection remain scheduled; their PR validation groups are isolated from production collectors.

## Preservation validation

The before/after SHA-256 manifest covered 410 files under `site/data/prospective/` and `research/prospective-forcing-archive/`; it matched exactly with zero additions, removals, or changed hashes. The frozen-artifact replay checked 12 model/horizon outputs (32,406–32,548 rows each); maximum absolute error was `8.89e-16 ft`, below the committed `1e-8 ft` tolerance. A fresh local refreeze had a different artifact SHA-256, but its model values matched the committed artifact exactly after normalizing JSON integers and floats to the same numeric type. The hash difference comes from JSON serialization of numerically equal integer-versus-float values; the committed frozen artifact was not regenerated or changed. Keep this serialization portability issue separate from any future scientific artifact revision.

## Remaining owner decisions

- At 350 MiB local Git pack size, review trend and decide whether to keep the current layout or prepare a measured separate-repository/Releases experiment.
- Before 500 MiB, choose retention and migration policy, if any. No deletion or migration is authorized by this report.
- Review and approve the MCHL1 reopening criteria in [the determination](mchl1-determination.md); its data stays shadow-only.
