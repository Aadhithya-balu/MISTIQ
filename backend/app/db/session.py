from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models import entities  # noqa: F401 - register model metadata

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("sqlite"):
        migrate_sqlite_schema(engine)


def migrate_sqlite_schema(database_engine) -> None:
    """Apply additive/rename migrations from the original Phase 0 SQLite schema."""
    renames = {
        "questions": (("id", "question_id"),),
        "attempts": (("id", "attempt_id"),),
        "mistake_events": (("id", "mistake_event_id"),),
    }
    with database_engine.begin() as connection:
        inspector = inspect(connection)
        for table, pairs in renames.items():
            if table not in inspector.get_table_names():
                continue
            present = {column["name"] for column in inspector.get_columns(table)}
            for old, new in pairs:
                if old in present and new not in present:
                    connection.execute(text(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}"'))
                    present.remove(old); present.add(new)
        additive = {
            "questions": {"error_mapping": "JSON NOT NULL DEFAULT '{}'"},
            "attempts": {"idempotency_key": "VARCHAR(100)"},
            "learner_states": {
                "attempt_count": "INTEGER NOT NULL DEFAULT 0",
                "relevant_mistake_count": "INTEGER NOT NULL DEFAULT 0",
            },
            "predictions": {
                "data_reliability": "FLOAT NOT NULL DEFAULT 0",
                "status": "VARCHAR(40) NOT NULL DEFAULT 'NORMAL_OPERATION'",
                "model_name": "VARCHAR(100) NOT NULL DEFAULT 'MISTIQ-AMPA'",
                "model_version": "VARCHAR(40) NOT NULL DEFAULT '1.0'",
                "context_question_id": "INTEGER REFERENCES questions(question_id)",
                "source_attempt_id": "INTEGER REFERENCES attempts(attempt_id)",
                "explanation": "JSON",
            },
            "recommendations": {
                "prediction_id": "INTEGER REFERENCES predictions(id)",
                "question_id": "INTEGER REFERENCES questions(question_id)",
                "score": "FLOAT",
                "score_components": "JSON",
                "completed_at": "DATETIME",
            },
        }
        for table, columns in additive.items():
            if table not in inspect(connection).get_table_names():
                continue
            present = {column["name"] for column in inspect(connection).get_columns(table)}
            for column, ddl in columns.items():
                if column not in present:
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {ddl}'))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_attempt_idempotency_key ON attempts(idempotency_key)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_mistake_attempt ON mistake_events(attempt_id)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_prediction_source_attempt ON predictions(source_attempt_id)"))
        _fix_questions_difficulty_type(connection, database_engine)


def _fix_questions_difficulty_type(connection, database_engine) -> None:
    """Phase 0 stored difficulty as VARCHAR(50) text; rebuild the column as INTEGER.

    Creates a new table, copies the data, then swaps it in. Unlike RENAME, this
    never rewrites the foreign keys of dependent tables, since the canonical
    ``questions`` name is recreated in place.
    """
    inspector = inspect(connection)
    if "questions" not in inspector.get_table_names():
        return
    present = {column["name"]: column for column in inspector.get_columns("questions")}
    if "difficulty" not in present or "VARCHAR" not in str(present["difficulty"]["type"]).upper():
        return
    connection.execute(text("PRAGMA foreign_keys=OFF"))
    try:
        connection.execute(text("""
            CREATE TABLE "_questions_new" (
                question_id INTEGER NOT NULL PRIMARY KEY,
                topic VARCHAR(200) NOT NULL,
                subtopic VARCHAR(200),
                difficulty INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option VARCHAR(1) NOT NULL,
                estimated_time INTEGER NOT NULL,
                error_mapping JSON NOT NULL,
                CONSTRAINT ck_questions_difficulty CHECK (difficulty BETWEEN 1 AND 5),
                CONSTRAINT ck_questions_estimated_time CHECK (estimated_time > 0)
            )
        """))
        connection.execute(text("""
            INSERT INTO "_questions_new" (question_id, topic, subtopic, difficulty, question_text,
                                          option_a, option_b, option_c, option_d, correct_option,
                                          estimated_time, error_mapping)
            SELECT question_id, topic, subtopic, CAST(difficulty AS INTEGER), question_text,
                   option_a, option_b, option_c, option_d, correct_option,
                   estimated_time, error_mapping
            FROM questions
        """))
        connection.execute(text('DROP TABLE "questions"'))
        connection.execute(text('ALTER TABLE "_questions_new" RENAME TO "questions"'))
    finally:
        connection.execute(text("PRAGMA foreign_keys=ON"))
