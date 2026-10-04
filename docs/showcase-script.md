# Seven-minute MISTIQ showcase script

## 0:00–0:30 — Problem

“A score tells us how many answers were correct. It does not always show what kind of mistake may happen next. MISTIQ looks at the sequence and category of practice mistakes to find patterns worth revisiting.”

## 0:30–1:00 — MISTIQ concept

“MISTIQ means Mistake Intelligence & Sequential Prediction. This showcase uses synthetic data only. Its local database still runs through the same question, attempt, feature, prediction, recommendation, and analytics services as the application.”

## 1:00–2:00 — Student practice

Open Dashboard, then Practice. Point out the topic, difficulty, answer choices, and neutral feedback after submitting. Explain that correctness comes from the question answer key stored in the database.

## 2:00–3:00 — Mistake detection

Open Mistakes. Show the synthetic learner's early Precision/Recall confusion and the repeated-mistake count. “These counts are computed from recorded attempts. They are not hand-entered analytics.”

## 3:00–4:00 — AMPA prediction

Return to Dashboard. Identify the actual predicted category and show probability, confidence, and data reliability as separate values. Explain that the saved MISTIQ-AMPA model processes the prior interaction features and that its estimate is uncertain.

## 4:00–4:45 — Explanation and recommendation

Expand “Why am I seeing this?” and point to the returned evidence. Show the recommended question, then open it in Practice. The recommendation is an existing question ranked using the learner history and configured recommendation components.

## 4:45–5:30 — Progress and mistake intelligence

Open Progress. Show overall/recent performance and observed topic/difficulty patterns. Return to Mistakes for confusion and trend details. Note that the synthetic history includes more successful responses later, so the analytics summarize a changing sequence.

## 5:30–6:30 — Formula Explorer

Open Research → Formula Explorer and load student 1's predictions. Select one with an exact trace. Walk from prior events through feature values and normalization, then learned weights, contributions, class scores, stable softmax, and the stored prediction. Point out the exact/approximate verification label.

## 6:30–7:00 — Evaluation and conclusion

Open Evaluation. Show actual comparison, ablation, calibration, confusion, and seed artifacts that are present. “These results use synthetic data and are not evidence of educational efficacy. We report baseline comparisons as measured, including metrics where a baseline is stronger.”
