# MISTIQ Prototype Excellence Audit — Pass 1

Read-only audit of the MISTIQ hybrid (SQLite + FastAPI + React + AMPA) showcase prototype.

## Baseline (executed)

| Check | Result |
|---|---|
| Backend tests (`python -m pytest tests`) | 58 passed (7.43s) |
| Frontend tests (`npm --prefix frontend run test`) | 16 passed (5.15s) |
| Frontend build (`npm --prefix frontend run build`) | OK (20.09s) |
| Backend boots from root; `/health` | OK |
| DB (`backend/mistiq.db`) | FK integrity clean; `idempotency_key` unique; questions 501–514 only (curated demo set) |

## Verified strengths (with evidence)

- **Deterministic, data-driven outputs.** Prediction, probability, confidence, reliability, explanation reasons, progress analytics, and recommendation scores are all computed from stored interactions plus the saved model — no hardcoded numbers anywhere in the online path.
- **No temporal leakage in model quality.** `build_next_mistake_examples` uses only attempts strictly before the target attempt; evaluation uses a chronological split with `assert_temporal_order`; ablations are train-time only; each seed is evaluated independently.
- **Honest calibration/confidence.** Reliability gating by attempt count (`no_reliable_max=4`, `low_max=14`, `medium_max=29`, `normal_threshold=30`); confidence is defined as probability × reliability and is explained in the Formula Explorer. AMPA has the best calibration of the learned models (ECE 0.0655).
- **Single canonical DB.** `config.py` anchors `sqlite:///{backend/mistiq.db}`; the demo reset touches only `student_id = 1` rows (Prediction, Recommendation, MistakeEvent, Attempt, LearnerState) and keeps the Student row; synthetic bank ids (1–500) do not overlap the curated demo ids (501–514).
- **Offline vs online separation.** Training and evaluation live in `scripts/`/ML packages writing to `experiments/`; API research views are read-only over saved artifacts and the live model.
- **Forward-looking Formula Explorer.** Newer predictions store a `research_trace_snapshot` so the trace can be replayed EXACT against the saved model; older rows fall back to APPROXIMATE and this is shown honestly.
- **Frontend maturity.** Correct route wiring (`/` → `/dashboard`, login redirect, all `/research/*` modes); consistent loading/error/empty states across pages; ResearchPage is complex but complete; all displayed metrics originate from API responses.
- **Synthetic data is honestly labeled** in the research pages and README; no real-world effectiveness claims.

## Findings

### BLOCKER

None.

### HIGH

**H1 — Recommendation can never become personalized inside the demo.**
`recommend_next` only produces a scored `PRACTICE_QUESTION` when the latest prediction has status `NORMAL_OPERATION` (≥30 attempts). The curated demo is 2 passes × 14 questions = 28 attempts, so every showcased recommendation is `STARTER_PRACTICE`, which is "pick the least-attempted (or unseen then lowest-id) question" — fluency sampling, not a lesson-aware recommendation. After the last unseen question is completed, STARTER silently advances through questions by ID. The headline "recommendation" feature therefore cannot be demonstrated as grounding in the model's top class. (Design/correctness gap, not a data bug.)

**H2 — No end-to-end/regression coverage of several headline flows.**
There are no tests for the recommendation service or `recommendations/*` endpoints, none for `showcase_service` reset isolation, none for the explanation payload, and no automated smoke test that re-runs the documented demo script against a fresh DB. The 58 backend tests cover models, evaluation, DB integrity, health, the core submit flow, and research views, but the recommendation/explanation/showcase surface is only exercised manually.

### MEDIUM

**M1 — TIME_PRESSURE is a dead class.** 7/1517 (0.46%) training examples; 0 precision and 0 recall at every seed; the live `behavior_pressure` feature requires response_time ≥ 1.5× estimated, which is rarely reachable in short sessions. The Mistakes/Research UI presents seven mistake classes and one of them never appears. Honest disclosure exists, but the synthetic generator could be enriched (offline, training-time only) so the head is representable and the class can be learned.

**M2 — Low raw model quality (honestly disclosed).** AMPA aggregate accuracy 0.2632 and macro-F1 0.128 versus a best-baseline macro-F1 of 0.2028 (KNN); AMPA does have the best calibration of all models (ECE 0.0655 vs 0.257–0.725 for the tree/forest methods); only CONCEPT_CONFUSION, CARELESS, and REPEATED_MISTAKE are predicted with nonzero recall; cold-start bucket 15–29 has acc 0.0 / top-3 0.60. The negative CONCEPT_CONFUSION weight on the CC feature is data-driven, not a bug. This is the core known limitation and it is presented honestly (comparison, calibration, confusion, seed-robustness cards all show real numbers, and the negative weight is explained in the Formula Explorer), so no defensive fix is required in Pass 2 — only stronger presentation.

