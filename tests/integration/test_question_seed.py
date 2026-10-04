import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Question
from backend.ml.datasets.synthetic_generator import GeneratorConfig, generate_dataset
from scripts.seed_question_bank import seed_questions


def test_seed_questions_imports_answer_keys_and_mappings():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    questions, _, _ = generate_dataset(GeneratorConfig(students=1, questions=4, attempts=1))
    with Session(engine) as session:
        assert seed_questions(session, questions) == 4
        rows = session.scalars(select(Question).order_by(Question.question_id)).all()
        assert len(rows) == 4
        assert rows[0].correct_option in {"A", "B", "C", "D"}
        assert rows[0].error_mapping


def test_seed_questions_refuses_existing_question_bank_without_changes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    questions, _, _ = generate_dataset(GeneratorConfig(students=1, questions=2, attempts=1))
    with Session(engine) as session:
        seed_questions(session, questions)
        with pytest.raises(ValueError, match="refusing to append or replace"):
            seed_questions(session, questions)
        assert session.scalar(select(Question.question_id)) == 1
