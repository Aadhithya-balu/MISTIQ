"""Run a complete, isolated MISTIQ demo through real API and ML services.

The demo creates clearly identified synthetic questions in an in-memory SQLite
database. It loads the checked-in AMPA artifact and persists no student data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import create_app
from app.services.ampa_service import AMPAService
from app.models import Question


QUESTIONS = [
    ("Precision", "Which metric is true positives divided by all predicted positives?", "Precision", "Recall", "F1 score", "Accuracy"),
    ("Recall", "Which metric is true positives divided by all actual positives?", "Recall", "Precision", "Specificity", "Accuracy"),
    ("Ridge", "Which regularizer applies an L2 penalty to coefficients?", "Ridge", "Lasso", "Elastic net", "None"),
    ("Lasso", "Which regularizer can drive coefficients to exactly zero with an L1 penalty?", "Lasso", "Ridge", "Elastic net", "None"),
    ("Overfitting", "Which condition often has low training error but high test error?", "Overfitting", "Underfitting", "Balanced fit", "Data scaling"),
    ("Underfitting", "Which condition describes a model too simple to capture the training pattern?", "Underfitting", "Overfitting", "Data leakage", "Regularization"),
    ("Stack", "Which structure normally follows last-in, first-out order?", "Stack", "Queue", "Heap", "Graph"),
    ("Queue", "Which structure normally follows first-in, first-out order?", "Queue", "Stack", "Heap", "Tree"),
]


def _check(response, expected=(200,)):
    if response.status_code not in expected:
        raise RuntimeError(f"{response.request.method} {response.request.url} returned {response.status_code}: {response.text}")
    return response.json()


def main() -> None:
    artifact = ROOT / "backend" / "ml" / "artifacts" / "ampa.npz"
    if not artifact.is_file():
        raise SystemExit(f"AMPA artifact is missing: {artifact}. See docs/backend-ml-integration.md to train it.")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        for index, row in enumerate(QUESTIONS, start=1):
            concept, prompt, a, b, c, d = row
            session.add(Question(
                question_id=index, topic="Machine Learning", subtopic=concept,
                difficulty=2 + (index - 1) // 2, question_text=prompt,
                option_a=a, option_b=b, option_c=c, option_d=d,
                correct_option="A", estimated_time=45,
                error_mapping={"B": "CONCEPT_CONFUSION", "C": "CALCULATION_ERROR", "D": "PROCEDURE_ERROR"},
            ))
        session.commit()
    service = AMPAService(artifact)
    application = create_app(database_engine=engine, ampa_service=service)

    with TestClient(application) as client:
        assert _check(client.get("/health"))["status"] == "ok"
        assert service.model is not None and service.model.fitted_
        student = _check(client.post("/api/students", json={"name": "MISTIQ demo learner"}), (201,))
        student_id = student["id"]
        questions = _check(client.get("/api/questions"))
        if len(questions) != len(QUESTIONS) or "correct_option" in questions[0]:
            raise RuntimeError("Public question API contract did not match the demo bank")

        first_attempts = []
        for index, selected in enumerate(("B", "A", "B", "A", "B"), start=1):
            result = _check(client.post("/api/attempts", json={
                "student_id": student_id, "question_id": 1,
                "selected_option": selected, "response_time": 28 + index,
                "idempotency_key": f"phase10-demo-{student_id}-{index}",
            }), (201,))
            if result["attempt"]["correct"] != (selected == "A"):
                raise RuntimeError("Attempt correctness did not come from the stored question")
            first_attempts.append(result)

        prediction = _check(client.get(f"/api/predictions/{student_id}/latest"))
        explanation = _check(client.get(f"/api/predictions/{student_id}/latest/explanation"))
        if prediction["model"] != "MISTIQ-AMPA" or not explanation["reasons"]:
            raise RuntimeError("Live AMPA prediction or explanation is unavailable")

        recommendation = _check(client.get(f"/api/recommendations/{student_id}/next"))
        recommendation_id = recommendation["recommendation"]["id"]
        recommended_question_id = recommendation["question"]["question_id"]
        before = _check(client.get(f"/api/progress/{student_id}"))
        mistakes_before = _check(client.get(f"/api/mistakes/{student_id}/summary"))
        state = _check(client.get(f"/api/students/{student_id}/state"))

        next_attempt = _check(client.post("/api/attempts", json={
            "student_id": student_id, "question_id": recommended_question_id,
            "selected_option": "B", "response_time": 31,
            "idempotency_key": f"phase10-demo-recommended-{student_id}",
        }), (201,))
        if next_attempt["attempt"]["question_id"] != recommended_question_id:
            raise RuntimeError("The recommendation question was not practiced")
        recommendations = _check(client.get(f"/api/recommendations/{student_id}"))
        completed = next(row for row in recommendations if row["id"] == recommendation_id)
        after = _check(client.get(f"/api/progress/{student_id}"))
        mistakes_after = _check(client.get(f"/api/mistakes/{student_id}/summary"))
        latest_prediction = next_attempt["prediction"]
        if latest_prediction is None:
            raise RuntimeError("AMPA did not calculate a prediction after the recommended attempt")
        trace = _check(client.get(f"/api/research/prediction/{latest_prediction['id']}/trace"))
        evaluation = _check(client.get("/api/research/evaluation"))
        if not evaluation["available"]:
            raise RuntimeError("Phase 4 evaluation artifacts are unavailable")

        report = {
            "database": "in-memory SQLite (discarded on exit)",
            "model": {"name": prediction["model"], "version": prediction["model_version"],
                      "trained": service.model.fitted_},
            "student_id": student_id,
            "question_count_loaded": len(questions),
            "attempts_before_recommendation": before["attempt_count"],
            "initial_mistakes": mistakes_before["mistake_count"],
            "learner_state_attempt_count": state["attempt_count"],
            "initial_prediction": prediction["prediction"],
            "explanation_reasons": len(explanation["reasons"]),
            "recommendation_id": recommendation_id,
            "recommended_question_id": recommended_question_id,
            "recommendation_completed": completed["completed_at"] is not None,
            "attempts_after_practice": after["attempt_count"],
            "mistakes_after_practice": mistakes_after["mistake_count"],
            "new_prediction_id": latest_prediction["id"],
            "new_prediction": latest_prediction["prediction"],
            "research_trace_matches_stored": trace["replay_matches_stored"],
            "evaluation_rows": len(evaluation["results"]),
        }
        print(json.dumps(report, indent=2))
        if after["attempt_count"] != before["attempt_count"] + 1 or not report["recommendation_completed"] or not trace["replay_matches_stored"]:
            raise RuntimeError("End-to-end demo acceptance check failed")


if __name__ == "__main__":
    main()
