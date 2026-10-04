"""Run Phase 4 chronological AMPA, baseline, calibration, and ablation studies."""

import argparse
from pathlib import Path

from backend.ml.evaluation.runner import run_evaluation

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, nargs="+", default=[42], help="one or more reproducible seeds")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "synthetic")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--ablation", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--baselines", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cold-start", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--learning-curve", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--calibration-bins", type=int, default=10)
    args = parser.parse_args(argv)
    if args.epochs < 1 or args.calibration_bins < 1:
        parser.error("epochs and calibration bins must be positive")
    summary = run_evaluation(
        dataset=args.dataset, output=args.output, seeds=args.seed, epochs=args.epochs,
        run_ablation=args.ablation, run_baselines=args.baselines,
        run_cold_start=args.cold_start, run_learning_curve=args.learning_curve,
        train_ratio=args.train_ratio, validation_ratio=args.validation_ratio,
        test_ratio=args.test_ratio, calibration_bins=args.calibration_bins,
    )
    print(f"Evaluation complete: {summary['results_count']} model runs, "
          f"{summary['ablations_count']} ablations. Results: {args.output}")


if __name__ == "__main__":
    main()
