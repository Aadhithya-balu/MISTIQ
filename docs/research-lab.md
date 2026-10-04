# MISTIQ Research Lab

## Architecture and scope

The Research Lab is a read-only view over the saved AMPA artifact, stored prediction/attempt records, and Phase 4 experiment output files. The model API reports the artifact's model version, classes, risk features, learned weight matrix and bias, feature normalization, configuration, and training metadata. New prediction records preserve the feature cutoff, feature configuration, normalization, and global parameters used at inference. The trace endpoint replays chronological interactions in an isolated state store and independently recomputes features, scores, and probabilities from those saved inference parameters; it does not mutate online model state or retrain parameters. Older records without exact snapshots are marked approximate and are not reported as verified.

The pipeline is: student attempts → mistake events → chronological per-student state → class-specific feature engineering → stability-to-instability risk representation → linear AMPA class scores → stable softmax → predicted mistake class and confidence/reliability → explanation and recommendation. Student pages continue to show their practice guidance and simple prediction explanation. Weights, scores, and softmax internals are confined to Research routes.

**MISTIQ-AMPA is a project-specific custom sequential mistake-prediction framework designed for this project. It is not claimed to be a newly invented universal machine-learning paradigm.**

## Features and implementation

The feature functions are in `backend/ml/ampa/features.py`; temporal memory and recency are in `memory.py`; momentum is in `momentum.py`; risk scoring and stable softmax are in `risk.py`.

- **Mistake frequency:** combines class-specific mistake fraction with bounded time-decayed mistake memory: `0.5 * class_error_count / relevant_attempt_count + 0.5 * memory`. The denominator is at least one.
- **Mistake recency:** for a class, the newest matching mistake's `exp(-decay_rate * age_days)` weight. The configured default decay rate is `0.08` per day.
- **Repetition score:** `A = 1 + alpha * log(1 + N)` is calculated as repetition amplification and the feature itself is `(A - 1) / A`. The default `alpha` is `0.5`.
- **Mistake memory:** each matching event contributes `recency * (1 + alpha * log(1 + previous_occurrences))`; the aggregate is bounded as `total / (total + memory_scale)`, default scale `3.0`.
- **Difficulty sensitivity:** when both hard (difficulty ≥ 4) and easy (≤ 2) history exist, it is the nonnegative hard-minus-easy error-rate difference, bounded to `[0,1]`, multiplied by `(candidate_difficulty - 1)/4`. If data is insufficient, the implementation uses `0.25 * (candidate_difficulty - 1)/4`.
- **Behavior pressure:** by default this is `min(1, abs(log(latest_response_time / prior_median)) / log(4))`, using earlier response times for the median. Fewer than two observations returns zero. A supplied context value takes precedence. It measures deviation from the learner's observed baseline, not a trait such as slowness.
- **Concept confusion:** for an eligible topic in a configured concept pair, the fraction of relevant mistakes that are concept-confusion events. Default pairs include Precision/Recall, Ridge/Lasso, Overfitting/Underfitting, Stack/Queue, BFS/DFS, Mean/Median, and Classification/Regression. The API reads the configured pairs; examples are not asserted to be observed for a student.
- **Learning stability:** `accuracy * (1 - min(1, 2 * sqrt(accuracy * (1 - accuracy))))` over relevant history. Empty history returns zero. This is a computational learning-history signal. It is not personality, intelligence, mental health, or psychological diagnosis.
- **Mistake momentum:** build binary class-risk history, compare recent and preceding windows of `k=5`, then use `tanh((recent_mean - previous_mean) / 0.25)`. It returns zero when fewer than two full windows are present. Positive means rising class risk; negative means falling risk; near zero means little change.

Features are initially engineered in bounded ranges (momentum is signed). For scoring, stability is transformed to `instability = 1 - stability`; all features are then standardized with training-split means and scales saved in the artifact. The displayed scoring vector is therefore standardized and unbounded. `X` is class-specific: one feature row per candidate error class.

## Score, probability, explanation

