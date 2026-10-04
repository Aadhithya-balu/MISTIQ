"""Seed a disposable MISTIQ database from the validated synthetic question CSV."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, migrate_sqlite_schema
from app.models import Question
from ml.datasets.loader import load_dataset


def seed_questions(session: Session, questions: list[dict]) -> int:
    existing = session.scalar(select(func.count(Question.question_id))) or 0
    if existing:
        raise ValueError(
            f"Question bank already contains {existing} rows; refusing to append or replace data. "
            "Use a new disposable SQLite database for the demo."
        )
    session.add_all([
        Question(
            question_id=int(row["question_id"]), topic=row["topic"], subtopic=row.get("subtopic") or None,
            difficulty=int(row["difficulty"]), question_text=row["question_text"],
            option_a=row["option_a"], option_b=row["option_b"],
            option_c=row["option_c"], option_d=row["option_d"],
            correct_option=row["correct_option"], estimated_time=int(row["estimated_time"]),
            error_mapping=json.loads(row["error_mapping"]),
        )
        for row in questions
    ])
    session.commit()
    return len(questions)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "synthetic")
    args = parser.parse_args(argv)
    questions, _, _ = load_dataset(args.dataset)
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        migrate_sqlite_schema(engine)
    with Session(engine) as session:
        count = seed_questions(session, questions)
    print(f"Seeded {count} synthetic questions into {engine.url.database or 'the configured database'}.")


if __name__ == "__main__":
    main()