**M3 — Recommendation scoring is untested and its cold-start branch is a one-liner.** The weighted five-component scoring and the deterministic cold-start path have no unit or integration tests; refactors could silently change ranking. Missing tests (see M4) should cover at least `recommend_next` ranking stability and tie-breaking.

### LOW

- **L1** — The Dashboard "evidence" list could be empty if every `|contribution| < 0.05` threshold; verify in the E2E that the demo explanations render at least one evidence row.
- **L2** — STARTER tie-break prefers the numerically higher question id (last-seeded); deterministic but arbitrary.
- **L3** — `response_time` floor is 1s; combined with the 1.5× estimate rule, TIME_PRESSURE is effectively unreachable in a live session (ties into M1).
- **L4** — Duplicated `try: from backend.ml… except ImportError: from ml…` import shims across several modules; harmless but noisy.
- **L5** — `GET /students` returns all students with names; intentional for the showcase, but worth a note if this were ever deployed.

## Prioritized improvements for Pass 2 (ordered per the brief)

1. **Correctness / leakage / data-integrity** — audit found nothing to fix; instead add regression tests that lock in the protections (temporal order, FK/idempotency, demo isolation).
2. **AMPA / model-quality (justified only)** — *optional*: enrich the synthetic generator so TIME_PRESSURE is representable, retrain, and re-run evaluation (fixes M1). Keep the artifact swap traceable and the research views' graceful fallbacks.
3. **Prediction / explanation consistency** — verify non-empty evidence in E2E (L1); leave logic as-is.
4. **Recommendation relevance** — implement a deterministic, honest topic/difficulty-aware STARTER selection plus a real scored recommendation path for medium-confident students, with truthful copy (fixes H1, L2).
5. **Dashboard / Practice polish** — no defects found; minor copy/UX seasoning only.
6. **Mistakes / Progress polish** — keep truthful TIME_PRESSURE display; clarify in copy that extremely rare classes may not appear (tie to M1).
7. **Research / Formula Explorer** — already strong; keep.
8. **Error handling / responsive** — spot-check narrow viewports; confirm 409/503 copy is friendly (it is, mostly).
9. **Integration / regression tests** — add recommendation service + endpoints, showcase reset isolation, explanation payload, and a demo-flow smoke test (fixes H2, M3).
10. **Showcase setup / docs** — document the ≥30-attempt personalization threshold and the STARTER behavior of the demo, and note TIME_PRESSURE rarity (finishes M1 disclosure).

## Bottom line

The prototype is trustworthy: no leakage, no hardcoding, no DB split, honest synthetic labeling, strong calibration messaging, and a mature, fully-wired frontend. The gaps are (a) the recommendation story cannot reach "personalized" within the demo, (b) TIME_PRESSURE is unrepresentable, and (c) the recommendation/explanation/showcase surface lacks automated tests. All three are addressable in Pass 2 without violating the constraints.

## Pass 2 + Pass 3 — resolution status (2026-10-09)

### Pass 2 implemented
- **H1 (recommendation reachability) — RESOLVED.** `recommendation_service.py` now shares one history-grounded five-component ranking (`_rank_candidates`) across both branches. The `STARTER_PRACTICE` branch keeps `cold_start: true` and `prediction_id: null` (honest: not forecast-driven) but stores the score, component breakdown, and a topic-aware reason, and selects by learning need instead of question ID. Verified: the seeded demo now recommends **Q507 (Precision, the intentionally unattempted concept-confusion question)** because recent Precision/Recall mistakes genuinely justify it — L2’s arbitrary ID ordering is no longer the selector.
- **H2 (missing coverage) — RESOLVED.** Added `tests/unit/test_recommendation_service.py` (warm-start ranking, empty-history determinism, NORMAL_OPERATION scored path, completion advance) and `tests/integration/test_showcase.py` (seed state + recommendation, live-API explanation/completion loop, demo reset isolation). Updated the existing STARTER assertions in `test_backend_ml_flow.py`.
- **M3 (untested scoring) — RESOLVED** by the above unit/integration coverage.
- **L1 — VERIFIED.** The demo explanation renders non-empty `evidence` (asserted in the showcase integration test); no fallback needed.
- **Docs** `prediction-explanation-recommendation.md` and `viva-cheatsheet.md` updated to describe the history-grounded cold-start ranking honestly.
- **Mistakes-page copy (improvement 6) — DONE.** The mistake distribution now states that only patterns present in the learner's recorded practice are shown and that very rare categories can be absent in a short session.
- **Showcase/threshold docs (improvement 10) — DONE.** The ≥30-attempt `NORMAL_OPERATION` threshold and the demo's starter-practice behavior are documented in `prediction-explanation-recommendation.md`, `backend-ml-integration.md`, and `viva-cheatsheet.md`.

