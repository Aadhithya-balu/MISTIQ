# MISTIQ Backend and AMPA Integration

## Scope

The backend connects the existing AMPA implementation to persisted student interactions. It does not perform online weight training or replace the ML model. Later phases add history-grounded recommendations, progress/mistake analytics, and the read-only Research API.

## Architecture

```text
Client
  │
  ▼
FastAPI routes ── Pydantic request/response schemas
  │
  ├── SQLAlchemy session ── Student / Question / Attempt / MistakeEvent
  │                       └─ LearnerState / Prediction / Recommendation
  ▼
Attempt integration service
  ├── correctness from stored Question
  ├── contextual mistake classification
  ├── update AMPA student history and Phase 2 feature state
  ├── AMPA prediction + model explanation
  └── commit interaction and derived records together
```

## Request and persistence flow

1. Create a student with `POST /api/students`.
2. Read questions with `GET /api/questions` or `GET /api/questions/{question_id}`. Public question responses omit the answer key and distractor mapping.
3. Submit `student_id`, `question_id`, `selected_option`, and `response_time` to `POST /api/attempts`. A client-supplied `correct` field is rejected.
4. The service loads the stored question, determines correctness, allocates an attempt number, and creates a mistake event for incorrect answers. Distractor mapping, timing, difficulty, and previous matching mistakes contribute to classification.
5. AMPA receives the current interaction and uses its student history to create context-sensitive class feature rows. The history is updated before predicting, so the result describes the learner's next mistake risk given the just-submitted interaction; no later interaction is available.
6. The learner state and, when AMPA returns a reliable prediction, the prediction and explanation are persisted with the attempt. Database failure rolls back and removes the staged interaction from in-memory student history.

An optional `idempotency_key` makes a retry with the same payload return the existing attempt; reusing it with a different payload is rejected.

## AMPA lifecycle and cold start

At application startup, AMPA loads the artifact at `MISTIQ_AMPA_MODEL_PATH` (default: `backend/ml/artifacts/ampa.npz`) once and hydrates per-student interaction history from the database. The artifact carries learned weights and bias, normalization values, class labels, configuration, and model version. The API does not fit or modify global weights during an attempt.

If the artifact is absent or invalid, health can still report database readiness, while prediction-dependent attempt submission and prediction routes return a clear `503 model_unavailable`. No synthetic prediction is substituted.

Cold-start thresholds are read from the loaded AMPA model configuration: 0–4 attempts return `NO_RELIABLE_PREDICTION` with no prediction row; 5–14 use `LOW_CONFIDENCE`; 15–29 use `MEDIUM_CONFIDENCE`; 30+ use `NORMAL_OPERATION`. Probability, confidence, and data reliability are returned as separate values from AMPA.

## Explanation and APIs

Explanation content comes from AMPA's contribution output and is stored with the prediction. The API exposes:

- `GET /health` and `GET /api/health`
- `POST /api/students`, `GET /api/students/{student_id}`, `GET /api/students/{student_id}/mistakes`
- `GET /api/questions`, `GET /api/questions/{question_id}`
- `POST /api/attempts`
- `GET /api/predictions/{student_id}`, `GET /api/predictions/{student_id}/latest`, `GET /api/predictions/{student_id}/latest/explanation`
- `GET /api/students/{student_id}/progress`, `GET /api/students/{student_id}/state`
- `GET /api/recommendations/{student_id}/next`, recommendation history/completion endpoints, mistake analytics endpoints, and the read-only `/api/research/*` routes are implemented in their later phase modules.

FastAPI OpenAPI documentation is available at `/docs`. Integration errors use stable error codes and do not return stack traces.

## Database and local run

The existing SQLite development database is used. Startup creates missing tables and applies additive/column-rename migrations for the original Phase 0 SQLite schema. Foreign keys are enabled for SQLite connections.

Run from the `backend/` directory so the default relative database URL resolves to `backend/mistiq.db`:

```powershell
python -m uvicorn app.main:app --reload
```

Train or refresh an artifact explicitly from the existing synthetic dataset before startup when needed:

```powershell
python -m scripts.train_ampa_artifact --seed 42
```

Training is an offline operation; requests only load and use the saved artifact.

## Validation

Run all tests from the repository root with `python -m pytest -q`. The integration test uses the real saved AMPA artifact and an isolated SQLite database to check cold start, mistakes, features/state persistence, explanation persistence, idempotency, and that model weights remain unchanged across requests.
