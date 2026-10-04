# MISTIQ 2.0 College Showcase

The showcase uses a dedicated SQLite database at `data/showcase/showcase.db`, a local saved AMPA artifact, and synthetic question records. It does not read, reset, or write the normal development database. Setup is repeatable: it resets only that dedicated showcase database and rebuilds the student history through the real API, feature, prediction, and analytics services.

## Prepare or reset the showcase

From the repository root:

```powershell
python scripts/setup_showcase.py
```

The command prints the deterministic student ID, generated question and attempt counts, actual model prediction, recommendation, observed concept confusions, and Research trace verification. It requires the checked-in local AMPA artifact and does not use network services.

To remove only the showcase database before rebuilding it:

```powershell
python scripts/reset_showcase.py
python scripts/setup_showcase.py
```

Stop the backend before resetting. Setup itself also resets this same dedicated database before recreating it. It never removes another database.

## Start the application

From the repository root, in the backend terminal:

```powershell
cd backend
$env:DATABASE_URL = "sqlite:///../data/showcase/showcase.db"
python -m uvicorn app.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open the Vite URL and choose **Start Showcase**. The button reconnects to the seeded synthetic student (ID 1 in a freshly set up showcase database). The student shell displays **Showcase Mode · Synthetic Data**.

## Suggested walkthrough

1. On Dashboard, introduce the current prediction, its separate probability/confidence/reliability values, progress summary, recent mistakes, and next practice question.
2. Open **Why am I seeing this?** to show the explanation returned by the backend.
3. Open Mistakes and point out the observed Precision ↔ Recall confusion count and trend, alongside other actual mistake categories.
4. Follow the recommended question into Practice. Submit an answer and discuss the live correctness and detected mistake. For a concept-confusion response, the feedback derives the pair from the question and the selected distractor.
5. Visit Progress to review the recorded trajectory, topic/difficulty performance, and recovery summaries.
6. In Research → Formula Explorer, enter student ID 1 and select a real stored prediction. Follow its saved feature snapshot, standardized inputs, weights, contributions, scores, probabilities, and verification status.
7. End in Research → Evaluation. Explain the available synthetic comparison and artifacts honestly; a baseline may outperform AMPA on a metric.

The history is synthetic and constructed to make progression easy to discuss. Every displayed model output and analytics value comes from the local application pipeline; no prediction is scripted. This environment is for a college demonstration, not real learner records.
