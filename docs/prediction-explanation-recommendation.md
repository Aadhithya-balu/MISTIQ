# MISTIQ prediction, explanation, and recommendation

Phase 7 uses the existing trained MISTIQ-AMPA artifact and the existing interaction tables. It does not retrain the artifact or change AMPA features, weights, or prediction math.

## Prediction and explanation

`GET /api/predictions/{student_id}/latest` continues to return the stored AMPA result and adds `top_predictions`, ranked from the actual probability distribution returned by the fitted model. `MISTIQ_PREDICTION_TOP_K` controls the number returned (default `3`). If AMPA has no reliable prediction yet, its existing cold-start behavior remains in effect and no probability values are fabricated.

`GET /api/predictions/{student_id}/latest/explanation` returns the saved feature values, learned weights, and contributions, plus student-facing summary and evidence. Only contributions whose absolute value meets `MISTIQ_EXPLANATION_CONTRIBUTION_THRESHOLD` are included (default `0.05`). The explanation states that these values contributed to a model score; it does not treat them as causal proof.

## Adaptive practice ranking

`GET /api/recommendations/{student_id}/next` ranks real questions from the question bank, stores the selected recommendation and returns its question. `GET /api/recommendations/{student_id}` returns recommendation history. `POST /api/recommendations/{recommendation_id}/complete` marks completion idempotently. Answering a recommended question also marks its latest unfinished recommendation complete.

The score is a normalized weighted sum:

```text
0.35 learning_need
+ 0.25 mistake_relevance
+ 0.20 difficulty_fit
+ 0.10 novelty
+ 0.10 retention_value
```

Each component is bounded to `[0, 1]`. The default weights can be overridden with `MISTIQ_RECOMMENDATION_WEIGHTS`, a JSON object containing all five component names. Concept confusion pairs default to the AMPA concept-pair list and can be overridden through `MISTIQ_CONCEPT_CONFUSION_PAIRS` as a JSON array of pairs. Difficulty fit uses the learner's observed accuracy by difficulty; topic relevance and retention use recorded mistake events; novelty uses actual attempt counts. Ties resolve consistently by attempt count and question ID.

Until AMPA has a `NORMAL_OPERATION` prediction, the route returns the same history-grounded ranking with `cold_start: true` and no `prediction_id`: a deterministic selection score, component breakdown, and topic-aware reason are still stored, but the pick is presented as starter practice rather than a forecast-driven recommendation. The ranking still prefers questions the learner has not attempted; once all questions have been attempted, it picks the least-attempted question with stable ID tie-breaking. With a normal-operation prediction, the returned item carries the prediction reference and `PRACTICE_QUESTION` type. If there are no bank questions, it returns a clear not-found response.

## Persistence and migration

Recommendations retain the existing student and optional prediction references and now store the selected question, overall score, component breakdown, and completion timestamp. SQLite startup migration adds these fields to existing databases; fresh databases get them from SQLAlchemy metadata. Recommendation scores are selection heuristics, not model probabilities or student outcomes.
