from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from backend.ml.datasets.loader import load_dataset
from backend.ml.datasets.schema import (
    ATTEMPT_FIELDS, DIFFICULTY_LABELS, ERROR_TYPES, MISTAKE_EVENT_FIELDS,
    QUESTION_FIELDS, DatasetValidationError, validate_dataset,
)
from backend.ml.datasets.synthetic_generator import GeneratorConfig, generate_dataset, write_dataset


@pytest.fixture(scope="module")
def sample():
    return generate_dataset(GeneratorConfig(seed=17, students=8, questions=30, attempts=240))


def test_same_seed_is_reproducible():
    config = GeneratorConfig(seed=101, students=5, questions=12, attempts=80)
    assert generate_dataset(config) == generate_dataset(config)


def test_schema_and_requested_row_counts(sample):
    questions, attempts, events = sample
    assert len(questions) == 30
    assert len(attempts) == len(events) == 240
    assert tuple(questions[0]) == QUESTION_FIELDS
    assert tuple(attempts[0]) == ATTEMPT_FIELDS
    assert tuple(events[0]) == MISTAKE_EVENT_FIELDS


def test_categories_references_and_chronology_are_valid(sample):
    questions, attempts, events = sample
    validate_dataset(questions, attempts, events)
    assert {row["difficulty"] for row in questions} <= set(DIFFICULTY_LABELS)
    assert {row["error_type"] for row in events} <= set(ERROR_TYPES)
    question_ids = {row["question_id"] for row in questions}
    attempt_ids = {row["attempt_id"] for row in attempts}
    assert all(row["question_id"] in question_ids for row in attempts)
    assert all(row["attempt_id"] in attempt_ids for row in events)
    previous = {}
    for row in attempts:
        stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        assert row["student_id"] not in previous or stamp >= previous[row["student_id"]]
        previous[row["student_id"]] = stamp


def test_csv_files_can_be_loaded_and_validated():
    output_dir = Path(__file__).resolve().parents[2] / ".test-output"
    expected = write_dataset(output_dir, GeneratorConfig(seed=8, students=3, questions=7, attempts=18))
    loaded = load_dataset(output_dir)
    assert [len(table) for table in loaded] == [len(table) for table in expected]


def test_validator_rejects_bad_difficulty(sample):
    questions, attempts, events = deepcopy(sample)
    questions[0]["difficulty"] = 6
    with pytest.raises(DatasetValidationError, match="invalid difficulty"):
        validate_dataset(questions, attempts, events)


def test_validator_rejects_missing_question_reference(sample):
    questions, attempts, events = deepcopy(sample)
    attempts[0]["question_id"] = 999999
    with pytest.raises(DatasetValidationError, match="references missing question"):
        validate_dataset(questions, attempts, events)


def test_validator_rejects_invalid_error_type(sample):
    questions, attempts, events = deepcopy(sample)
    events[0]["error_type"] = "MADE_UP_ERROR"
    with pytest.raises(DatasetValidationError, match="invalid error_type"):
        validate_dataset(questions, attempts, events)
