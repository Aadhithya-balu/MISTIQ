"""Train a versioned AMPA artifact from chronological Phase 1 synthetic data."""

import argparse
from pathlib import Path

from backend.ml.ampa import MISTIQAMPA
from backend.ml.evaluation.splitting import build_next_mistake_examples, chronological_split
from backend.ml.datasets.loader import load_dataset

ROOT = Path(__file__).resolve().parents[1]


def train(dataset, output, seed=42, epochs=300):
    questions, attempts, mistakes = load_dataset(dataset)
    examples = build_next_mistake_examples(questions, attempts, mistakes)
    split = chronological_split(examples)
    training = split["train"]
    model = MISTIQAMPA(seed=seed, epochs=epochs).fit(
        [row["features"] for row in training], [row["target"] for row in training]
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    model.save(output)
    return model, len(training)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "synthetic")
    parser.add_argument("--output", type=Path, default=ROOT / "backend" / "ml" / "artifacts" / "ampa.npz")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=300)
    args = parser.parse_args(argv)
    if args.epochs < 1:
        parser.error("epochs must be positive")
    model, count = train(args.dataset, args.output, args.seed, args.epochs)
    print(f"Saved MISTIQ-AMPA {model.get_parameters()['version']} using {count} chronological training examples to {args.output}")


if __name__ == "__main__":
    main()
