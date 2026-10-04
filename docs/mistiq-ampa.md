# MISTIQ-AMPA core engine

MISTIQ-AMPA (Adaptive Mistake Propagation Algorithm) predicts the next mistake category from a student's interaction history. **MISTIQ-AMPA is a project-specific custom sequential mistake-prediction framework. It is not claimed to be a newly invented universal machine-learning paradigm.** The implementation uses NumPy and explicit equations; it does not wrap a classifier library.

## Inputs and sequence state

The eight Phase 2 feature inputs, in order, are mistake frequency `F`, recency `R`, repetition `A`, difficulty sensitivity `D`, behavioral pressure `B`, concept confusion `C`, learning stability `S`, and mistake momentum `MM`. For a candidate error class `e`, AMPA uses the class-specific row

```text
X_e = [F_e, R_e, A_e, D_e, B_e, C_e, 1-S_e, MM_e]
```

`S` is protective. The implementation transforms it to instability `1-S` before fitting and before inference, so high stability is not directly added as risk. The feature adapter derives candidate rows from a student's events strictly earlier than the prediction timestamp. Context may provide a topic, subtopic, difficulty, or a previously engineered behavior-pressure value. Configured concept-pair eligibility matches an exact topic or subtopic label; training and online inference pass the same context fields. A current or future outcome is never used as context.

The per-student state store holds ordered interactions separately from global learned weights. It retains no future-derived feature cache. Concept-pair defaults include Precision/Recall, Ridge/Lasso, Overfitting/Underfitting, Stack/Queue, BFS/DFS, Mean/Median, and Classification/Regression.

## Mistake memory, recency, repetition

Each prior event has occurrence strength `E_i=1`. With age in days and configurable decay `lambda`:

```text
R_i = exp(-lambda * age_days)
A(N) = 1 + alpha * log(1 + N)
Memory(e,t) = sum_i [E_i * R_i * A_i]
```

The aggregate memory feature is bounded as `Memory / (Memory + memory_scale)`. The per-class recency feature uses the newest relevant event's exponential weight. Repetition is bounded from the same logarithmic amplification. These features distinguish recent evidence from old evidence while keeping long histories from growing without bound.

## Difficulty, behavior, confusion, stability, momentum

Difficulty sensitivity compares observed error rates on hard (4–5) and easy (1–2) relevant attempts, keeps positive hard-question vulnerability, and scales it by the current known difficulty. Behavioral pressure uses an explicit precomputed context value when supplied; otherwise it measures the last response time's deviation from the student's historical median on a log scale. Concept confusion is the proportion of relevant mistakes typed as `CONCEPT_CONFUSION` for a configured concept. Stability combines topic accuracy with outcome consistency; AMPA then uses its complement.

For each error class, the history is converted to a sequence of binary class-risk observations. Momentum needs two configured windows of `k` observations:

```text
MM_raw = mean(last k risks) - mean(previous k risks)
MM = tanh(MM_raw / tau)
```

Insufficient history returns zero momentum. The bounded transform preserves sign and prevents large values from dominating.

## Risk, probabilities, and training

AMPA learns global class-specific weights `W` and biases `b`. For each candidate mistake class `e`:

```text
Z_e = b_e + sum_j W[e,j] * X[e,j]
P(e) = exp(Z_e - max(Z)) / sum_k exp(Z_k - max(Z))
```

The softmax subtraction stabilizes exponentials. Fit accepts bounded feature rows (either `N x 8` shared rows or `N x classes x 8` candidate-specific rows), transforms stability, and fits mean/scale on the training input only. The retained training transform is reused for prediction. Zero-variance features use scale 1.

Training uses multiclass cross entropy with L2 weight regularization:

```text
L = -mean(log(P[target])) + lambda_reg * ||W||^2
delta = P - one_hot(y)
Gradient_W = X^T delta / N + 2 * lambda_reg * W
Gradient_b = mean(delta)
W = W - learning_rate * Gradient_W
b = b - learning_rate * Gradient_b
```

For class-specific rows, the weight gradient sums each sample's corresponding class row. Biases are not regularized. `fit_interactions` creates chronological training rows from strictly prior same-student events and excludes `CORRECT` outcomes from the mistake-class target set. No evaluation metric or baseline comparison is produced.

## Confidence and cold start

The returned top-class probability is the model's probability. Data reliability separately combines history volume, topic relevance, concept coverage, and outcome consistency. Confidence is `top_class_probability * data_reliability`. Configurable defaults yield `NO_RELIABLE_PREDICTION` for 0–4 attempts, `LOW_CONFIDENCE` for 5–14, `MEDIUM_CONFIDENCE` for 15–29, and `NORMAL_OPERATION` at 30 or more. In cold start, no predicted class is presented even though a fitted model's probability distribution remains available for inspection.

## Online state, explanations, and persistence

`update(interaction)` appends an ordered outcome to that student's history; it does not retrain global `W` or `b`. Future calls recompute memory, recency, repetition, confusion, and momentum from the filtered history. `explain` returns the selected class's standardized feature values, learned weights, and their actual `W[e,j] * X[e,j]` contributions. Persistence stores model version, weights, bias, training-only normalization parameters, classes, and configuration. It intentionally omits student histories.

The feature adapter is local to this engine and maps the implemented Phase 2 feature contract into the AMPA model input. It does not add a separate prediction algorithm.
