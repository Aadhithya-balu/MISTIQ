# MISTIQ demonstration guide

## Run the reproducible end-to-end flow

From the repository root with the pinned dependencies installed and the trained artifact available:

```powershell
python scripts/demo.py
```

The script creates eight clearly identified synthetic question rows in an in-memory SQLite database, loads the same saved AMPA artifact as the application, and sends requests through the actual FastAPI routes and application services. The database disappears when the script exits; no student or attempt data is added to the developer's persistent database. No prediction, recommendation, feature, or metric is hardcoded. An artifact must already exist; the demo stops clearly if it is missing.

The script verifies and reports:

1. Backend health, saved model version, and question loading.
2. Student creation and five persisted attempts with correctness determined by the question answer key.
3. Three recorded mistakes, learner-state updates, an actual AMPA prediction, and its contribution explanation.
4. A question ranked and persisted by the recommendation service.
5. Practice on that recommended question, automatic completion of its recommendation, and updated attempt/mistake analytics.
6. A new stored prediction with a reproducible research trace and available Phase 4 evaluation outputs.

IDs in the printed report are local to its temporary database and cannot be reconnected to after the process exits.

## Interactive student workflow

The isolated script is the reproducible acceptance demo. To click through the browser UI, first provide a development SQLite database with question rows. The frontend intentionally has no bundled hidden or sample student data. Set `DATABASE_URL` for the backend process and arrange a question bank using your development-only seed process, then start FastAPI from `backend/` and Vite from `frontend/`. Open the Vite URL, create a local development profile, and visit Dashboard, Practice, Progress, Mistakes, and Profile. A fresh empty database cannot offer Practice questions until questions are added.

The profile flow is not authentication. Use synthetic/demo records only. To prepare a disposable browser demo database, first generate the documented synthetic CSVs from the repository root, then seed an empty database and start the backend from `backend/`:

```powershell
python -m backend.ml.datasets.synthetic_generator --seed 42
cd backend
$env:DATABASE_URL = "sqlite:///./demo.db"
python ..\scripts\seed_question_bank.py
python -m uvicorn app.main:app --reload
```

In another terminal, run Vite from `frontend/`. The seed command refuses to append to or replace an existing question bank. With seed 42, the browser script's first question has A as its correct answer. The existing browser script `scripts/browser_ui_e2e.mjs` drives the student pages with a local CDP-enabled browser and appends learner/attempt rows to the configured disposable database. After the demo, stop the backend and remove only `backend/demo.db` to reset it. The isolated `scripts/demo.py` flow resets itself automatically.

## Research demonstration

1. Open Research from the secondary navigation.
2. Review model version/status, the implemented pipeline, and feature definitions.
3. Open Formula Explorer, enter a student ID from the backend database used by the interactive app, load predictions, and inspect a trace. The standalone in-memory demo prints its own trace and discards its database on exit, so its student ID is intentionally not available to the browser afterward.
4. Inspect feature snapshot, learned weights/bias, class score contributions, raw/shifted logits, softmax probabilities, and the stored/replayed comparison.
5. Open Evaluation to inspect actual comparison, ablation, calibration, confusion matrix, seed robustness, learning-curve, and cold-start files. Missing artifacts are labeled unavailable; no metrics are filled in by the UI.

## Interpretation

Probability, confidence, and data reliability are distinct. The cold-start policy withholds a predicted class for students with fewer than five attempts. Experiment results use synthetic data and do not establish educational efficacy. MISTIQ-AMPA is a project-specific custom sequential mistake-prediction framework, not a claimed universal new ML paradigm. Research endpoints and the development student profile do not have role-based authorization; do not demonstrate using real student data.
