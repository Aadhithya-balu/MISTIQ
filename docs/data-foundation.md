# Data foundation

The synthetic interaction dataset is generated/exported as three related CSV files under `data/synthetic/` (the generated CSVs are ignored by Git and should be regenerated for a clean checkout):

- `questions.csv`: question content, difficulty (1–5), answer options, and per-distractor error mapping.
- `attempts.csv`: raw student selections, correctness, response time, timestamp, and per-question attempt number.
- `mistake_events.csv`: one linked event per attempt, including `CORRECT` events and categorized mistakes.

Question, attempt, and event field names are defined in `backend/ml/datasets/schema.py`. `validate_dataset` checks required values, IDs, difficulty/error categories, response time bounds, references, correctness consistency, and per-student chronology. `load_dataset` reads and validates the CSV files.

Generate the default 100-student, 500-question, 10,000-attempt dataset with:

```bash
python -m backend.ml.datasets.synthetic_generator --seed 42
```

Use `--students`, `--questions`, and `--attempts` to change the dataset size; `--min-response-time` and `--max-response-time` set response bounds. The Python `GeneratorConfig` also accepts custom concept confusion pairs. Reusing a seed and configuration reproduces the same rows. Student behavior profiles are latent generator settings and are not exported as labels.

All generated question content and interactions are synthetic. They are for data-pipeline development and do not represent real student records. To reproduce Phase 4 results, keep the same generated CSV files or regenerate them with the recorded seed and generator configuration.
