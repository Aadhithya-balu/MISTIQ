from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import LearnerState
from app.services.mistake_analytics_service import build_mistake_analytics
from app.services.progress_service import build_progress, compare_accuracy
from app.services.recovery_service import analyze_recovery
from app.services.trajectory_service import build_trajectory
from backend.ml.ampa.features import _learning_stability


def make_history(outcomes=None):
    outcomes = outcomes or [False, False, False, True, False, True, True, True]
    history = []
    errors = ["CONCEPT_CONFUSION", "REPEATED_MISTAKE", "CALCULATION_ERROR", "CORRECT",
              "REPEATED_MISTAKE", "CORRECT", "CORRECT", "CORRECT"]
    for index, correct in enumerate(outcomes):
        error = "CORRECT" if correct else errors[index % len(errors)]
        if not correct and error == "CORRECT":
            error = "CALCULATION_ERROR"
        history.append({
            "attempt_id": index + 1, "student_id": 9, "question_id": index % 3 + 1,
            "attempt_number": index + 1, "selected_option": "B", "correct": correct,
            "response_time": 20 + index, "timestamp": datetime(2026, 1, 1) + timedelta(days=index),
            "topic": "Machine Learning" if index < 6 else "Statistics",
            "subtopic": "Metrics" if index < 6 else "Mean", "difficulty": index % 5 + 1,
            "selected_answer": "Precision" if not correct else "Recall",
            "correct_answer": "Recall", "error_type": error,
            "mistake_event_id": index + 101 if not correct else None,
            "mistake_timestamp": datetime(2026, 1, 1) + timedelta(days=index) if not correct else None,
        })
    return history


def test_comparable_accuracy_windows_and_minimum_sample_size():
    rows = make_history([False, False, True, False, True, True, True, False])
    comparison = compare_accuracy(rows)
    assert comparison["improvement_direction"] == "IMPROVING"
    assert comparison["improvement_value"] == 0.5
    assert comparison["sample_sizes"] == {"recent": 4, "previous": 4}
    assert compare_accuracy(rows[:5])["improvement_direction"] == "INSUFFICIENT_DATA"


def test_topic_subtopic_difficulty_and_summary_are_database_grounded():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    history = make_history([False, False, True, False, True, True, True, False])
    with Session(engine) as session:
        result = build_progress(session, 9, history)
    summary = result["summary"]
    assert summary["total_attempts"] == 8
    assert summary["total_correct"] == 4
    assert summary["total_incorrect"] == 4
    assert summary["overall_accuracy"] == 0.5
    assert summary["current_streak"] == 0
    assert summary["best_streak"] == 3
    assert {row["topic"] for row in result["topic_performance"]} == {"Machine Learning", "Statistics"}
    assert result["subtopic_performance"][0]["attempts"] > 0
    assert [row["difficulty"] for row in result["difficulty_performance"]] == [1, 2, 3, 4, 5]
    assert sum(row["attempts"] for row in result["difficulty_performance"]) == 8


def test_mistake_distribution_repeats_and_confusion_pairs_come_from_answers():
    rows = make_history()
    analytics = build_mistake_analytics(rows, 9)
    assert {row["error_type"] for row in analytics["distribution"]} == {
        "CONCEPT_CONFUSION", "CALCULATION_ERROR", "REPEATED_MISTAKE",
    }
    assert abs(sum(row["percentage_of_mistakes"] for row in analytics["distribution"]) - 1) < 1e-9
    assert analytics["repeated"]
    assert analytics["repeated"][0]["occurrences"] >= 2
    assert analytics["confusions"]["nodes"] == ["Precision", "Recall"]
    assert analytics["confusions"]["edges"][0]["occurrences"] >= 2
    assert analytics["confusions"]["edges"][0]["strength"] is None
    assert analytics["trend"] == "DECREASING"
    empty = build_mistake_analytics([], 9)
    assert empty["mistake_count"] == 0
    assert empty["timeline_message"] == "Keep practicing to reveal your mistake patterns."


def test_recovery_requires_complete_windows_and_trajectory_is_prefix_only():
    history = make_history()
    recovery = analyze_recovery(history, window=3)
    assert recovery["eligible_mistakes"] == 4
    assert recovery["recovery_count"] == 4
    assert recovery["recovery_rate"] == 1.0
    first, difficulty = build_trajectory(history)
    extended, _ = build_trajectory(history + make_history([True] * 3))
    assert first == extended[:len(first)]
    assert [point["attempt_number"] for point in first] == list(range(1, 9))
    assert len(difficulty) == len(first)
    assert first[0]["accuracy"] == 0.0


def test_stability_reuses_phase_feature_and_empty_student_is_safe():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    history = make_history([True, False, True, True, True, False, True, True, False, True])
    with Session(engine) as session:
        session.add(LearnerState(student_id=9, knowledge_stability=.42, mistake_momentum=-.3))
        session.commit()
        result = build_progress(session, 9, history)
        empty = build_progress(session, 10, [])
    assert result["stability"]["value"] == .42
    assert result["mistake_momentum"]["value"] == -.3
    points = build_trajectory(history)[0]
    assert points[-1]["learning_stability"] == _learning_stability(history)
    assert [point["learning_stability"] for point in points] == [
        _learning_stability(history[:index]) for index in range(1, len(history) + 1)
    ]
    assert empty["summary"]["overall_accuracy"] == 0
    assert empty["summary"]["improvement_direction"] == "INSUFFICIENT_DATA"
    assert empty["trajectory"] == []


def test_single_correct_attempt_has_safe_rates_and_insufficient_trends():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    one = make_history([True])
    with Session(engine) as session:
        result = build_progress(session, 9, one)
    assert result["summary"]["overall_accuracy"] == 1.0
    assert result["summary"]["recent_accuracy"] == 1.0
    assert result["summary"]["improvement_value"] is None
    assert result["summary"]["improvement_direction"] == "INSUFFICIENT_DATA"
    assert result["recovery"]["recovery_rate"] is None
    assert all(row["attempts"] == 0 and row["accuracy"] is None
               for row in result["difficulty_performance"] if row["difficulty"] != 1)