For class `e`, the implementation computes `z_e = b_e + Σ_j W_ej X_ej`. Contributions shown by Formula Explorer are `W_ej * X_ej` and sum with the bias to the raw class score. Stable softmax subtracts the maximum score first: `z'_e = z_e - max(z)` and `p_e = exp(z'_e) / Σ_k exp(z'_k)`.

Prediction probability is the winning softmax probability. Data reliability is calculated separately from interaction volume, query relevance, concept coverage, and history consistency (see `backend/ml/ampa/prediction.py`). Confidence is winning probability multiplied by reliability. With at most four attempts the model abstains from returning a reliable predicted class, even though the class probability distribution may be available.

## Training objective and optimization

AMPA uses mean multiclass cross entropy plus L2 weight regularization, `L = -mean(log(p_true)) + lambda * ||W||²`. Bias is not regularized. The batch gradient is the class-specific equivalent of `Xᵀ(P-Y)/N + 2 lambda W`; the bias gradient is `mean(P-Y)`. `backend/ml/ampa/optimizer.py` applies full-batch gradient descent `W -= learning_rate * gradient_W`, `b -= learning_rate * gradient_b`. Learning rate, epoch count, regularization coefficient, seed, and feature configuration are read from the saved model artifact; the explorer does not insert default values for an existing artifact.

## Prediction and explanation trace

`GET /api/research/prediction/{prediction_id}/trace` uses the stored prediction's source attempt and context question, replays interactions for that student in `(timestamp, attempt_id)` order through the source attempt, and derives features using the backend feature implementation. New predictions persist the exact feature/parameter/score operands and inference cutoff alongside the ordinary student explanation; this avoids recency drift and allows bit-for-bit repeatable traces. The response distinguishes raw engineered values from standardized scoring values, returns actual `W` and `b`, contribution rows, raw and shifted scores, exponentials, softmax probabilities, and stored/replayed prediction comparison. Predictions without source context cannot be historically reconstructed and return a conflict response. Existing predictions created before Phase 9 do not have an exact snapshot, so their trace is reconstructed from history at the stored prediction time and may differ slightly from the original output due to the absence of a persisted inference cutoff.

## Evaluation and artifacts

Evaluation endpoints read existing files below `experiments/`: `reports/comparison.csv`, `ablations/ablation_results.json`, `calibration/`, `confusion_matrices/`, `reports/seed_robustness.json`, `learning_curves/learning_curve.json`, and `results/cold_start.json`. Missing files are marked unavailable; the API does not rerun experiments or manufacture metrics. The current comparison output is an aggregate (`mean`) table. Ablation Δ macro-F1 is displayed against that full-AMPA aggregate mean because the comparison artifact has no per-seed full-AMPA rows; this is clearly labeled and should not be interpreted as a paired per-seed difference. Calibration is empirical; softmax normalization by itself is not evidence of calibration. Some confusion-matrix and calibration artifacts are model/seed specific.

The learning-curve artifact includes history sizes 5, 10, 15, 20, 30, and 50 for seeds 42 and 123. The cold-start artifact contains 0–4 and 5–14 buckets without scored samples, ten samples in 15–29, and 218 samples in 30+ for the recorded seed. The absence of cold-start scores is shown as such; it is not extrapolated. Evaluation remains limited by the checked-in experiment dataset, its class distribution, and the saved seeds/splits. Metrics are descriptive project results, not claims of generalization to a representative student population.

## API

- `GET /api/research/model`, `/model/features`, `/model/parameters`
- `GET /api/research/students/{student_id}/predictions`
- `GET /api/research/prediction/{prediction_id}/trace`
- `GET /api/research/evaluation`, `/evaluation/ablations`, `/evaluation/calibration`, `/evaluation/confusion-matrix`, `/evaluation/seeds`, `/evaluation/learning-curves`, `/evaluation/cold-start`

These are research-facing, read-only endpoints. They expose model parameters and student-linked historical traces, so deployments intended for external users should put Research behind the institution's reviewer authorization boundary; the present project has no role-based authentication layer to enforce that distinction.
