"""Run a live HTTP flow against a running Phase 5 API and its SQLite database."""

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import Question


BASE_URL = os.getenv("MISTIQ_API_URL", "http://127.0.0.1:8765").rstrip("/")


def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(BASE_URL + path, data=data, method=method,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} failed ({error.code}): {detail}") from error


def main():
    with SessionLocal() as session:
        question_id = (session.scalar(select(func.max(Question.question_id))) or 0) + 1
        question = Question(
            question_id=question_id, topic="Manual Integration", subtopic="Metrics",
            difficulty=2, question_text="Which answer is the designated correct choice?",
            option_a="Correct choice", option_b="Precision", option_c="Recall", option_d="F1",
            correct_option="A", estimated_time=60,
            error_mapping={"B": "CONCEPT_CONFUSION", "C": "CALCULATION_ERROR", "D": "PROCEDURE_ERROR"},
        )
        session.add(question)
        session.commit()

    health_status, health = request("GET", "/health")
    assert health_status == 200 and health["status"] == "ok", health
    status, student = request("POST", "/api/students", {"name": "Phase 5 E2E learner"})
    assert status == 201
    student_id = student["id"]
    selected = ["B", "A", "C", "B", "A"]
    for index, answer in enumerate(selected):
        status, result = request("POST", "/api/attempts", {
            "student_id": student_id, "question_id": question_id,
            "selected_option": answer, "response_time": 20,
            "idempotency_key": f"manual-e2e-{student_id}-{index}",
        })
        assert status == 201
    _, prediction = request("GET", f"/api/predictions/{student_id}/latest")
    _, explanation = request("GET", f"/api/predictions/{student_id}/latest/explanation")
    _, progress = request("GET", f"/api/students/{student_id}/progress")
    _, state = request("GET", f"/api/students/{student_id}/state")
    _, mistakes = request("GET", f"/api/students/{student_id}/mistakes")
    assert prediction["model"] == "MISTIQ-AMPA" and prediction["probability"] is not None
    assert explanation["reasons"]
    assert progress["attempt_count"] == 5 and len(mistakes) == 3
    assert state["attempt_count"] == 5
    print(json.dumps({
        "health": health, "student_id": student_id, "question_id": question_id,
        "attempt_count": progress["attempt_count"], "mistake_count": len(mistakes),
        "prediction": prediction, "explanation_contributors": len(explanation["reasons"]),
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
