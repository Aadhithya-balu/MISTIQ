"""Reproducible, behaviorally varied synthetic educational interactions.

Run from the repository root with:
    python -m backend.ml.datasets.synthetic_generator --seed 42

The generated examples are synthetic test data, not student records or model results.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

try:
    from backend.app.core.error_types import ErrorType
    from backend.ml.datasets.schema import (
        ATTEMPT_FIELDS, DIFFICULTY_LABELS, MISTAKE_EVENT_FIELDS, QUESTION_FIELDS,
        validate_dataset,
    )
except ModuleNotFoundError:
    from app.core.error_types import ErrorType
    from ml.datasets.schema import (
        ATTEMPT_FIELDS, DIFFICULTY_LABELS, MISTAKE_EVENT_FIELDS, QUESTION_FIELDS,
        validate_dataset,
    )

DEFAULT_CONCEPT_PAIRS = (
    ("Precision", "Recall"),
    ("Ridge", "Lasso"),
    ("Overfitting", "Underfitting"),
    ("Stack", "Queue"),
    ("BFS", "DFS"),
    ("Mean", "Median"),
    ("Classification", "Regression"),
)
BEHAVIOR_TYPES = (
    "FAST_ACCURATE", "SLOW_ACCURATE", "CONCEPT_CONFUSED", "CARELESS",
    "DIFFICULTY_SENSITIVE", "REPETITIVE_MISTAKE", "IMPROVING", "DECLINING",
)
_BEHAVIOR_PROFILES = {
    "FAST_ACCURATE": {"accuracy": 0.91, "speed": 0.68},
    "SLOW_ACCURATE": {"accuracy": 0.93, "speed": 1.48},
    "CONCEPT_CONFUSED": {"accuracy": 0.73, "speed": 1.17},
    "CARELESS": {"accuracy": 0.82, "speed": 0.91},
    "DIFFICULTY_SENSITIVE": {"accuracy": 0.92, "speed": 1.04},
    "REPETITIVE_MISTAKE": {"accuracy": 0.84, "speed": 1.07},
    "IMPROVING": {"accuracy": 0.70, "speed": 1.20},
    "DECLINING": {"accuracy": 0.91, "speed": 0.98},
}


@dataclass
class GeneratorConfig:
    seed: int = 42
    students: int = 100
    questions: int = 500
    attempts: int = 10_000
    min_response_time: float = 1.0
    max_response_time: float = 900.0
    concept_pairs: Sequence[tuple[str, str]] = field(default_factory=lambda: DEFAULT_CONCEPT_PAIRS)

    def validate(self) -> None:
        if self.students < 1 or self.questions < 1 or self.attempts < 1:
            raise ValueError("students, questions, and attempts must each be at least 1")
        if not 0 < self.min_response_time < self.max_response_time:
            raise ValueError("response time bounds must satisfy 0 < minimum < maximum")
        if not self.concept_pairs or any(len(pair) != 2 or not all(pair) for pair in self.concept_pairs):
            raise ValueError("concept_pairs must contain non-empty pairs")


def generate_dataset(config: GeneratorConfig | None = None):
    """Return question, attempt, and mistake-event row dictionaries."""
    config = config or GeneratorConfig()
    config.validate()
    rng = random.Random(config.seed)
    questions = _generate_questions(config, rng)
    attempts, events = _generate_interactions(config, rng, questions)
    validate_dataset(
        questions, attempts, events,
        min_response_time=config.min_response_time,
        max_response_time=config.max_response_time,
    )
    return questions, attempts, events


def write_dataset(output_dir: str | Path, config: GeneratorConfig | None = None):
    """Generate, validate, and write the three canonical CSV files."""
    questions, attempts, events = generate_dataset(config)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    _write_csv(destination / "questions.csv", QUESTION_FIELDS, questions)
    _write_csv(destination / "attempts.csv", ATTEMPT_FIELDS, attempts)
    _write_csv(destination / "mistake_events.csv", MISTAKE_EVENT_FIELDS, events)
    return questions, attempts, events


def _generate_questions(config: GeneratorConfig, rng: random.Random) -> list[dict]:
    concepts = [concept for pair in config.concept_pairs for concept in pair]
    rows = []
    for question_id in range(1, config.questions + 1):
        topic = rng.choice(concepts)
        paired_topic = _paired_concept(topic, config.concept_pairs)
        correct = rng.choice("ABCD")
        distractors = [choice for choice in "ABCD" if choice != correct]
        mappings = {
            distractors[0]: "CONCEPT_CONFUSION",
            distractors[1]: rng.choice(("CALCULATION_ERROR", "PROCEDURE_ERROR")),
            distractors[2]: "CARELESS_ERROR",
        }
        options = {letter: f"Synthetic answer choice {letter}" for letter in "ABCD"}
        options[correct] = f"Synthetic answer representing {topic}"
        options[distractors[0]] = f"A concept associated with {paired_topic}"
        rows.append({
            "question_id": question_id,
            "topic": topic,
            "subtopic": f"{topic} fundamentals",
            "difficulty": rng.choices((1, 2, 3, 4, 5), weights=(10, 20, 35, 23, 12))[0],
            "question_text": f"Synthetic practice question about {topic} (item {question_id}).",
            "option_a": options["A"], "option_b": options["B"],
            "option_c": options["C"], "option_d": options["D"],
            "correct_option": correct,
            "estimated_time": rng.randint(20, 150),
            "error_mapping": json.dumps(mappings, sort_keys=True, separators=(",", ":")),
        })
    return rows


def _generate_interactions(config: GeneratorConfig, rng: random.Random, questions: list[dict]):
    students = list(range(1, config.students + 1))
    behaviors = {student_id: rng.choice(BEHAVIOR_TYPES) for student_id in students}
    familiarity = {
        student_id: {pair_topic: rng.uniform(0.32, 0.91)
                     for pair in config.concept_pairs for pair_topic in pair}
        for student_id in students
    }
    mistake_history: dict[tuple[int, str], list[str]] = defaultdict(list)
    question_attempt_counts: dict[tuple[int, int], int] = defaultdict(int)
    last_timestamps = {
        student_id: datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=rng.randint(0, 28))
        for student_id in students
    }
    attempts, events = [], []

    for index in range(config.attempts):
        student_id = students[index % len(students)]
        question = rng.choice(questions)
        behavior = behaviors[student_id]
        topic = question["topic"]
        familiarity_score = familiarity[student_id][topic]
        difficulty = question["difficulty"]
        progress = (index // len(students)) / max(1, (config.attempts - 1) // len(students))
        probability_correct = _accuracy_probability(behavior, difficulty, familiarity_score, progress)
        correct = rng.random() < probability_correct

        if correct:
            selected_option = question["correct_option"]
            error_type = "CORRECT"
        else:
            mapping = json.loads(question["error_mapping"])
            selected_option = rng.choice(tuple(mapping))
            error_type = mapping[selected_option]
            history_key = (student_id, topic)
            repeat_chance = 0.46 if behavior == "REPETITIVE_MISTAKE" else 0.16
            if mistake_history[history_key] and rng.random() < repeat_chance:
                error_type = "REPEATED_MISTAKE"
            elif difficulty >= 4 and rng.random() < 0.20:
                error_type = "DIFFICULTY_FAILURE"
            elif behavior in ("FAST_ACCURATE", "CARELESS") and rng.random() < 0.12:
                error_type = "CARELESS_ERROR"
            elif behavior == "SLOW_ACCURATE" and rng.random() < 0.10:
                error_type = "TIME_PRESSURE"
            mistake_history[history_key].append(error_type)

        response_time = _response_time(
            rng, behavior, difficulty, familiarity_score, correct,
            config.min_response_time, config.max_response_time,
        )
        timestamp = last_timestamps[student_id] + timedelta(minutes=rng.randint(8, 360))
        last_timestamps[student_id] = timestamp
        key = (student_id, question["question_id"])
        question_attempt_counts[key] += 1
        attempt_id = index + 1
        timestamp_text = timestamp.isoformat().replace("+00:00", "Z")
        attempts.append({
            "attempt_id": attempt_id,
            "student_id": student_id,
            "question_id": question["question_id"],
            "selected_option": selected_option,
            "correct": correct,
            "response_time": round(response_time, 2),
            "timestamp": timestamp_text,
            "attempt_number": question_attempt_counts[key],
        })
        events.append({
            "mistake_event_id": attempt_id,
            "student_id": student_id,
            "attempt_id": attempt_id,
            "error_type": error_type,
            "topic": topic,
            "subtopic": question["subtopic"],
            "timestamp": timestamp_text,
        })
        familiarity[student_id][topic] = min(0.97, familiarity_score + (0.003 if correct else -0.001))
    return attempts, events


def _accuracy_probability(behavior: str, difficulty: int, familiarity: float, progress: float) -> float:
    profile = _BEHAVIOR_PROFILES[behavior]
    probability = profile["accuracy"] + (familiarity - 0.60) * 0.28
    probability += (difficulty - 3) * (-0.075 if behavior == "DIFFICULTY_SENSITIVE" else -0.035)
    if behavior == "IMPROVING":
        probability += 0.23 * progress
    elif behavior == "DECLINING":
        probability -= 0.22 * progress
    return min(0.98, max(0.12, probability))


def _response_time(rng, behavior, difficulty, familiarity, correct, minimum, maximum) -> float:
    speed = _BEHAVIOR_PROFILES[behavior]["speed"]
    if behavior == "FAST_ACCURATE":
        speed = 0.68
    elif behavior == "SLOW_ACCURATE":
        speed = 1.48
    elif behavior == "IMPROVING":
        speed *= 0.90
    elif behavior == "DECLINING":
        speed *= 1.12
    mean = (19 + difficulty * 14) * speed * (1.28 - 0.48 * familiarity)
    if not correct and behavior != "CARELESS":
        mean *= 1.10
    value = rng.lognormvariate(math.log(max(minimum, mean)), 0.32)
    return min(maximum, max(minimum, value))


def _paired_concept(topic: str, pairs: Sequence[tuple[str, str]]) -> str:
    for left, right in pairs:
        if topic == left:
            return right
        if topic == right:
            return left
    return topic


def _write_csv(path: Path, fields: Sequence[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--students", type=int, default=100)
    parser.add_argument("--questions", type=int, default=500)
    parser.add_argument("--attempts", type=int, default=10_000)
    parser.add_argument("--min-response-time", type=float, default=1.0)
    parser.add_argument("--max-response-time", type=float, default=900.0)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[3] / "data" / "synthetic")
    args = parser.parse_args(argv)
    config = GeneratorConfig(
        seed=args.seed, students=args.students, questions=args.questions,
        attempts=args.attempts, min_response_time=args.min_response_time,
        max_response_time=args.max_response_time,
    )
    try:
        questions, attempts, events = write_dataset(args.output_dir, config)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"Generated {len(questions)} questions, {len(attempts)} attempts, and {len(events)} mistake events in {args.output_dir}")


if __name__ == "__main__":
    main()
