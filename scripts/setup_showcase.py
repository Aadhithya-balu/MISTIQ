#!/usr/bin/env python
"""Create a deterministic synthetic showcase in the normal local database."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.base import Base
from app.db.session import engine, migrate_sqlite_schema
from app.main import create_app
from app.services.ampa_service import AMPAService
from app.services.showcase_service import setup_showcase_in_normal_db


ARTIFACT = ROOT / "backend" / "ml" / "artifacts" / "ampa.npz"


def setup_showcase() -> dict:
    if not ARTIFACT.is_file():
        raise FileNotFoundError(f"Trained local AMPA artifact not found: {ARTIFACT}")
    service = AMPAService(ARTIFACT)
    service.load_once()
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema(engine)
    app = create_app(database_engine=engine, ampa_service=service)
    result = setup_showcase_in_normal_db(engine, service)
    return result


if __name__ == "__main__":
    report = setup_showcase()
    print(json.dumps(report, indent=2))