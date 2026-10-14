# MISTIQ 2.0 — Full Project Description

**MISTIQ** stands for **Mistake Intelligence & Sequential Prediction**. It is a student-practice web
platform backed by a custom, sequential mistake-category model called **MISTIQ-AMPA**
(**Adaptive Mistake Propagation Algorithm**). Given a learner's recorded attempts and mistake
events, MISTIQ-AMPA estimates the *next mistake category* the learner is likely to make. Adaptive
practice, explanations, progress views, mistake summaries, and recommendations are all driven by
real application data — never by hardcoded or sample values.

> **Research question:** *Can the trajectory of a student's mistakes predict their next conceptual
> failure better than their overall accuracy?*

> **Honesty note (repeated throughout the project):** MISTIQ-AMPA is a project-specific, custom
> sequential mistake-prediction framework designed for this project. It is not claimed to be a newly
> invented universal machine-learning paradigm, and it is not a psychological or causal model.

---

## Table of Contents

1. [High-Level Overview](#1-high-level-overview)
2. [Repository Structure & Tech Stack](#2-repository-structure--tech-stack)
3. [The Model: MISTIQ-AMPA](#3-the-model-mistiq-ampa)
4. [Data Foundation](#4-data-foundation)
5. [Backend: Architecture, Pipeline & API](#5-backend-architecture-pipeline--api)
6. [Frontend: UI & Design System](#6-frontend-ui--design-system)
7. [Frontend: All Pages](#7-frontend-all-pages)
8. [UX Flows](#8-ux-flows)
9. [Evaluation & Measured Results](#9-evaluation--measured-results)
10. [Limitations & Academic Honesty](#10-limitations--academic-honesty)
11. [Setup & How to Run](#11-setup--how-to-run)

---

## 1. High-Level Overview

MISTIQ turns the *sequence* of a learner's mistakes into a usable signal. Instead of only tracking
overall accuracy, it stores the full chain:

```
Student  ->  Question  ->  Attempt  ->  Mistake Event
```

From that history it derives **eight temporal features**, applies saved AMPA global parameters to
score **seven candidate mistake categories**, and produces:

- a **next-mistake prediction** (with probability, confidence, and data reliability),
- a **plain-language explanation** of *why* that prediction was made,
- a **recommended practice question**,
- **progress analytics** (accuracy trend, per-topic/difficulty performance, recovery, stability),
- **mistake analytics** (common mistakes, repeated patterns, concept-confusion pairs, activity timeline).

The project deliberately separates **offline training/evaluation** from **online inference**:
requests load a saved model artifact and never retrain or modify global weights.

**Components included:**

- A **React 18 + TypeScript** student application and a technical Research Lab.
- A **FastAPI + SQLAlchemy 2 + SQLite** backend.
- The **explicit NumPy implementation** of the AMPA model (no wrapped classifier library).
- **scikit-learn comparison baselines** (Logistic Regression, Decision Tree, Random Forest, KNN, Majority).
- **Synthetic interaction data** generation.
- A **temporal evaluation pipeline** producing comparison, ablation, calibration, confusion, seed-robustness, and learning-curve artifacts.

---

## 2. Repository Structure & Tech Stack

### Structure

```
MISTIQ/
├── backend/
│   ├── app/            FastAPI app: api/, core/, db/, models/, schemas/, services/
│   ├── ml/             AMPA model, datasets, baselines, evaluation
│   ├── artifacts/      ampa.npz (trained weights + normalization + metadata)
│   ├── tests/          ML tests
│   ├── requirements.txt
│   └── mistiq.db       SQLite database (canonical)
├── frontend/
│   └── src/            React app: api/, components/, context/, layouts/, pages/, styles/, test/, types/
├── data/synthetic/     questions.csv, attempts.csv, mistake_events.csv (generated; git-ignored)
├── experiments/        reports/, ablations/, calibration/, confusion_matrices/, learning_curves/, results/
├── scripts/            train_ampa_artifact.py, setup_showcase.py, seed_question_bank.py, reset_showcase.py, demo.py
├── tests/              unit/ + integration/ (pytest)
├── docs/               architecture, methods, research, and demo guides
└── package.json        root orchestration (concurrently)
```

### Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ (tested on 3.14), FastAPI 0.135, Pydantic 2, SQLAlchemy 2, NumPy, scikit-learn |
| Frontend | React 18, TypeScript 5, Vite 5, React Router 6, Vitest 2 |
| Database | SQLite (default local file) |
| Data | Generated synthetic CSVs (deterministic, seeded) |

There is **no CORS middleware, no static-file serving, and no auth layer** in the Python backend.
The frontend dev server proxies `/api` to `http://127.0.0.1:8000`.

---

## 3. The Model: MISTIQ-AMPA

### 3.1 What it is

**MISTIQ-AMPA** is a softmax (multiclass logistic) classifier augmented with **temporal memory** and
**per-student state**. It is implemented directly in NumPy with explicit equations and trained
offline. It predicts the next **mistake category**, not raw correctness.

**Target classes (7, `CORRECT` excluded):**
`CONCEPT_CONFUSION`, `CALCULATION_ERROR`, `PROCEDURE_ERROR`, `CARELESS_ERROR`, `TIME_PRESSURE`,
`DIFFICULTY_FAILURE`, `REPEATED_MISTAKE`.

### 3.2 Input features (8)

For each candidate error class `e`, a class-specific feature row is built using only events strictly
before the prediction time `as_of`:

```
X_e = [ F_e, R_e, A_e, D_e, B_e, C_e, 1 - S_e, MM_e ]
```

| Symbol | Feature | Meaning |
|---|---|---|
| `F` | mistake_frequency | Class frequency blended with memory |
| `R` | mistake_recency | Exponential recency weighting `exp(-lambda * age_days)` |
| `A` | repetition_score | `1 + alpha * log(1 + N)` amplification by repetition |
| `D` | difficulty_sensitivity | Hard-vs-easy error rate difference scaled by candidate difficulty |
| `B` | behavior_pressure | Bounded `|log(latest_time / prior_median)| / log(4)` |
| `C` | concept_confusion | Topic-scoped fraction of confusions for a configured concept pair |
| `S` | learning_stability | `accuracy * (1 - min(1, 2*sqrt(accuracy*(1-accuracy))))` |
| `MM` | mistake_momentum | Signed momentum `tanh((recent_mean - previous_mean) / scale)` |

Stability is **protective**, so it is transformed to **instability `1 - S`** before fitting and
inference (`RISK_FEATURE_NAMES`).

### 3.3 Scoring and probabilities

```
Z_e = b_e + sum_j W[e,j] * X[e,j]
P(e) = exp(Z_e - max(Z)) / sum_k exp(Z_k - max(Z))
```

The max-subtraction in the softmax keeps exponentials numerically stable.

### 3.4 Training

- Multiclass **cross-entropy** loss with **L2 weight regularization** (`lambda_reg`), optimized by
  **full-batch gradient descent**.
- Gradients (analytical; biases are not regularized):
  ```
  delta       = P - one_hot(y)
  Grad_W      = X^T delta / N + 2 * lambda_reg * W
  Grad_b      = mean(delta)
  W := W - learning_rate * Grad_W
  b := b - learning_rate * Grad_b
  ```
- Normalization (feature mean/scale) is fit **on the training rows only**; zero-variance features
  use scale 1.
- `fit_interactions(...)` builds examples **chronologically** from strictly prior same-student
  events (leakage-safe), then appends the target. `CORRECT` outcomes are excluded from the target set.
- A numerical gradient checker (`numerical_gradient`, central finite differences) validates the
  analytical gradients. Divergence during training raises a `FloatingPointError`.

**Default hyperparameters:** `learning_rate=0.05`, `epochs=300`, `regularization=0.01`, `seed=42`,
`decay_rate=0.08`, `repetition_alpha=0.5`, `memory_scale=3.0`, `momentum_window=5`,
`momentum_scale=0.25`. Weights are initialized `N(0, 0.01)` elsewhere `(7 x 8)`, bias zeros.
Training metadata for the committed artifact: **1059 examples, 300 epochs, seed 42**, version `1.0`.

### 3.5 Confidence, reliability & cold start

Two separate quantities are reported (never conflated):

- **Probability** — the softmax output for the winning class.
- **Data reliability** — a **history-grounded** score combining volume, topic relevance, concept
  coverage, and outcome consistency:
  ```
  reliability = volume * sqrt(relevance) * (0.5 + 0.5*coverage) * (0.5 + 0.5*consistency)
  volume      = min(1, attempts / 30)
  ```
- **Confidence = probability x reliability.**

**Reliability tiers** (configurable defaults):

| Status | Attempt count |
|---|---|
| `NO_RELIABLE_PREDICTION` | 0–4 (model **abstains** — no class presented) |
| `LOW_CONFIDENCE` | 5–14 |
| `MEDIUM_CONFIDENCE` | 15–29 |
| `NORMAL_OPERATION` | 30+ |

Under `NO_RELIABLE_PREDICTION` the model returns **no predicted class** rather than a low-quality
guess. The model's top-class probability is *not* presumed calibrated; expected calibration error
(ECE) is measured and reported rather than assumed.

### 3.6 Online vs offline separation

- **Online (per request):** `update(interaction)` appends an ordered outcome to per-student history
  and **does not retrain global `W`/`b`**. The API loads the saved artifact once at startup.
- **Offline (scripts / ML package):** baselines and evaluation live under `backend/ml/` and
  `experiments/`; they never run during a student request.

The saved artifact `ampa.npz` stores only **global parameters, normalization, config, classes, and
metadata** — never per-student state. It is version- and class-validated on load.

### 3.7 Key model modules

| File | Responsibility |
|---|---|
| `backend/ml/ampa/model.py` | `MISTIQAMPA`: fit/predict/explain/update/save/load, `predict_for_student` |
| `features.py` | 8 feature names, 7 classes, concept pairs, `class_feature_matrix`, stability helpers |
| `memory.py` | Recency weight, repetition amplification, bounded mistake memory |
| `momentum.py` | Signed `risk_momentum` with a low-information guard |
| `risk.py` | `class_risk` (Z), stable softmax, cross-entropy, stability→instability |
| `optimizer.py` | Analytical + numerical gradients, `train_parameters` |
| `state.py` | `StudentStateStore` (per-student ordered histories, rollback support) |
| `explainer.py` | Per-feature contribution ranking for the winning class |
| `prediction.py` | Confidence tiers, data reliability, `prediction_result` (abstention) |

---

## 4. Data Foundation

### 4.1 Synthetic dataset

All question content and interactions are **synthetic** and honestly labeled; they are for pipeline
development and do not represent real student records.

Default size: **100 students, 500 questions, 10,000 attempts** (plus a linked mistake event per
attempt). Generated deterministically with `--seed 42`.

**Files (`data/synthetic/`):**

| File | Contents |
|---|---|
| `questions.csv` | Content, topic/subtopic, difficulty 1–5, options A–D, correct option, per-distractor `error_mapping` |
| `attempts.csv` | Selected option, correctness, response time, timestamp, per-question attempt number |
| `mistake_events.csv` | One linked event per attempt, including `CORRECT` events and categorized mistakes |

Validation (`backend/ml/datasets/schema.py`): required fields, ID uniqueness, difficulty/error
category checks, response-time bounds (`1.0–900.0`), referential integrity, correctness consistency,
and per-student chronology. Reusing a seed and config reproduces identical rows.

### 4.2 Mistake structure (post-fix)

The generator was redesigned so mistakes are **autocorrelated**, not independent noise:

- Each `(student, topic)` carries a **persistent misconception category**, repeated on a wrong
  answer with probability **~0.68–0.86** (higher for repetitive/confused profiles).
- A deterministic per-topic **secondary distractor** (`CALCULATION_ERROR` / `PROCEDURE_ERROR`)
  generalizes across a topic.
- Time/difficulty/repeat overrides **mirror the live classifier**: `response_time >= 1.5 x estimate`
  → `TIME_PRESSURE`; `difficulty >= 4` and over estimate → `DIFFICULTY_FAILURE`; a repeated
  distractor → `REPEATED_MISTAKE`.
- Result: `P(next = previous | same topic)` rose from **0.234 to 0.614**, and predictable
  misconception classes now make up ~86% of mistakes.

This is a **genuine data-structure change**, not metric-gaming (see [Section 9](#9-evaluation--measured-results)).

---

## 5. Backend: Architecture, Pipeline & API

### 5.1 Application

- `backend/app/main.py` builds the app via `create_app(...)`, enables SQLite foreign keys, runs a
  `lifespan` that creates tables, applies compatibility migrations, constructs the `AMPAService`,
  loads the artifact once, and **hydrates** in-memory state by replaying stored attempts.
- If the model fails to load, the service is marked unavailable, DB health still works, but
  prediction routes return **503**.
- Routers are mounted under **`/api`**; `GET /health` is also available at the root.
- A global `IntegrationError` handler returns `{"error", "detail"}` — **never stack traces**.

### 5.2 Domain model (SQLite)

| Table | Key columns |
|---|---|
| `students` | id, name, created_at |
| `questions` | question_id, topic, subtopic, difficulty (1–5), question_text, options A–D, correct_option, estimated_time, error_mapping (JSON) |
| `attempts` | attempt_id, student_id, question_id, selected_option, correct, response_time, timestamp, attempt_number, idempotency_key (unique) |
| `mistake_events` | mistake_event_id, student_id, attempt_id (unique), error_type, topic, subtopic, timestamp |
| `learner_states` | id, student_id (unique), attempt_count, relevant_mistake_count, 8 feature columns, updated_at |
| `predictions` | id, student_id, predicted_error, probability, confidence, data_reliability, status, model_name/version, context_question_id, source_attempt_id (unique), explanation (JSON) |
| `recommendations` | id, student_id, prediction_id, type, reason, question_id, score, score_components (JSON), completed_at, created_at |

Additive compatibility migrations rename legacy columns, add newer columns, and create unique
indexes for idempotency.

### 5.3 Attempt pipeline

When a student submits an attempt:

1. **Idempotency** — same key + same payload returns the existing attempt; same key + different
   payload → 422.
2. **Validation** — student/question exist; option in A–D; response time in `(0, 900]`.
3. **Attempt creation** — `attempt_number` = count of prior attempts on the same question.
4. **Mistake classification** (incorrect only) — reads `question.error_mapping`, then may override to
   `TIME_PRESSURE`, `DIFFICULTY_FAILURE`, or `REPEATED_MISTAKE` per the rules above.
5. **History update** — the model appends the interaction to per-student history *before* predicting
   (context-aware, strictly prior events only).
6. **Feature extraction & state persistence** — 7-class × 8-feature matrix; `LearnerState` stores
   **max** for frequency/recency/repetition/behavior_pressure/concept_confusion and **mean** for
   difficulty_sensitivity/stability/momentum.
7. **Prediction & explanation** — a `Prediction` row plus a plain-language explanation and a
   **research trace snapshot** are stored atomically with the attempt.
8. **Rollback safety** — on any exception the transaction rolls back and the staged history entry is
   discarded.

### 5.4 API endpoints (all under `/api` unless noted)

**Students / mistakes**
- `POST /api/students` → 201 Student · `GET /api/students` · `GET /api/students/{id}`
- `GET /api/students/{id}/mistakes`
- `GET /api/mistakes/{id}`, `/summary`, `/repeated`, `/confusions`

**Questions**
- `GET /api/questions?topic=&subtopic=&difficulty=` · `GET /api/questions/{id}` (answer key hidden)

**Attempts**
- `POST /api/attempts` → 201 `AttemptSubmission` (attempt, mistake_event, prediction,
  prediction_status, correct_option, correct_answer)

**Predictions**
- `GET /api/predictions/{id}`, `/latest`, `/latest/explanation`

**Recommendations**
- `GET /api/recommendations/{id}`, `/next` · `POST /api/recommendations/{id}/complete`

**Progress**
- `GET /api/progress/{id}` and `/api/students/{id}/progress`, `GET /api/students/{id}/state`

**Showcase** (`/api/showcase`) — `status`, `reset`, `seed`

**Research** (`/api/research`, read-only) — `database/inspection`, `students/{id}/predictions`,
`model`, `model/features`, `model/parameters`, `prediction/{id}/trace`, `evaluation`,
`evaluation/ablations`, `evaluation/calibration`, `evaluation/confusion-matrix`,
`evaluation/seeds`, `evaluation/learning-curves`, `evaluation/cold-start`

**Health** — `GET /health`, `GET /api/health`

### 5.5 Services

- **`ampa_service`** — loads/hydrates the model, runs the attempt pipeline, persists explanations and
  trace snapshots, and supports exact replay.
- **`recommendation_service`** — ranks candidate questions by a weighted, history-grounded score:
  `learning_need 0.35`, `mistake_relevance 0.25`, `difficulty_fit 0.20`, `novelty 0.10`,
  `retention_value 0.10`. Cold-start recommendations are also ranked (not a stub) and flagged
  `cold_start`. This "score" is a reproducible **selection** score, explicitly not a model prediction.
- **`progress_service` / analytics services** — totals, accuracy, streaks, per-topic/subtopic/
  difficulty performance, recent-vs-previous trend, recovery after mistakes, stability & momentum,
  prefix-only trajectory.
- **`mistake_analytics_service`** — distribution, repeated patterns, concept-confusion pairs,
  weekly/daily timeline, trends.
- **`research_service`** — exposes model metadata, prediction traces (replayed and verified
  `EXACT`/`APPROXIMATE`/`MISMATCH`), and reads evaluation artifacts (reporting `available: false`
  rather than inventing data).
- **`showcase_service`** — a curated demo: `DEMO_STUDENT_ID = 1`, 14 curated questions, a fixed
  16-attempt sequence ending in a `CONCEPT_CONFUSION` on a Recall question, leaving a Precision
  question unattempted. Expected result: 16 attempts, 5 mistakes, prediction `CONCEPT_CONFUSION`
  (`MEDIUM_CONFIDENCE`), recommended question 507.

### 5.6 Prediction trace & explainability

Each new prediction stores a full `research_trace_snapshot`: raw per-class features, normalized and
instability-transformed features, learned weights, bias, normalization, config, raw/shifted scores,
exponentials, and probabilities. The Research Lab replays this snapshot to produce a **bit-for-bit**
trace (`replay_matches_stored == true`). Older predictions without a snapshot are marked
`APPROXIMATE`.

---

## 6. Frontend: UI & Design System

### 6.1 Stack & entry

- React 18 + TypeScript 5 + Vite 5 + React Router 6; tests with Vitest.
- `index.html`: title **MISTIQ 2.0**, theme-color `#386b58`, inline SVG "M" favicon, **DM Sans**
  font from Google Fonts.
- `/api` is proxied to the backend in development (`VITE_API_URL=/api`).
- Charts are **hand-built inline SVG**; icons are plain Unicode glyphs. No icon or chart library.

### 6.2 Visual identity

A calm, editorial "learning notebook" aesthetic: off-white background, forest-green primary, mint
highlights, muted grey text, and coral accents for errors. Rounded 8–13px corners, hairline borders,
very soft shadows, uppercase letter-spaced kickers, tight negative letter-spacing on headings, and
generous whitespace. The `✳` mark recurs as a decorative motif.

**Design tokens (`:root`):**

| Token | Value | Use |
|---|---|---|
| `--ink` | `#202c32` | Primary text |
| `--muted` | `#748087` | Secondary text |
| `--line` | `#e5e9e5` | Hairline borders |
| `--paper` | `#fff` | Card background |
| `--primary` | `#386b58` | Forest-green brand |
| `--primary-dark` | `#2e5949` | Hover/active |
| `--mint` | `#eaf2ed` | Soft highlight |
| `--coral` | `#b86956` | Error accent |
| `--soft-coral` | `#fbefeb` | Error background |
| `--gold` | `#9b7840` | Warning accent |
| `--shadow` | `0 9px 24px rgba(34,52,44,.035)` | Card shadow |

### 6.3 Layout & responsiveness

- Fixed **244px sidebar** on desktop; content constrained to 1280px with fluid padding.
- Dashboard: two-column grid (`1.05fr .95fr`); the model-quality card spans the full width.
- Practice / Mistakes: main column + narrow aside.
- **Breakpoints:** `1050px` (tighter padding), `760px` (mobile: static top bar, bottom nav,
  single-column layouts, asides hidden, learn-steps single column), `560px` (research facts 2-up),
  `420px` (stacked actions, tighter padding).
- Accessibility: visible focus rings, `role="status"` / `role="alert"`, `aria-label`s on charts and
  bars, `sr-only` legends, and `prefers-reduced-motion` support.

### 6.4 Reusable components & state

- UI primitives: `Button`, `Card`, `PageHeader`, `LoadingState`, `EmptyState`, `ErrorState`.
- `StudentContext` — the session provider: `student`, `ready`, `restoreError`, `enter(name)`,
  `reconnect(id)`, `leave()`. There is **no persistence** (no `localStorage`): a browser refresh
  returns to sign-in. "Sign-in" means creating/reconnecting a **local profile** — there is no
  authentication token or credential.
- API layer (`src/api/`): `client.ts` (base URL, `ApiError`, centralized request/error mapping),
  plus `students.ts`, `questions.ts`, `attempts.ts`, `predictions.ts`, `recommendations.ts`,
  `research.ts`, `showcase.ts`.

### 6.5 Error handling in the UI

- Network failure → *"MISTIQ could not reach the learning service. Check that the backend is running."*
- **409** → honest *"Keep practicing. MISTIQ needs more interaction history before it can identify
  reliable patterns."*
- **503** → *"The learning prediction service is not ready yet. Your practice can continue when it is
  available."*
- Raw stack traces are never displayed.

---

## 7. Frontend: All Pages

The app has one public page (`/login`) and the rest are protected by `AppLayout`, which redirects
unauthenticated visitors to `/login` while remembering the attempted URL (`state.from`).

### 7.1 Login — `/login` (public)

- **Hero:** eyebrow *"Mistake Intelligence & Sequential Prediction"*; H1 *"Learn from how mistakes
  change over time."*; explanatory paragraph; a note that **every number shown is computed from the
  student's own recorded practice, no sample data**.
- **Local profile card:** create a profile with a name (`POST /students`) or reconnect with a
  Student ID (`GET /students/{id}`). Explicit copy states data is stored in the local MISTIQ
  database with **no account, email, or sign-up required**.
- **"How it works" section (`#learn-more`):** H2 *"A loop that learns from each attempt."* with three
  steps — *Create a local profile*, *Practice and get checked*, *See what may come next*.
- On success, navigates to the remembered deep link or `/dashboard`.

### 7.2 Dashboard — `/dashboard`

Fetches progress, mistakes, the latest prediction, and the next recommendation concurrently (plus the
explanation and offline model-quality data). Sections:

- **Greeting:** *"Good to see you, {name}."* — *"Small steps add up. Pick up where you left off."*
- **Welcome card:** *"Make a little progress today."* with a **Start practicing** CTA.
- **Likely next challenge (PredictionCard):** shows the predicted category (or *"Keep practicing"* /
  *"No challenge identified yet"*), a status pill (*Normal operation* / *Early signal*), the model
  probability, confidence, and data reliability. A collapsible **"Why am I seeing this?"** explains
  the reasoning and lists other possible patterns.
- **Recommended practice (RecommendationCard):** the next suggested topic/subtopic, a reason,
  difficulty and time guide, and a **Try this question** deep link.
- **Model quality (ModelPerformanceCard):** states, in live percentages, the offline benchmark
  accuracy, macro-F1, expected calibration error, and the majority baseline — with an explicit note
  that it is *measured offline, not from live sessions*.
- **Your progress:** attempted count, accuracy, and things to review.
- **Recent learning:** the last few mistakes as a compact list, linking to the full review.

### 7.3 Practice — `/practice`

Accepts optional `?topic`, `?subtopic`, and `?question` deep links. Shows the topic, difficulty tag,
and `QUESTION NN · N sec guide`, then a question with four answer options (A–D). Submitting
(`POST /attempts` with elapsed response time and a UUID idempotency key) produces a feedback panel:

- **Correct** (`✓`) or **Not quite** (`↗`), with the correct answer revealed.
- A mistake explanation; a special **aha-card** for concept confusion (*"A pattern MISTIQ noticed"*)
  with a **Practice this concept** link.
- An optional *"A possible next challenge: …"* line when a reliable prediction exists.
- **Next question** cycles through the loaded set; the timer resets per question and the feedback
  panel is focusable for screen readers.

An aside reminds the learner: *"Practice, then reflect."*

### 7.4 Progress — `/progress`

Stat cards (questions attempted, overall accuracy, recent accuracy, current/best streak), a recent
trend comparison (*"{+/-}n percentage points"*), per-topic and per-subtopic performance bars, a
difficulty breakdown, an inline **accuracy/difficulty trajectory chart**, **recovery after mistakes**,
and **learning stability** + mistake-momentum status. Empty until the first attempts.

### 7.5 Mistakes — `/mistakes`

Shows **common mistakes** (counts, percentages, trends), **repeated patterns** (with *Practice this*
deep links), **concept confusions** (pairs like `Precision ↔ Recall`), a **mistake activity**
timeline (daily/weekly), and the **full recent-mistakes history**. Only patterns actually present in
the learner's recorded practice are shown.

### 7.6 Profile — `/profile`

A gentle snapshot of four learning signals (each explained as descriptive, not a label):

- **Concept confidence** — inverse of concept-confusion events.
- **Learning stability** — from correctness and outcome consistency.
- **Challenge handling** — inverse of difficulty-sensitivity patterns.
- **Practice rhythm** — inverse of recent mistake momentum.

A `409` (insufficient data) is treated as "no state yet", not an error.

### 7.7 Research Lab — `/research` and sub-routes

A technical, read-only laboratory with four tabs:

**Overview** — model metadata (name/version), the full name *"Adaptive Mistake Propagation
Algorithm"*, research facts (features/classes/training/evaluation), the 9-step pipeline
(*Student attempts → Mistake events → Mistake memory → Feature engineering → Risk representation →
AMPA scores → Stable softmax → Prediction and explanation → Recommendation*), and feature definitions.

**Database (`/research/showcase`)** — a live database inspector: demo-student status, **Seed demo
session** / **Reset demo history** actions, live row counts, and the latest live writes (attempt,
mistake, prediction) as **proof of a real database**.

**Formula Explorer (`/research/formula-explorer`)** — select a historical context (student →
prediction) and **trace the calculation**: implemented feature parameters, the feature snapshot
table (classes × features), learned weights and bias, per-class score contributions, and the stable
softmax steps (raw z, shifted, exp, probability).

**Evaluation (`/research/evaluation`)** — an experiment selector (comparison model, ablation,
calibration/confusion model, seed 42/123) driving **model comparison**, **ablation results**,
**calibration bars**, **confusion matrix**, **seed robustness**, **learning curves**, and
**cold-start** performance (including AMPA's abstention at ≤4 attempts).

---

## 8. UX Flows

1. **Login-first:** every session begins at `/login`. Creating or reconnecting a local profile is the
   only way in; protected URLs redirect there and are restored after sign-in. A refresh signs out
   (in-memory session).
2. **Practice loop:** pick a question (optionally from a deep link) → select an answer → submit →
   immediate, honest feedback with the correct answer and reasoning → next question.
3. **Dashboard overview:** a single glance at greeting, next challenge, recommendation, offline
   model quality, progress summary, and recent mistakes.
4. **Mistake review:** distribution, repeats, confusion pairs, and timeline drive *what to review*,
   with one-click practice deep links.
5. **Progress reflection:** trends, per-topic/difficulty performance, recovery, stability, and a
   trajectory chart.
6. **Profile snapshot:** four plain-language learning signals.
7. **Research exploration:** inspect the model, trace a real prediction through its formula, and
   review the offline evaluation — all grounded in saved artifacts, never fabricated.
8. **Sign-out:** the **Sign out** button (sidebar on desktop, header on mobile) clears the session
   and returns to sign-in, remembering where you were.

---

## 9. Evaluation & Measured Results

### 9.1 Methodology

- **Target:** the next **non-`CORRECT`** mistake category, with feature history **strictly preceding**
  the target timestamp (leakage-safe).
- **Split:** a single **chronological** holdout — no shuffling. Sizes: **train 1059 / validation 227 /
  test 228**.
- **Seeds:** checked-in artifacts use **42 and 123** (`epochs=100`).
- **Metrics:** accuracy, macro/weighted precision-recall-F1, log loss, top-2/top-3 accuracy,
  multiclass Brier, and expected calibration error (ECE).
- **Baselines:** Logistic Regression, Decision Tree, Random Forest, KNN, and Majority — each fit on
  the training rows only.
- **Caveat:** these are descriptive measurements on synthetic data, **not claims of educational
  effectiveness or model superiority**, and no significance testing or nested cross-validation is
  performed.

### 9.2 Final comparison (mean of seeds 42 & 123)

| Model | Macro F1 | Accuracy | Weighted F1 | Log Loss | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|
| KNN | 0.3356 | 0.5175 | 0.4919 | 171.5344 | 0.7446 | 0.1813 |
| Random Forest | 0.3137 | 0.4890 | 0.4622 | 68.0573 | 0.7455 | 0.1943 |
| **MISTIQ-AMPA** | **0.3126** | **0.5263** | **0.4732** | **1.4270** | **0.6388** | **0.0970** |
| Logistic Regression | 0.2973 | 0.5000 | 0.4548 | 1.4532 | 0.6546 | 0.0969 |
| Decision Tree | 0.2799 | 0.3925 | 0.3864 | 390.0403 | 1.1580 | 0.5602 |
| Majority | 0.0714 | 0.3333 | 0.1667 | 1.6995 | 0.7923 | 0.0132 |

**Headline:** AMPA reaches **~0.53 accuracy / ~0.31 macro-F1**, above the majority baseline (~0.33
accuracy), competitive with the best macro-F1 baseline (KNN ~0.34), and has the **lowest log loss of
all compared models (1.427)** and strong calibration (ECE ~0.097, essentially tied with Logistic
Regression; Majority's ECE is lower but it is a trivial predictor).

### 9.3 Additional AMPA metrics

- Macro precision 0.333, macro recall 0.321, top-2 accuracy ~0.667, top-3 accuracy ~0.825,
  Brier 0.639.
- **Seed robustness:** accuracy std 0, macro-F1 ±0.0002 — highly stable across the two seeds
  (top-3 0.825 shows the correct class is usually near the top even when not first).

### 9.4 Ablations (Δ macro-F1, seed 42)

Removing `mistake_frequency` (−0.006), `behavior_pressure` (−0.006), `learning_stability` (−0.006),
or `concept_confusion` (−0.004) **hurts** performance; removing `mistake_momentum` (+0.003) or
`mistake_recency` (+0.002) slightly helps.

### 9.5 Cold-start (seed 42)

- 0–4 attempts: abstains (`NO_RELIABLE_PREDICTION`), no scored samples.
- 15–29: 9 scored samples, accuracy 0.444, macro-F1 0.173.
- 30+: 219 scored samples, accuracy 0.530, macro-F1 0.315.

### 9.6 The M1/M2 investigation (context)

- **M1 — `TIME_PRESSURE` dead class:** enriched the data to ~5–8% of mistakes; it *still* scored
  precision/recall 0.00 while overall quality fell. **Rolled back** — the retrained artifact was
  byte-identical to the committed one. Making it predictable would require a model-structure change
  (per-class feature isolation), and inflating the corpus would be metric-gaming, so it was not done.
- **M2 — low raw quality:** probes (hyperparameter sweep, class weighting, prior correction) showed
  the ceiling was the **label distribution** — the generator made consecutive same-topic mistakes
  near-independent (`P(next = previous | same topic) ≈ 0.234`), so no model could beat it.
- **Resolution:** the generator redesign above raised that persistence to **0.614**, lifting AMPA from
  accuracy 0.263 → 0.526 and macro-F1 0.128 → 0.313. The reported figure remains a **synthetic-data**
  measurement.

---

## 10. Limitations & Academic Honesty

- **Synthetic data only.** Results do not establish performance with real learners; with real, less
  autocorrelated data, scores would be lower.
- **AMPA is project-specific.** Predictive and recommendation signals are **not** causal explanations
  or psychological assessments.
- **No authentication / role authorization.** The profile screen is not authentication; the research
  APIs are unauthenticated. Do not expose this project or its research APIs to real student data
  without an authorization layer.
- **No production hardening.** No privacy/deployment hardening; only SQLite compatibility migrations.
- **Calibration caveat.** Softmax probabilities are not presumed calibrated; ECE is measured, not
  assumed. AMPA's "best calibration" claim holds only as *best non-trivial / learned* model and is
  essentially tied with Logistic Regression — AMPA is unambiguously best on **log loss**.
- **Trace snapshots.** Older stored predictions (pre-Phase 9) may lack exact formula snapshots and
  are replayed as `APPROXIMATE`.
- **Analytics are descriptive.** Progress/mistake signals are not psychological or causal; concept
  pairs inferred from option text can split equivalent concepts.
- **`TIME_PRESSURE` remains rare** and is honestly disclosed rather than artificially inflated.

---

## 11. Setup & How to Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
cd frontend
npm ci
cd ..

# Only needed if backend/ml/artifacts/ampa.npz is missing:
python -m backend.ml.datasets.synthetic_generator --seed 42
python -m scripts.train_ampa_artifact --seed 42

# Start backend + frontend together:
npm run dev:all
```

| Task | Command |
|---|---|
| Backend API only | `python -m uvicorn app.main:app --app-dir backend --reload` (serves `http://127.0.0.1:8000`) |
| Frontend only | `npm --prefix frontend run dev` (proxies `/api`) |
| Backend tests | `python -m pytest tests -q` |
| Frontend tests | `npm --prefix frontend run test` |
| Frontend build | `npm --prefix frontend run build` |
| Retrain artifact | `python -m scripts.train_ampa_artifact --seed 42` |
| Regenerate data | `python -m backend.ml.datasets.synthetic_generator --seed 42` |
| Re-run evaluation | `python -m experiments.run_evaluation --seed 42 123 --epochs 100` |
| Seed college showcase | `python scripts/setup_showcase.py` (demo Student ID 1) |
| Reset showcase | `python scripts/reset_showcase.py` |

**Notes:** the frontend `VITE_API_URL` lives in `frontend/.env`; backend settings are read from
process environment variables. The default SQLite database is `backend/mistiq.db`. OpenAPI docs are
available at `/docs`.

---

*This document consolidates the project architecture, the MISTIQ-AMPA model, the data foundation,
the FastAPI backend and its API, the React user interface, every page and UX flow, and the measured
evaluation results. All figures are the checked-in synthetic-data measurements.*
