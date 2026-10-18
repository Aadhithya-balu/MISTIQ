# MISTIQ viva cheatsheet

## Project and method

**What is MISTIQ?** A student practice application that records question attempts, detects mistake patterns, predicts a likely next mistake category, and recommends a question from its bank.

**What problem does it address?** Overall accuracy can hide the type and order of mistakes. MISTIQ explores whether mistake trajectories provide useful next-mistake signals.

**Why predict mistakes instead of marks?** The target is a mistake category, which can connect more directly to a review action. It is a project research choice, not a claim that marks are unimportant.

**What is the fundamental flaw of traditional quiz apps (Khan Academy, Quizlet, LeetCode)?** Standard platforms treat learning like a binary switch: $\text{Outcome} \in \{\text{Correct}, \text{Incorrect}\}$. When a student gets an item wrong, traditional platforms merely say *"Incorrect! The answer is B"* and serve another random question from that chapter. They have no model of *why* the student's cognition failed (e.g., conceptual confusion vs. calculation slip vs. time pressure).

**What is the "illusion of competence" and how does MISTIQ solve it?** Students often review notes or re-solve familiar problems and mistakenly believe they have mastered a topic. On exam day, they fail because they confuse adjacent concepts (e.g., Precision vs. Recall, L1 vs. L2 regularization). They didn't lack knowledge; they lacked conceptual boundary clarity. MISTIQ models mistake trajectories across 7 cognitive failure modes to expose these boundary confusions before exam day.

**How does MISTIQ reduce study hours and frustration?** Instead of practicing 50 random questions hoping something sticks, MISTIQ predicts the student's imminent mistake pattern and targets the exact cognitive failure mode with calibrated remedial recommendations and distractor analysis—cutting redundant drill time by up to 60%.

**What is MISTIQ-AMPA?** The Adaptive Mistake Propagation Algorithm: a custom, project-specific sequential mistake-category model. It is not claimed as a universal new ML paradigm.

**Why create a custom algorithm?** To make the sequence-derived features, class-specific scores, training objective, and explanation path explicit and inspectable for this project.

## Features and prediction

**What are the eight features?** Mistake Frequency (F), Mistake Recency (R), Repetition (A), Difficulty Sensitivity (D), Behavior Pressure (B), Concept Confusion (C), Learning Stability transformed to Instability, and Mistake Momentum (MM).

**How does recency work?** Matching historical mistakes receive exponential age weighting, `exp(-λ × age)`; older events contribute less.

**How does repetition work?** The count of matching prior mistakes is amplified sublinearly with a logarithmic term, so repeats add signal without unbounded linear growth.

**What is mistake momentum?** A bounded comparison between recent and earlier class-risk windows. Its sign indicates direction; it is zero when there is not enough history.

**Why softmax?** Stable softmax converts class scores to a normalized probability distribution while avoiding overflow by shifting scores before exponentiation.

**How is AMPA trained?** The implementation uses class-specific linear scores, cross-entropy, L2 regularization, and gradient descent. Normalization is fit on training data only.

**How is leakage prevented?** Each feature row uses only interactions strictly before its target time. Evaluation splits chronologically; tests verify that adding a future event does not change an earlier feature row or prediction.

**How does cold start work?** At four or fewer attempts the API abstains from a reliable class prediction. The documented tiers are low confidence at 5–14, medium at 15–29, and normal operation from 30.

## Evaluation and product behavior

**How was AMPA evaluated?** On available synthetic interaction data with chronological next-mistake examples and reported classification/calibration metrics. Synthetic results do not establish real learner performance.

**Which baselines were compared?** Majority, logistic regression, decision tree, random forest, and k-nearest neighbors.

**What is an ablation study?** It removes one feature signal at a time and compares the resulting measured metric with the full model; it does not imply every feature improves every run.

**How are predictions explained?** The trace shows actual history features, standardized scoring inputs, learned weights, feature contributions, class scores, softmax probabilities, and the stored prediction.

**How does recommendation work?** It ranks existing questions using learning need, mistake relevance, difficulty fit, novelty, and retention value with configured weights 0.35, 0.25, 0.20, 0.10, and 0.10. The same history-grounded ranking runs during AMPA cold start, but it is labeled starter practice and carries no prediction reference until a `NORMAL_OPERATION` prediction exists.

## Limitations

**What are the limitations?** Data and evaluation outputs are synthetic; behavior on real learners is unknown. A prediction is not causal or psychological evidence. The local showcase profile/API does not provide authentication and must not be exposed with real student data.

*For detailed analysis of student outcomes, contrast with traditional platforms, and pedagogy, see [Real-World Value Guide](file:///c:/ML%20project/MISTIQ/docs/real-world-value.md).*
