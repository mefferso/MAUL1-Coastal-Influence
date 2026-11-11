# Implementation plan: automated archive monitoring

## Files

- `scripts/archive_monitoring.py`: pure report builders, GitHub Actions run-history client, storage reader, deterministic JSON/Markdown writing, and CLI.
- `tests/test_archive_monitoring.py`: synthetic receipt, issuance, verification, schedule, gap, event-grouping, and idempotency tests.
- `.github/workflows/archive-monitoring.yml`: daily/weekly schedule, report summary, changed-only commit with the existing rebase-safe publisher.
- `docs/prospective-forcing-archive.md`: describe report cadence, provisional criteria, and report locations.
- `.github/workflows/site.yml`: only if needed to preserve archive-only Pages exclusion for report paths.

## Tasks

1. Write regression tests first for schedule accounting, receipt latency/issue cutoffs, wind-window gaps, missing context, significant-rise episode grouping, insufficient events, and deterministic writes. Run and observe the expected failures.
2. Implement report data readers and daily archive-health evaluation. Reuse `archive_completeness` and `archive_growth` where practical; do not alter immutable data.
3. Implement weekly feature and event evidence summaries with explicit provisional criteria and no interpolation/datum conversion.
4. Add the Actions workflow, changed-only report publication, concise step summary, and documentation.
5. Run focused and full test suites, execute the scripts against the actual archive in offline mode, inspect generated output and repository diff, then open a reviewable PR without merging.

## Verification

- Focused: `python -m unittest tests.test_archive_monitoring tests.test_archive_completeness tests.test_archive_workflow -v`.
- Full: `python -m unittest discover -s tests`.
- CLI: generate daily and weekly reports twice into a temporary directory with a fixed evaluation time and verify bytes are identical; inspect real-archive status for honest pre/post-merge evidence.
- Static: `python -m py_compile scripts/archive_monitoring.py`; JSON parse the generated reports; `git diff --check`; hosted PR checks after publishing.
