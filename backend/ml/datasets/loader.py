"""Load and validate the canonical synthetic dataset CSV files."""

import csv
from pathlib import Path

try:
    from backend.ml.datasets.schema import validate_dataset
except ModuleNotFoundError:
    from ml.datasets.schema import validate_dataset


def load_dataset(directory: str | Path):
    """Read the three CSVs, validate their contents, and return row dictionaries."""
    directory = Path(directory)
    names = ("questions", "attempts", "mistake_events")
    tables = {}
    for name in names:
        path = directory / f"{name}.csv"
        try:
            with path.open(newline="", encoding="utf-8") as source:
                tables[name] = list(csv.DictReader(source))
        except OSError as error:
            raise ValueError(f"could not read {path}: {error}") from error
    validate_dataset(tables["questions"], tables["attempts"], tables["mistake_events"])
    return tables["questions"], tables["attempts"], tables["mistake_events"]
