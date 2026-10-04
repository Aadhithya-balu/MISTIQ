"""Create a deterministic synthetic showcase through MISTIQ's real API pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.main import create_app
from app.models import Question
from app.services.ampa_service import AMPAService
from ml.datasets.synthetic_generator import GeneratorConfig, generate_dataset
from reset_showcase import DATABASE, SHOWCASE_DIR, reset_showcase


ARTIFACT = ROOT / "backend" / "ml" / "artifacts" / "ampa.npz"
STUDENT_NAME = "Aadhi Demo Student"


def _curated_questions() -> list[dict]:
    definitions = [
        ("Precision", "Which metric divides true positives by all predicted positives?", "Recall", 2),
        ("Recall", "Which metric divides true positives by all actual positives?", "Precision", 2),
        ("Precision", "A search returns 10 items, 4 relevant. Which metric is 4 divided by 10?", "Recall", 3),
        ("Recall", "There are 8 relevant items and the system finds 6. Which metric is 6 divided by 8?", "Precision", 3),
        ("Precision", "Which metric answers how many positive predictions were correct?", "Recall", 4),
        ("Recall", "Which metric answers how many actual positives were found?", "Precision", 4),
        ("Precision", "For a high cost of false positives, which metric is most directly relevant?", "Recall", 2),
        ("Recall", "For a high cost of missed positives, which metric is most directly relevant?", "Precision", 3),
        ("Ridge", "Which method uses an L2 coefficient penalty?", "Lasso", 2),
        ("Stack", "Which data structure follows last in, first out?", "Queue", 2),
        ("Mean", "Which measure is more sensitive to extreme values?", "Median", 3),
        ("Overfitting", "Which condition often has low training error and high test error?", "Underfitting", 4),
        ("Classification", "Which task predicts a discrete label?", "Regression", 2),
        ("BFS", "Which graph traversal explores neighbors level by level?", "DFS", 3),
    ]
    rows = []
    for offset, (topic, prompt, paired, difficulty) in enumerate(definitions, start=501):
        rows.append({
            "question_id": offset, "topic": topic, "subtopic": topic,
            "difficulty": difficulty, "question_text": prompt,
            "option_a": f"{topic}", "option_b": f"{paired}",
            "option_c": "A measure based on the mean of all observations",
            "option_d": "A randomized method unrelated to this concept",
            "correct_option": "A", "estimated_time": 120,
            "error_mapping": {"B": "CONCEPT_CONFUSION", "C": "CALCULATION_ERROR",
                              "D": "CARELESS_ERROR"},
        })
    return rows


def _history() -> list[tuple[int, str, float]]:
    early = [(509, "A", 58), (510, "C", 74), (511, "A", 69), (512, "A", 66)]
    confusion = [(question_id, "B", 80 + index)
                 for index, question_id in enumerate(range(501, 509))]
    improvement = [(question_id, "A", 46 - index)
                   for index, question_id in enumerate((501, 502, 503, 504, 505, 506, 507, 508))]
    later = [
        (501, "B", 75),  # A new occurrence on the same item is classified from prior history.
        (513, "B", 73), (511, "A", 52), (514, "B", 72), (509, "A", 48),
        (513, "A", 46), (502, "A", 43), (504, "A", 41), (507, "A", 40), (508, "A", 39),
    ]
    return early + confusion + improvement + later


def setup_showcase() -> dict:
    if not ARTIFACT.is_file():
        raise FileNotFoundError(f"Trained local AMPA artifact not found: {ARTIFACT}")
    SHOWCASE_DIR.mkdir(parents=True, exist_ok=True)
    reset_showcase()
    url = f"sqlite:///{DATABASE.as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        generated, _, _ = generate_dataset(GeneratorConfig(seed=42, students=1, questions=500, attempts=1))
        questions = generated + _curated_questions()
        factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with factory() as session:
            session.add_all([Question(**{
                **row,
                "error_mapping": (json.loads(row["error_mapping"])
                                  if isinstance(row["error_mapping"], str) else row["error_mapping"]),
            }) for row in questions])
            session.commit()

        service = AMPAService(ARTIFACT)
        app = create_app(database_engine=engine, ampa_service=service)
        with TestClient(app) as client:
            if client.get("/health").json().get("status") != "ok":
                raise RuntimeError("Showcase database health check failed")
            student_response = client.post("/api/students", json={"name": STUDENT_NAME})
            student_response.raise_for_status()
            student_id = student_response.json()["id"]
            for index, (question_id, selected, response_time) in enumerate(_history(), start=1):
                response = client.post("/api/attempts", json={
                    "student_id": student_id, "question_id": question_id,
                    "selected_option": selected, "response_time": response_time,
                    "idempotency_key": f"showcase-{student_id}-{index}",
                })
                if response.status_code != 201:
                    raise RuntimeError(f"Showcase attempt {index} failed: {response.status_code} {response.text}")
            prediction = client.get(f"/api/predictions/{student_id}/latest")
            prediction.raise_for_status()
            explanation = client.get(f"/api/predictions/{student_id}/latest/explanation")
            explanation.raise_for_status()
            recommendation = client.get(f"/api/recommendations/{student_id}/next")
            recommendation.raise_for_status()
            recommended_topic = recommendation.json()["question"]["topic"]
            if recommended_topic not in {"Precision", "Recall"}:
                raise RuntimeError(f"Expected pair-focused practice, got topic {recommended_topic!r}")
            progress = client.get(f"/api/progress/{student_id}")
            progress.raise_for_status()
            analytics = client.get(f"/api/mistakes/{student_id}/summary")
            analytics.raise_for_status()
            trace = client.get(f"/api/research/prediction/{prediction.json()['id']}/trace")
            trace.raise_for_status()
            trace_data = trace.json()
            if trace_data["verification_status"] != "EXACT":
                raise RuntimeError(f"Showcase research trace verification failed: {trace_data['verification_status']}")
            result = {
                "mode": "Showcase Mode — Synthetic Data",
                "database": str(DATABASE), "student_id": student_id,
                "student_name": STUDENT_NAME, "questions": len(questions),
                "attempts": progress.json()["attempt_count"],
                "mistakes": analytics.json()["mistake_count"],
                "concept_confusions": analytics.json()["confusions"]["edges"],
                "prediction": prediction.json()["prediction"],
                "prediction_status": prediction.json()["status"],
                "explanation_reasons": len(explanation.json()["reasons"]),
                "recommended_topic": recommended_topic,
                "recommended_question_id": recommendation.json()["question"]["question_id"],
                "research_trace": trace_data["verification_status"],
            }
            return result
    finally:
        engine.dispose()


if __name__ == "__main__":
    report = setup_showcase()
    print(json.dumps(report, indent=2))
