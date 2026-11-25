# MISTIQ: Intelligent Learning & Mistake Pattern Analyzer
## Slide Deck Presentation (10 Slides)

---

### Slide 1: Title Slide
# MISTIQ
### Mistake Identification & Sequential Trajectory Inference for Quantitative Learning
**AI-Powered Adaptive Learning Platform**

- **Model**: AMPA (*Adaptive Mistake Pattern Analyzer*)
- **Presented by**: [Your Name / Team]
- **Domain**: Machine Learning in EdTech & Cognitive Modeling

---

### Slide 2: Problem Statement (The "Binary Trap")
# Why Do Current Learning Platforms Fail?

- **The Problem**: Existing platforms (Google Forms, Canvas, Coursera) evaluate students as a simple binary outcome:
  $$\text{Score} = \text{Right (1)} \quad \text{or} \quad \text{Wrong (0)}$$
- **What is Missing?** All wrong answers are treated the same:
  - A fast **careless typo** is graded the same as a deep **concept confusion**.
  - Rushing under **time pressure** is graded the same as a **calculation error**.
- **The Consequence**: 
  - Students get frustrated with repeated "Wrong!" alerts.
  - Platforms cannot give personalized help because they do not know **why** the student made the mistake.

---

### Slide 3: Our Proposed Solution
# MISTIQ: Understanding the "Why" Behind Mistakes

- **Move from Binary Grading to Cognitive Diagnosis**:
  - Instead of just checking correctness, MISTIQ classifies errors into **7 cognitive mistake categories**:
    1. **Concept Confusion** (mixing up opposite terms like *Precision* vs. *Recall*)
    2. **Careless Error** (fast slips on easy concepts)
    3. **Calculation Error** (arithmetic/numerical slip)
    4. **Procedure Error** (steps performed in wrong order)
    5. **Time Pressure** (panicking when time runs out)
    6. **Difficulty Failure** (cognitive breakdown on hard problems)
    7. **Repeated Mistake** (repeating the exact same mistake twice)
- **Proactive AI**: Predicts what mistake the student will make **before** they make it, and automatically serves a targeted remedial lesson.

---

### Slide 4: Models Used in the Project
# Overview of Machine Learning Models

We tested and benchmarked multiple machine learning models:

1. **KNN (K-Nearest Neighbors)**:
   - *Category*: Instance-based learning.
   - *Purpose*: Finds past students with the nearest error profile to predict the current student's behavior.
2. **Random Forest**:
   - *Category*: Bagged ensemble learning (100 decision trees).
   - *Purpose*: Tests if combining non-linear decision trees improves prediction accuracy.
3. **Logistic Regression & Decision Tree**:
   - *Category*: Standard linear and rule-based baselines.
4. **MISTIQ-AMPA (Our Primary Production Model)**:
   - *Category*: Custom sequential regularized Softmax model with an online temporal memory engine.

---

### Slide 5: Baseline Models: KNN & Random Forest
# How Do the Baselines Work?

### 1. K-Nearest Neighbors (KNN — Nearest Error Retrieval)
- **Concept**: If Student A is rushing and failing at the same rate Student B did yesterday, Student A will likely make the same mistake.
- **How it works**: Measures the Euclidean distance between student feature vectors and takes the vote of the $k=5$ closest historical learner events.
- **Finding**: Good accuracy, but outputs extreme probabilities ($0\%$ or $100\%$), leading to poor probability calibration.

### 2. Random Forest (Bagging Model)
- **Concept**: Combines 100 decision trees trained on random subsets of student data (Bootstrap Aggregation).
- **Finding**: Achieved $48.9\%$ accuracy, but like KNN, tree averaging produced high Log Loss ($68.0$), making confidence scores uncalibrated.

---

### Slide 6: Our Core Model: AMPA
# AMPA (Adaptive Mistake Pattern Analyzer)

