"""Generate comparison reports only from measured result rows."""

import csv
from dataclasses import asdict, is_dataclass
from pathlib import Path


def comparison_markdown(rows, path):
    ordered = sorted(rows, key=lambda row: row["macro_f1"], reverse=True)
    lines = ["# Model comparison", "", "Measured test-set metrics; rows are ordered by macro F1.", "",
             "| Model | Macro F1 | Accuracy | Weighted F1 | Log Loss | Brier | ECE |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for row in ordered:
        lines.append(f"| {row['model_name']} | {row['macro_f1']:.4f} | {row['accuracy']:.4f} | "
                     f"{row['weighted_f1']:.4f} | {row['log_loss']:.4f} | "
                     f"{row['brier_score']:.4f} | {row['ece']:.4f} |")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def comparison_csv(rows, path):
    fields = ("model_name", "seed", "accuracy", "macro_precision", "macro_recall", "macro_f1",
              "weighted_f1", "log_loss", "top2_accuracy", "top3_accuracy", "brier_score", "ece")
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def write_ablation_report(rows, path):
    rows = [asdict(row) if is_dataclass(row) else row for row in rows]
    full_by_seed = {row["seed"]: row["macro_f1"] for row in rows if not row.get("removed_feature")}
    lines = ["# AMPA feature ablation", "", "Delta is ablation macro F1 minus the full model for the same seed.", "",
             "| Removed feature | Seed | Macro F1 | Delta F1 |", "|---|---:|---:|---:|"]
    for row in rows:
        removed = row.get("removed_feature") or "None (all features)"
        delta = row["macro_f1"] - full_by_seed[row["seed"]]
        lines.append(f"| {removed} | {row['seed']} | {row['macro_f1']:.4f} | {delta:+.4f} |")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
