#!/usr/bin/env python
"""Reset only the demo student data in the normal local database."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal
from app.services.showcase_service import reset_demo_student
from app.main import create_app


def reset_showcase() -> None:
    app = create_app()
    with app.state.SessionLocal() as session:
        reset_demo_student(session)


if __name__ == "__main__":
    reset_showcase()
    print("Reset demo student in the local application database.")

