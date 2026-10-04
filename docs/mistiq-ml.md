# MISTIQ machine-learning pipeline

The deployed prediction path is implemented in `backend/ml/ampa/` and uses the versioned artifact in `backend/ml/artifacts/ampa.npz`. The separate `backend/ml/baselines/` and `backend/ml/evaluation/` packages are used by offline Phase 4 experiments; they do not replace AMPA or run during student requests.

## Online AMPA

The predictor estimates a next mistake category from sequential student history. Its eight features are mistake frequency, recency, repetition, difficulty sensitivity, behavior pressure, concept confusion, learning stability, and mistake momentum. The feature adapter filters history strictly before its `as_of` timestamp. Candidate-class feature rows are transformed from stability to instability and standardized with values saved from training.

The global model computes class-specific linear scores and stable softmax probabilities. `W` and `b` are learned offline by full-batch gradient descent on mean multiclass cross entropy with L2 weight regularization. Online attempts append to per-student state, do not update `W` or `b`, and create a stored prediction/explanation only when the cold-start policy allows one.

## Dataset and offline evaluation

`backend/ml/datasets/` generates and validates synthetic student-question-attempt-mistake records. `backend/ml/evaluation/` constructs chronological next-mistake examples, applies a chronological train/validation/test split, trains AMPA and independent scikit-learn baselines, measures calibration/confusion matrices, and retrains AMPA for feature ablations. Normalization and model fitting use only the training partition. Validation and test examples use their available chronological prefix as online inference history, never their target label or future events.

Commands and mathematical detail are in [AMPA](mistiq-ampa.md), [data foundation](data-foundation.md), and [evaluation](evaluation.md). Experiment metrics describe the generated synthetic benchmark only.