### Pass 3 verification (all executed, exact results)
| Check | Result |
|---|---|
| `python -m pytest tests` | **65 passed** (58 → 65) |
| `npm --prefix frontend run test` | **16 passed** |
| `npm --prefix frontend run build` | **OK** (14.06s) |
| Documented demo setup (`scripts/setup_showcase.py`) | Output verified: 16 attempts, 5 mistakes, prediction CONCEPT_CONFUSION (MEDIUM_CONFIDENCE), recommended **Q507/Precision** (STARTER_PRACTICE) |
| Full E2E (Student → Question → Attempt → Mistake → Feature update → AMPA prediction → Explanation → Recommendation → New attempt → Updated analytics → Formula trace) | **PASSED** against the real app/artifact/DB; prediction trace verifies **EXACT** with `replay_matches_stored == true`; SQLite confirmed to reflect the interaction |
| DB hygiene | E2E rows cleaned up; canonical demo state restored (1 student, 14 questions, 16 attempts, 5 mistakes, 12 predictions, 1 recommendation) |

### M1 — attempted, measured, and rolled back (2026-10-09)
- **Enrichment tried.** The synthetic generator was changed to emit `TIME_PRESSURE` when a wrong attempt's `response_time ≥ 1.5 × estimated_time` (mirroring the live behavior-pressure rule), replacing the old SLOW_ACCURATE 0.10 branch and moving response-time sampling before error-type selection. Regenerated with seed 42, the class grew from **7/1517 (0.46%) to 92 events (~5–8% of mistakes)** — genuinely representable in the corpus.
- **Measured outcome (full evaluation re-run, seeds 42/123).** `TIME_PRESSURE` still scored **precision 0.00 / recall 0.00** at every seed (test support 22), while aggregate quality *fell*: AMPA macro-F1 **0.128 → 0.101**, accuracy **0.263 → 0.200** (best baseline dropped likewise). The linear multiclass AMPA shares one normalized feature vector across all seven target-class rows, so widening a rare head reallocated label mass without making it separable. The change also flipped the curated demo prediction CONCEPT_CONFUSION → CALCULATION_ERROR.
- **Decision — reverted.** Regenerated the original corpus (deterministic seed), retrained the artifact **byte-identical to the committed one**, re-ran the evaluation (all metrics identical; only run `timestamp`/`experiment_id` values differ), and re-seeded the demo (CONCEPT_CONFUSION @ 0.3302, recommends Q507). `git status` clean; 65 backend / 16 frontend tests and the production build all pass.
- **Honest standing:** `TIME_PRESSURE` remains a rare, disclosed class. Making it *predicted* would require a model-structure change (per-class feature isolation) outside this hardening pass; inflating the corpus until it happens would be metric-gaming and was deliberately not done.

### M2 — investigated; confirmed a data/label ceiling (2026-10-09)
- **Read-only hyperparameter sweep.** Trained on the temporal train split and selected on the validation split (test reported), over `learning_rate ∈ {0.01, 0.03, 0.05, 0.1, 0.3, 1.0}`, `L2 ∈ {0.001, 0.01, 0.05, 0.2}`, `epochs ∈ {100, 300, 800}`, seeds 42/123. Validation macro-F1 was essentially flat — **0.1292 at the current default up to only 0.1309 at the best config** — and the current default was among the best on the held-out test macro-F1 (0.1385). The plateau shows the limit is the synthetic label distribution, not the optimizer.
- **Decision — no change.** A model-structure change (non-linear or richer per-class features) would be needed for a material gain, which is out of scope for this hardening pass and would break the Formula-Explorer trace contract and the curated demo. AMPA's real, already-documented advantage is calibration and interpretability; KNN leads raw macro-F1 (0.2028). Reported honestly, no patch applied.

### Not implemented
- Recommendation logic, demo narrative, and copy remain within the audit constraints (no hardcoding, no artifact edits, the real pipeline is the only path).
