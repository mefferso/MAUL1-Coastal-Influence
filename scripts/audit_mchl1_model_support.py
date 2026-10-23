"""Read-only audit of MCHL1 training support in frozen Phase 5 models."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MODEL_MAP = {
    "phase5a_maul1_only": "phase5a",
    "phase5a_coastal": "phase5a",
    "phase5b_coastal_tidal": "phase5b",
    "phase5b_full_multivariable": "phase5b",
}
HORIZONS = (6, 12, 24)


def coefficient_for(model: dict, feature_index: int, missingness: bool = False) -> float:
    """Return a frozen standardized ridge coefficient, respecting its active mask."""
    count = len(model["feature_names"])
    column = feature_index + (count if missingness else 0)
    active = model.get("active")
    coefficients = model.get("coefficients", [])
    if active is None or column >= len(active) or not active[column]:
        return 0.0
    coefficient_index = sum(bool(item) for item in active[:column + 1])
    if coefficient_index >= len(coefficients):
        raise ValueError("Frozen active-column mask and coefficient vector do not align")
    return float(coefficients[coefficient_index])


def summarize_model_support(model_name: str, horizon: int, model: dict,
                            feature_rows: list[dict], train_count: int) -> dict:
    """Summarize MCHL1 predictor support and frozen slopes for one fit."""
    features = []
    names = model["feature_names"]
    for index, name in enumerate(names):
        if not name.startswith("mchl1_"):
            continue
        observed = sum(row.get(name) not in (None, "") for row in feature_rows)
        # MCHL1's SHEF missing code can leak into lag differences as values
        # near +/-5e6 ft. Flag these separately from ordinary missing values.
        sentinel_contaminated = sum(
            row.get(name) not in (None, "") and abs(float(row[name])) > 10_000
            for row in feature_rows
        )
        features.append({
            "name": name,
            "training_rows": train_count,
            "observed_rows": observed,
            "missing_rows": train_count - observed,
            "observed_percent": 100.0 * observed / train_count if train_count else None,
            "missing_percent": 100.0 * (train_count - observed) / train_count if train_count else None,
            "sentinel_contaminated_rows": sentinel_contaminated,
            "usable_observed_rows": observed - sentinel_contaminated,
            "usable_observed_percent": 100.0 * (observed - sentinel_contaminated) / train_count if train_count else None,
            "value_coefficient_standardized": coefficient_for(model, index),
            "missingness_coefficient_standardized": coefficient_for(model, index, missingness=True),
        })
    return {
        "model": model_name,
        "horizon_hours": horizon,
        "training_rows": train_count,
        "status": "audited" if features else "no_mchl1_predictors",
        "features": features,
    }


def audit_model_support(root: Path) -> dict:
    """Recreate each frozen fit's exact calibration rows and audit MCHL1 columns."""
    root = Path(root)
    sys.path.insert(0, str(root / "scripts"))
    import phase5a  # project's canonical Phase 5A feature and training-row builders
    import phase5b  # project's canonical Phase 5B row builder

    artifact = json.loads((root / "site/data/prospective/model-artifacts.json").read_text())
    phase5a_models = json.loads((root / "site/data/history/phase5a/models.json").read_text())["final_holdout_fit"]
    phase5b_models = json.loads((root / "site/data/history/phase5b/models.json").read_text())
    _, phase5a_data = phase5a._feature_data(root)
    phase5b_rows, _ = phase5b._load_table(root)

    result = {
        "schema": "phase6.mchl1-model-support-audit.v1",
        "artifact_sha256": artifact["artifact_sha256"],
        "calibration_period": "2016-01-01 through 2022-12-31, with 72-hour target embargo",
        "coefficient_units": "standardized ridge slope in feet of target change per one training standard deviation",
        "models": {},
        "interpretation": (
            "A nonzero coefficient is not evidence of useful MCHL1 skill. Availability rates describe training support; "
            "they do not establish datum, sensor independence, or QC validity."
        ),
    }

    for model_name, family in MODEL_MAP.items():
        result["models"][model_name] = {}
        for horizon in HORIZONS:
            model = artifact["models"][model_name][str(horizon)]
            if family == "phase5a":
                target = phase5a._delta_targets(phase5a_data, horizon)
                cutoff = int(phase5a.BOUNDARY.timestamp() // 3600) - phase5a.EMBARGO_HOURS
                train_ix = phase5a.np.flatnonzero(phase5a._training_mask(
                    phase5a_data, target, horizon, cutoff
                ))
                feature_rows = [phase5a_data["feature_rows"][i] for i in train_ix]
                expected = int(phase5a_models[str(horizon)]["parameters"]["models"][
                    "maul1_only" if model_name == "phase5a_maul1_only" else "maul1_plus_coastal"
                ]["train_count"])
            else:
                feature_rows = [
                    row for row in phase5b_rows[horizon]
                    if row["split"] == "calibration"
                    and row["actual"] is not None
                    and row["target_time"] < phase5b.BOUNDARY - phase5b.dt.timedelta(hours=72)
                    and row.get("maul1_stage_native_ft") is not None
                ]
                fit_name = "maul1_coastal_tidal" if model_name == "phase5b_coastal_tidal" else "full_multivariable"
                expected = int(phase5b_models[str(horizon)][fit_name]["training_n"])
            if len(feature_rows) != expected:
                raise ValueError(
                    f"{model_name} {horizon}h training rows disagree with frozen artifact: "
                    f"{len(feature_rows)} != {expected}"
                )
            summary = summarize_model_support(model_name, horizon, model, feature_rows, len(feature_rows))
            result["models"][model_name][str(horizon)] = summary
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(audit_model_support(args.root), indent=2))


if __name__ == "__main__":
    main()
