"""Run Phase 5A unchanged against a separate Phase 7 cleaned archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import phase5a
from phase7_data import build_clean_experiment


def run(root, workdir, outdir):
    root, workdir, outdir = map(pathlib.Path, (root, workdir, outdir))
    original = root / "site/data/history"
    workdir.mkdir(parents=True, exist_ok=True)
    run_dir = pathlib.Path(tempfile.mkdtemp(prefix="phase7-run-", dir=workdir))
    cleaned_hourly = run_dir / "cleaned-hourly"
    experiment_root = run_dir / "experiment-root"
    experiment_history = experiment_root / "site/data/history"
    experiment_history.mkdir(parents=True, exist_ok=True)
    audit = build_clean_experiment(original / "hourly", cleaned_hourly)
    (experiment_history / "hourly").symlink_to(cleaned_hourly.resolve(), target_is_directory=True)
    (experiment_history / "phase3b").symlink_to((original / "phase3b").resolve(), target_is_directory=True)
    summary = phase5a.run(experiment_root, outdir)
    result = {
        "schema": "phase7.cleaned-hindcast.v1",
        "study": "Retrospective experimental Phase 5A replay on conservative Phase 7 cleaned archive",
        "forecast_eligible": False,
        "cleaning_method": "phase7-clean-v1",
        "cleaned_dataset_audit": audit,
        "hindcast_summary": summary,
        "experiment_code_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "phase5a_code_sha256": hashlib.sha256((HERE / "phase5a.py").read_bytes()).hexdigest(),
        "interpretation": "The 2023-onward period is an already inspected retrospective benchmark, not an independent test. No result changes frozen or prospective models.",
    }
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "phase7-experiment.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=HERE.parent)
    parser.add_argument("--workdir", type=pathlib.Path, required=True)
    parser.add_argument("--outdir", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.root, args.workdir, args.outdir)
    print(json.dumps({"output": str(args.outdir / "phase7-experiment.json"),
                      "issue_count": result["hindcast_summary"]["issue_count"],
                      "holdout": result["hindcast_summary"]["holdout_results"]}, indent=2))


if __name__ == "__main__":
    main()
