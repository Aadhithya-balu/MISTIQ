"""Structured experiment-result validation and machine-readable storage."""

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

RESULT_FIELDS = (
    "experiment_id", "model_name", "model_version", "seed", "feature_set",
    "train_size", "validation_size", "test_size", "accuracy", "macro_precision",
    "macro_recall", "macro_f1", "weighted_f1", "log_loss", "top2_accuracy",
    "top3_accuracy", "brier_score", "ece", "timestamp",
)


@dataclass
class ExperimentResult:
    experiment_id: str
    model_name: str
    model_version: str
    seed: int
    feature_set: str
    train_size: int
    validation_size: int
    test_size: int
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    weighted_f1: float
    log_loss: float
    top2_accuracy: float
    top3_accuracy: float
    brier_score: float
    ece: float
    timestamp: str = ""
    removed_feature: str | None = None
    baseline_name: str | None = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        validate_result(asdict(self))


def validate_result(row):
    missing = [field for field in RESULT_FIELDS if field not in row]
    if missing:
        raise ValueError(f"result missing required fields: {missing}")
    for field in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1",
                  "top2_accuracy", "top3_accuracy", "ece"):
        if not 0.0 <= float(row[field]) <= 1.0:
            raise ValueError(f"{field} must be in [0, 1]")
    if not 0.0 <= float(row["brier_score"]) <= 2.0:
        raise ValueError("multiclass brier_score must be in [0, 2]")
    if float(row["log_loss"]) < 0:
        raise ValueError("log_loss must be non-negative")
    if min(int(row["train_size"]), int(row["validation_size"]), int(row["test_size"])) < 0:
        raise ValueError("split sizes cannot be negative")
    return row


def save_results(rows, json_path, csv_path):
    rows = [asdict(row) if isinstance(row, ExperimentResult) else dict(row) for row in rows]
    for row in rows:
        validate_result(row)
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fields = list(RESULT_FIELDS) + ["removed_feature", "baseline_name"]
    with Path(csv_path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
