# Showcase service
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Attempt, LearnerState, MistakeEvent, Prediction, Question, Recommendation, Student
from app.schemas.entities import AttemptCreate
from app.services.ampa_service import AMPAService
from app.services.recommendation_service import RecommendationService

DEMO_STUDENT_NAME = "Aadhi Demo Student"
DEMO_STUDENT_ID = 1


def _question(topic: str, text: str, options: list[str], difficulty: int,
              paired: str, correct_option: str = "A", subtopic: str | None = None,
              error_mapping: dict[str, str] | None = None) -> dict[str, Any]:
    """Build one curated confidence question with its distractor error mapping."""
    default_mapping = {
        opt: ("CONCEPT_CONFUSION" if opt == ("B" if correct_option != "B" else "A") else "CARELESS_ERROR")
        for opt in ["A", "B", "C", "D"] if opt != correct_option
    }
    return {
        "topic": topic, "subtopic": subtopic, "difficulty": difficulty,
        "question_text": text, "options": options, "correct_option": correct_option,
        "estimated_time": 60,
        "error_mapping": error_mapping or default_mapping,
        "_paired": paired,
    }


_CURATED_QUESTIONS: tuple[dict[str, Any], ...] = (
    # 501-508: Precision & Recall (Evaluation Metrics)
    _question("Precision", "Which metric divides true positives by all predicted positives?",
              ["Precision", "Recall", "Accuracy", "F1"], 2, "Recall", "A", "Metrics",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),
    _question("Recall", "Which metric divides true positives by all actual positives?",
              ["Recall", "Precision", "Accuracy", "F1"], 2, "Precision", "A", "Metrics",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),
    _question("Precision", "A search returns 10 items, 4 of which are relevant. Which metric is 4 divided by 10?",
              ["Precision", "Recall", "Accuracy", "F1"], 3, "Recall", "A", "Calculation",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),
    _question("Recall", "There are 8 relevant items and the system returns 6 of them. Which metric is 6 divided by 8?",
              ["Recall", "Precision", "Accuracy", "F1"], 3, "Precision", "A", "Calculation",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),
    _question("Precision", "Which metric answers: of the predicted positives, how many were correct?",
              ["Precision", "Recall", "Accuracy", "F1"], 3, "Recall", "A", "Intuition",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),
    _question("Recall", "Which metric answers: of the actual positives, how many were found?",
              ["Recall", "Precision", "Accuracy", "F1"], 3, "Precision", "A", "Intuition",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),
    _question("Precision", "When false positives are very costly, which metric matters most?",
              ["Precision", "Recall", "Accuracy", "F1"], 2, "Recall", "A", "Cost Sensitivity",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),
    _question("Recall", "When missed positives are very costly, which metric matters most?",
              ["Recall", "Precision", "Accuracy", "F1"], 3, "Precision", "A", "Cost Sensitivity",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),

    # 509-514: Curriculum Anchors
    _question("Ridge", "Which penalty does ridge regression apply to the coefficients?",
              ["Ridge (L2 Squared)", "Lasso (L1 Absolute)", "Elastic Net", "Ordinary Least Squares"], 2, "Lasso", "A", "Penalty",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Stack", "Which data structure follows last in, first out (LIFO)?",
              ["Stack (LIFO)", "Queue (FIFO)", "Tree", "Heap"], 2, "Queue", "A", "Ordering",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Mean", "Which central-tendency measure is most sensitive to extreme values?",
              ["Mean", "Median", "Mode", "Range"], 2, "Median", "A", "Sensitivity",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Overfitting", "Which condition typically shows low training error but high test error?",
              ["Overfitting (High Variance)", "Underfitting (High Bias)", "L2 Regularization", "Cross-Validation"], 3, "Underfitting", "A", "Generalization",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Classification", "Which task predicts a discrete label rather than a continuous number?",
              ["Classification", "Regression", "Clustering", "Ranking"], 2, "Regression", "A", "Task Type",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("BFS", "Which graph traversal explores all neighbors of a node before going deeper?",
              ["Breadth-First Search (BFS)", "Depth-First Search (DFS)", "Dijkstra", "A* Search"], 3, "Depth-First Search", "A", "Traversal",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),

    # 515-535: Paired Concepts & Multi-Concept Practice
    _question("Lasso", "Which regularization method drives non-essential weights to exactly zero for feature selection?",
              ["Ridge Regression", "Lasso Regression (L1)", "Dropout", "Early Stopping"], 3, "Ridge", "B", "Feature Sparsity",
              {"A": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Ridge", "When features exhibit strong multicollinearity, which model keeps all features with stable weights?",
              ["Stepwise Selection", "Decision Tree", "Ridge Regression (L2)", "Lasso (L1)"], 3, "Lasso", "C", "Multicollinearity",
              {"A": "PROCEDURE_ERROR", "B": "CARELESS_ERROR", "D": "CONCEPT_CONFUSION"}),
    _question("Lasso", "Geometrically, why does L1 regularization produce sparse solutions?",
              ["It has smooth spherical contours", "It has sharp diamond corners that intersect loss contours on axes", "It uses second-order derivatives", "It normalizes data to unit variance"], 4, "Ridge", "B", "Geometry",
              {"A": "CONCEPT_CONFUSION", "C": "PROCEDURE_ERROR", "D": "CARELESS_ERROR"}),

    _question("Underfitting", "A model has 51% training accuracy and 50% test accuracy on data with a 95% human baseline. What is the diagnosis?",
              ["Overfitting (High Variance)", "Label Leakage", "Exploding Gradients", "Underfitting (High Bias)"], 2, "Overfitting", "D", "Generalization",
              {"A": "CONCEPT_CONFUSION", "B": "CARELESS_ERROR", "C": "PROCEDURE_ERROR"}),
    _question("Overfitting", "Which method directly mitigates overfitting by penalizing large model parameters?",
              ["Adding more hidden layers", "L1 / L2 Regularization", "Increasing learning rate", "Removing validation sets"], 3, "Underfitting", "B", "Remediation",
              {"A": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Underfitting", "If a linear model cannot capture a cyclical seasonal sales curve, what is the best immediate solution?",
              ["Increase model capacity by adding polynomial features", "Add heavy L1 penalty", "Shrink training set", "Decrease epochs"], 3, "Overfitting", "A", "Remediation",
              {"B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),

    _question("Regression", "Predicting the continuous market price of a home in dollars based on location and size is which type of task?",
              ["Classification", "Clustering", "Regression", "Association Rules"], 2, "Classification", "C", "Task Type",
              {"A": "CONCEPT_CONFUSION", "B": "PROCEDURE_ERROR", "D": "CARELESS_ERROR"}),
    _question("Classification", "Despite its historical name, Logistic Regression is primarily used for which machine learning task?",
              ["Continuous estimation", "Discrete Classification", "Dimensionality Reduction", "Kernel Density"], 3, "Regression", "B", "Task Nuance",
              {"A": "CONCEPT_CONFUSION", "C": "PROCEDURE_ERROR", "D": "CARELESS_ERROR"}),
    _question("Regression", "Which loss function is specifically used for regression models but not for discrete classification?",
              ["Mean Squared Error (MSE)", "Cross-Entropy Loss", "Hinge Loss", "F1 Score"], 3, "Classification", "A", "Loss Functions",
              {"B": "CARELESS_ERROR", "C": "PROCEDURE_ERROR", "D": "CONCEPT_CONFUSION"}),

    _question("Queue", "Which data structure follows the first in, first out (FIFO) access order?",
              ["Stack", "Queue (FIFO)", "Heap", "Binary Search Tree"], 2, "Stack", "B", "Ordering",
              {"A": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Stack", "Which data structure is naturally utilized to implement an Undo history mechanism in text editors?",
              ["Queue", "FIFO Buffer", "Stack (LIFO)", "Linked Ring"], 2, "Queue", "C", "Applications",
              {"A": "CONCEPT_CONFUSION", "B": "CONCEPT_CONFUSION", "D": "CARELESS_ERROR"}),
    _question("Queue", "A network printer buffer servicing documents in submission order relies on which structure?",
              ["Stack", "Recursion Stack", "Vector", "Queue (FIFO)"], 2, "Stack", "D", "Applications",
              {"A": "CONCEPT_CONFUSION", "B": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR"}),

    _question("DFS", "Which graph traversal follows each branch down to its deepest unvisited node before backtracking?",
              ["Depth-First Search (DFS)", "Breadth-First Search (BFS)", "Kruskal Algorithm", "Bellman-Ford"], 2, "BFS", "A", "Traversal",
              {"B": "CONCEPT_CONFUSION", "C": "PROCEDURE_ERROR", "D": "CARELESS_ERROR"}),
    _question("BFS", "On an unweighted graph, which search guarantees finding the shortest path with minimum edges?",
              ["Depth-First Search", "Breadth-First Search (BFS)", "Topological Sort", "Eulerian Path"], 3, "DFS", "B", "Shortest Path",
              {"A": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("DFS", "While BFS requires a Queue, standard DFS is fundamentally implemented using which mechanism?",
              ["FIFO Queue", "Priority Queue", "Stack or Call-Stack Recursion", "Double-ended Deque"], 3, "BFS", "C", "Data Structures",
              {"A": "CONCEPT_CONFUSION", "B": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),

    _question("Median", "In a country where 99% earn $40k and 1% earn $50M, which statistic best reflects the typical person's earnings?",
              ["Arithmetic Mean", "Standard Deviation", "Median (50th percentile)", "Variance"], 2, "Mean", "C", "Central Tendency",
              {"A": "CONCEPT_CONFUSION", "B": "PROCEDURE_ERROR", "D": "CARELESS_ERROR"}),
    _question("Mean", "In a symmetric normal bell curve distribution with zero skew, what is the relation between Mean and Median?",
              ["Mean > Median", "Mean == Median", "Mean < Median", "Mean == 0 and Median == 1"], 3, "Median", "B", "Symmetry",
              {"A": "CARELESS_ERROR", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Median", "What is the median value of the sorted observations: [2, 5, 8, 12, 16, 20]?",
              ["8", "10", "12", "14"], 2, "Mean", "B", "Calculation",
              {"A": "CARELESS_ERROR", "C": "CARELESS_ERROR", "D": "CALCULATION_ERROR"}),
    _question("Lasso", "Which hyperparameter in L1 regularization controls the penalty weight against non-zero coefficients?",
              ["Lambda (or Alpha)", "Learning Rate", "Batch Size", "Momentum Beta"], 3, "Ridge", "A", "Hyperparameters",
              {"B": "CARELESS_ERROR", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Stack", "What condition occurs when attempting to pop an element from a stack that has zero elements?",
              ["Stack Overflow", "Stack Underflow", "Memory Segmentation", "Heap Collision"], 2, "Queue", "B", "Edge Cases",
              {"A": "CARELESS_ERROR", "C": "PROCEDURE_ERROR", "D": "PROCEDURE_ERROR"}),
    _question("Queue", "In a standard queue implementation, elements are enqueued at the rear and dequeued from where?",
              ["Top", "Front", "Middle", "Random Index"], 2, "Stack", "B", "Operations",
              {"A": "CONCEPT_CONFUSION", "C": "CARELESS_ERROR", "D": "PROCEDURE_ERROR"}),
)


# Deterministic practice history for the demo student.
# Covers all 14 topics across 7 core modules with realistic performance (~78% accuracy).
# The final seeded attempt is a Recall concept confusion on Q506; Q507 (Precision) is left
# unattempted so the live demo and automated tests exercise it against the stored prediction.
_SEED_ATTEMPTS: tuple[tuple[int, str], ...] = (
    # Precision & Recall (501-505, 508)
    (501, "A"), (502, "B"), (503, "B"), (504, "A"), (505, "A"),
    (501, "B"), (502, "A"), (508, "B"),
    # Curriculum Anchors (509-514)
    (509, "A"), (510, "A"), (511, "A"), (512, "A"), (513, "A"), (514, "A"),
    # Paired Topics: Lasso, Underfitting, Regression, Queue, DFS, Median
    (515, "B"), (516, "C"), (517, "A"),
    (518, "D"), (519, "B"), (520, "A"),
    (521, "C"), (522, "B"), (523, "A"),
    (524, "B"), (525, "C"), (526, "D"),
    (527, "A"), (528, "B"), (529, "C"),
    (530, "C"), (531, "B"), (532, "B"),
    # Anchor finale: 506 Recall correct, then 506 Recall concept confusion with Precision
    (506, "A"), (506, "B"),
)

_SEED_RESPONSE_TIME = 30.0


def get_or_create_demo_student(session: Session) -> Student:
    student = session.get(Student, DEMO_STUDENT_ID)
    if student is not None:
        if student.name != DEMO_STUDENT_NAME:
            student.name = DEMO_STUDENT_NAME
            session.commit()
            session.refresh(student)
        return student
    student = Student(id=DEMO_STUDENT_ID, name=DEMO_STUDENT_NAME)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def reset_demo_student(session: Session, ampa_service: AMPAService | None = None) -> bool:
    """Remove the demo student's dependent rows while keeping the student identity."""
    for model in (Recommendation, Prediction, MistakeEvent, Attempt, LearnerState):
        session.execute(delete(model).where(model.student_id == DEMO_STUDENT_ID))
    session.commit()
    if ampa_service is not None and ampa_service.model is not None:
        ampa_service.model.clear_student(DEMO_STUDENT_ID)
    return True


def ensure_curated_questions(session: Session) -> int:
    """Upsert the curated demo question bank with stable IDs 501-514."""
    for index, definition in enumerate(_CURATED_QUESTIONS, start=501):
        question_id = index
        existing = session.get(Question, question_id)
        if existing is None:
            existing = Question(question_id=question_id)
            session.add(existing)
        existing.topic = definition["topic"]
        existing.subtopic = definition["subtopic"]
        existing.difficulty = definition["difficulty"]
        existing.question_text = definition["question_text"]
        existing.option_a, existing.option_b = definition["options"][0], definition["options"][1]
        existing.option_c, existing.option_d = definition["options"][2], definition["options"][3]
        existing.correct_option = definition["correct_option"]
        existing.estimated_time = definition["estimated_time"]
        existing.error_mapping = definition["error_mapping"]
    session.commit()
    return len(_CURATED_QUESTIONS)


def seed_demo_history(session: Session, ampa_service: AMPAService) -> dict[str, Any]:
    """Replay the curated history through the same pipeline as POST /attempts.

    Commit happens inside each submit_attempt call, and a small delay keeps
    timestamps strictly monotonic so the in-memory student state stays consistent.
    """
    seeded = 0
    for index, (question_id, selected_option) in enumerate(_SEED_ATTEMPTS, start=1):
        payload = AttemptCreate(
            student_id=DEMO_STUDENT_ID, question_id=question_id,
            selected_option=selected_option, response_time=_SEED_RESPONSE_TIME,
            idempotency_key=f"showcase-{index:03d}",
        )
        ampa_service.submit_attempt(session, payload)
        seeded += 1
        time.sleep(0.006)
    latest = session.scalar(
        select(Prediction).where(Prediction.student_id == DEMO_STUDENT_ID)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
    )
    return {
        "attempts_seeded": seeded,
        "latest_prediction_error": latest.predicted_error if latest else None,
        "latest_prediction_status": latest.status if latest else None,
    }


def demo_status(session: Session) -> dict[str, Any]:
    student = session.get(Student, DEMO_STUDENT_ID)
    attempt_count = session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.student_id == DEMO_STUDENT_ID)
    ) or 0
    mistake_count = session.scalar(
        select(func.count()).select_from(MistakeEvent).where(MistakeEvent.student_id == DEMO_STUDENT_ID)
    ) or 0
    latest_prediction = session.scalar(
        select(Prediction).where(Prediction.student_id == DEMO_STUDENT_ID)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
    )
    latest_attempt = session.scalar(
        select(Attempt).where(Attempt.student_id == DEMO_STUDENT_ID)
        .order_by(Attempt.timestamp.desc(), Attempt.attempt_id.desc())
    )
    has_learner_state = (
        session.scalar(
            select(func.count()).select_from(LearnerState).where(LearnerState.student_id == DEMO_STUDENT_ID)
        ) or 0
    ) > 0
    return {
        "student_id": DEMO_STUDENT_ID,
        "student_name": student.name if student else None,
        "seeded": student is not None and attempt_count > 0,
        "attempt_count": attempt_count,
        "mistake_count": mistake_count,
        "has_learner_state": has_learner_state,
        "latest_prediction_error": latest_prediction.predicted_error if latest_prediction else None,
        "latest_prediction_status": latest_prediction.status if latest_prediction else None,
        "latest_attempt_question_id": latest_attempt.question_id if latest_attempt else None,
    }


def setup_showcase_in_normal_db(engine, ampa_service: AMPAService) -> dict[str, Any]:
    """Create/reset the demo student, seed the curated bank, and report the result.

    This is the single entry point used by scripts/setup_showcase.py. All state is
    written through the real AMPA pipeline into the normal application database.
    """
    from sqlalchemy.orm import sessionmaker
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        demo = get_or_create_demo_student(session)
        reset_demo_student(session, ampa_service)
        ensure_curated_questions(session)
        seeded = seed_demo_history(session, ampa_service)
        recommender = RecommendationService()
        recommendation = recommender.recommend_next(session, demo.id)
        session.commit()
        try:
            recommended_question = recommendation.question
            recommended_topic = recommended_question.subtopic or recommended_question.topic
            recommendation_type = recommendation.type
        except AttributeError:
            recommended_topic = None
            recommendation_type = None
        latest_attempt = session.scalar(
            select(Attempt).where(Attempt.student_id == DEMO_STUDENT_ID)
            .order_by(Attempt.timestamp.desc(), Attempt.attempt_id.desc())
        )
        latest_mistake = session.scalar(
            select(MistakeEvent).where(MistakeEvent.student_id == DEMO_STUDENT_ID)
            .order_by(MistakeEvent.timestamp.desc(), MistakeEvent.mistake_event_id.desc())
        )
        latest_prediction = session.scalar(
            select(Prediction).where(Prediction.student_id == DEMO_STUDENT_ID)
            .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        )
        attempt_count = session.scalar(
            select(func.count()).select_from(Attempt).where(Attempt.student_id == DEMO_STUDENT_ID)
        ) or 0
        mistake_count = session.scalar(
            select(func.count()).select_from(MistakeEvent).where(MistakeEvent.student_id == DEMO_STUDENT_ID)
        ) or 0
        has_learner_state = (
            session.scalar(
                select(func.count()).select_from(LearnerState).where(LearnerState.student_id == DEMO_STUDENT_ID)
            ) or 0
        ) > 0
        return {
            "student_id": demo.id,
            "student_name": demo.name,
            "attempt_count": attempt_count,
            "mistake_count": mistake_count,
            "has_prediction": latest_prediction is not None,
            "prediction_error": latest_prediction.predicted_error if latest_prediction else None,
            "prediction_status": latest_prediction.status if latest_prediction else None,
            "prediction_probability": latest_prediction.probability if latest_prediction else None,
            "has_learner_state": has_learner_state,
            "latest_attempt_question_id": latest_attempt.question_id if latest_attempt else None,
            "latest_mistake_error_type": latest_mistake.error_type.value if latest_mistake else None,
            "recommended_question_id": recommendation.question_id if recommendation else None,
            "recommended_topic": recommended_topic,
            "recommendation_type": recommendation_type,
            "seeded_attempts": seeded["attempts_seeded"],
        }