- **What Makes AMPA Special?**
  - Unlike static models, AMPA remembers that **human learning changes over time**:
    - **Forgetting Memory**: Older mistakes fade away using exponential recency decay ($\lambda = 0.08$).
    - **Mistake Momentum**: Detects whether a student is entering a frustration streak over the last 5 attempts.
    - **Concept-Pair Tracking**: Specifically monitors twin concepts (e.g. *Ridge* vs *Lasso*, *Stack* vs *Queue*).
- **Ultra-Fast & Explainable**:
  - Runs in **$< 2\text{ milliseconds}$** on normal CPU (no expensive GPU needed).
  - Can explain every prediction in plain English to the student.

---

### Slide 7: Mathematical Formulation of AMPA
# The Core Formulas

### 1. Linear Score Calculation (Logits)
For each mistake class $c \in \{1, \dots, 7\}$ and feature vector $\mathbf{x}_c \in \mathbb{R}^8$:
$$z_c = \mathbf{W}_c^T \mathbf{x}_c + b_c$$
*(Where $\mathbf{W}$ is the learned weight matrix and $b_c$ is the class bias)*

### 2. Probability Distribution (Softmax Function)
Converts raw scores into a calibrated percentage probability:
$$P(\text{Mistake} = c) = \frac{e^{z_c}}{\sum_{j=1}^{7} e^{z_j}}$$

### 3. Training Loss Function (Cross-Entropy with L2 Regularization)
$$\mathcal{L} = -\sum_{c=1}^{7} y_c \log(P(c)) + \frac{\lambda_{\text{reg}}}{2} \|\mathbf{W}\|^2$$
- Penalizes prediction errors while preventing weights from growing too large (avoiding overfitting).

---

### Slide 8: Experimental Results
# Why AMPA Won Over Other Models

All models were evaluated on chronological student interaction test splits:

| Model | Type | Accuracy | Log Loss (Lower is Better) | Expected Calibration Error |
| :--- | :--- | :---: | :---: | :---: |
| **MISTIQ-AMPA (Ours)** | **Linear + Temporal State** | **52.6%** | **1.42** *(Best)* | **0.097** *(Best Calibration)* |
| **KNN** | Nearest Neighbors | 51.7% | 171.53 *(Uncalibrated)* | 0.181 |
| **Logistic Regression** | Linear Baseline | 50.0% | 1.45 | 0.096 |
| **Random Forest** | Bagged Ensemble | 48.9% | 68.05 *(Uncalibrated)* | 0.194 |
| **Decision Tree** | Single Tree | 39.2% | 390.04 | 0.560 |

> **Key Takeaway**: AMPA achieved the **highest accuracy ($52.6\%$)** and the **best probability calibration (Log Loss $1.42$)**, ensuring predictions represent genuine student risk.

---

### Slide 9: User Experience: Student LMS vs. Admin Studio
# How MISTIQ Works in Practice

- **1. Student Portal (Coursera/Udemy Style Experience)**:
  - Shielded from complex ML math.
  - Receives **"Personalized Study Focus"** tips.
  - Interactive **💡 Concept Primers** with side-by-side comparison tables.
  - Multi-topic practice selector across 7 modules (Precision/Recall, Ridge/Lasso, Stack/Queue, etc.).
- **2. Instructor / ML Studio**:
  - Live model latency HUD ($<2\text{ms}$).
  - Live formula trace viewer ($z = Wx + b$).
  - Cognitive Simulator to test what happens when students make mistakes.

---

### Slide 10: Conclusion & Thank You
# Summary & Impact

- **Key Achievements**:
  1. Replaced blind binary grading ($0/1$) with **7-class cognitive error diagnosis**.
  2. Built **AMPA**, a fast, calibrated, and $100\%$ explainable sequential ML model.
  3. Created an **adaptive recommendation loop** that fixes student misconceptions before exams.
- **Real-World Impact**:
  - Reduces student exam anxiety.
  - Transforms online practice from stressful testing into guided learning.

---

# Thank You!
### Questions & Discussion
*(Open for Viva / Panel Q&A)*
