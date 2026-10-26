"""Report working-tree archive sizes and recent Git data growth for Actions."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
import statistics
import subprocess
import sys

DATA_PREFIXES = ("site/data/", "research/prospective-forcing-archive/")
SOFT_WARNING_BYTES = 350 * 1024 * 1024
OWNER_REVIEW_BYTES = 500 * 1024 * 1024


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True)


def bytes_of(root: Path, paths: list[str]) -> int:
    return sum((root / path).stat().st_size for path in paths
               if (root / path).is_file())


def history_growth(root: Path, days: int = 7) -> tuple[int, list[int]]:
    """Count unique data blobs first introduced on first-parent history in days."""
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=days)
    commits = git(root, "rev-list", "--first-parent", "HEAD").splitlines()
    introduced: set[str] = set()
    cycle_bytes: list[int] = []
    total = 0
    for commit in commits:
        parent_line = git(root, "rev-list", "--parents", "-n", "1", commit).split()
        if len(parent_line) < 2:
            break
        parent = parent_line[1]
        stamp = git(root, "show", "-s", "--format=%cI", commit).strip()
        if dt.datetime.fromisoformat(stamp) < cutoff:
            break
        raw = git(root, "diff-tree", "--no-commit-id", "--no-renames", "--raw", "-r", parent, commit)
        added_this_commit = 0
        for line in raw.splitlines():
            if not line.startswith(":"):
                continue
            meta, path = line.split("\t", 1)
            fields = meta[1:].split()
            new_sha = fields[3]
            if not any(path.startswith(prefix) for prefix in DATA_PREFIXES):
                continue
            if new_sha == "0" * 40 or new_sha in introduced:
                continue
            introduced.add(new_sha)
            size = int(git(root, "cat-file", "-s", new_sha))
            total += size
            added_this_commit += size
        subject = git(root, "show", "-s", "--format=%s", commit).strip().lower()
        if "phase 6 prospective cycle" in subject:
            cycle_bytes.append(added_this_commit)
    return total, cycle_bytes


def format_bytes(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(size)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    raise AssertionError("unreachable")


def storage_budget_notice(pack_bytes: int) -> str:
    """Return an advisory threshold message; never gate archive writes."""
    if pack_bytes >= OWNER_REVIEW_BYTES:
        return (f"Owner review suggested: Git pack is {format_bytes(pack_bytes)} "
                f"(review threshold {format_bytes(OWNER_REVIEW_BYTES)}).")
    if pack_bytes >= SOFT_WARNING_BYTES:
        return (f"Soft warning: Git pack is {format_bytes(pack_bytes)} "
                f"(soft threshold {format_bytes(SOFT_WARNING_BYTES)}).")
    return (f"Below advisory thresholds: Git pack is {format_bytes(pack_bytes)}; "
            f"soft warning {format_bytes(SOFT_WARNING_BYTES)}, owner review "
            f"{format_bytes(OWNER_REVIEW_BYTES)}.")


def build_report(root: Path) -> str:
    # Include newly collected files before the workflow stages them for commit.
    tracked = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")
    tracked = [p for p in tracked if p]
    data_paths = [p for p in tracked if any(p.startswith(prefix) for prefix in DATA_PREFIXES)]
    tree_bytes = bytes_of(root, tracked)
    archive_bytes = bytes_of(root, data_paths)
    history_bytes, cycles = history_growth(root)
    pack_size = 0
    for line in git(root, "count-objects", "-v").splitlines():
        if line.startswith("size-pack: "):
            pack_size = int(line.split(":", 1)[1].strip()) * 1024
    days = 7
    six_months = (history_bytes / days) * 183
    twelve_months = (history_bytes / days) * 365
    cycle = (f"median {format_bytes(int(statistics.median(cycles)))} and mean "
             f"{format_bytes(sum(cycles) // len(cycles))} new Git blobs/cycle "
             f"(n={len(cycles)})" if cycles else "n/a (no Phase 6 cycle commits in window)")
    return "\n".join((
        "### Archive growth (current checkout)",
        f"- Working tree: **{format_bytes(tree_bytes)}** tracked files; archive data: **{format_bytes(archive_bytes)}**.",
        f"- Git pack/history: **{format_bytes(pack_size)}** (history size is distinct from working-tree size).",
        f"- Storage budget: {storage_budget_notice(pack_size)}",
        f"- New unique data blobs on first-parent history, trailing 7 days: **{format_bytes(history_bytes)}**.",
        f"- Phase 6 cycle additions: {cycle}.",
        f"- Linear projection of new data-blob payload: +{format_bytes(int(six_months))} in 6 months; +{format_bytes(int(twelve_months))} in 12 months.",
        f"- Adding that payload to today's Git pack gives an uncompressed planning ceiling of {format_bytes(pack_size + int(six_months))} and {format_bytes(pack_size + int(twelve_months))}.",
        "- Scenario assumes the measured 7-day commit rate continues; the window includes historical backfill, and Git pack delta-compression makes actual storage lower.",
        "- Git pack size is a local compressed-history measurement, not GitHub's repository-size meter; projections sum unique uncompressed blob payload and do not model pack deltas, reachability cleanup, or GitHub accounting.",
    )) + "\n"


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    report = build_report(root)
    print(report, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(report)
