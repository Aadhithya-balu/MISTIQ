# Temporal evaluation methodology

MISTIQ-AMPA is a project-specific custom sequential mistake-prediction framework, not a claim of a universal new machine-learning paradigm. Phase 4 compares its measured outputs with separate baseline models. Metrics are descriptive measurements on synthetic data, not claims of educational effectiveness or model superiority.

## Target and temporal split

Every incorrect attempt creates a next-mistake target; correct attempts remain in history but are not target labels. For each target at timestamp `t`, `build_next_mistake_examples` derives features from the same student's interactions strictly earlier than `t`, then appends the target outcome to that student's history for later examples. The target event's selected response, correctness, and mistake label are not features.

Examples are sorted chronologically and split globally, by default 70% training, 15% validation, and 15% test. Ratios can be changed on the command line. There is no random shuffle. AMPA feature means and scales are fit in `MISTIQAMPA.fit` from training `X` alone and reused unchanged for validation/test. Each baseline fits on the shared training examples only; its scaler is part of the baseline training pipeline. Ablations mask the selected feature before independently fitting AMPA on training rows.

Validation metrics are stored separately. Test metrics populate comparisons, confusion matrices, calibration outputs, and per-class results. Online-style validation/test feature histories may contain earlier interactions from those chronological portions, which would be observed at prediction time. The current target labels and any future interactions are excluded.

## Models and metrics

The model set is MISTIQ-AMPA plus Majority (`DummyClassifier`), Logistic Regression, Decision Tree, Random Forest, and KNN. Baselines receive the same chronological example splits and flattened class-candidate rows (7 × 8 features); AMPA retains class-specific rows.

Reports measure accuracy, macro precision/recall/F1, weighted F1, log loss, top-2/top-3 accuracy, multiclass Brier score, ECE, per-class statistics, and fixed-label confusion matrices. Brier score is the mean sum of squared class-probability errors in `[0,2]`. ECE is a sample-weighted top-label calibration gap computed from saved bins. Softmax probabilities are not presumed calibrated.

## Ablations and robustness

Each ablation sets one feature to zero in training, validation, and test inputs before that ablated model is fitted. This includes frequency, recency, repetition, difficulty sensitivity, behavior pressure, concept confusion, stability/instability, and momentum. The experiment runner's ablation report pairs ablation and full-AMPA macro F1 by seed. The Research page has the aggregate comparison table and labels its ΔF1 as the ablation seed score minus the available full-AMPA aggregate mean because the comparison CSV contains means rather than per-seed full-model entries.

Seed robustness reports mean, sample standard deviation (zero for a single seed), min, max, and seed count over actual runs. Cold-start analysis marks 0–4 prior attempts as not reliably predicted; 5–14, 15–29, and 30+ are reported as separate available history buckets. Learning curves use history sizes 5, 10, 15, 20, 30, and 50 by default and record sample counts.

## Run and output files

From the repository root:

```powershell
python -m experiments.run_evaluation --seed 42 123 --epochs 100
```

Key options include `--dataset`, `--output`, `--epochs`, `--ablation/--no-ablation`, `--baselines/--no-baselines`, `--cold-start/--no-cold-start`, and `--learning-curve/--no-learning-curve`. Outputs under `experiments/` include per-run `results/model_results.json`, validation files, calibration bins, confusion matrices, ablation rows/reports, cold-start results, learning curves, seed robustness, and comparison CSV/Markdown. The Research API reads these files and reports absence as unavailable instead of inventing data.

## Reproducibility and limitations

The synthetic dataset can be regenerated with `python -m backend.ml.datasets.synthetic_generator --seed 42`; preserve its CSVs and configuration when comparing reruns. The same input data, seed list, and configuration should reproduce metric values within floating-point tolerance; output timestamps/experiment IDs intentionally change. The task uses one chronological holdout rather than nested cross-validation or significance testing. Results depend on generated class distribution and synthetic response behavior, and do not establish real student performance. Some tree baseline probabilities may be poorly calibrated. AMPA may score below a baseline; results are reported without selective presentation.
