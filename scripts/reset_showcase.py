"""Reset only the dedicated local synthetic showcase database."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE_DIR = (ROOT / "data" / "showcase").resolve()
DATABASE = (SHOWCASE_DIR / "showcase.db").resolve()


def reset_showcase() -> None:
    if DATABASE.parent != SHOWCASE_DIR or DATABASE.name != "showcase.db":
        raise RuntimeError("Refusing to reset a database outside data/showcase/showcase.db")
    for path in (DATABASE, Path(f"{DATABASE}-wal"), Path(f"{DATABASE}-shm")):
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    reset_showcase()
    print(f"Reset dedicated showcase database: {DATABASE}")
