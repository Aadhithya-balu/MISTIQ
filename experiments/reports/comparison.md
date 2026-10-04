# Model comparison

Measured test-set metrics; rows are ordered by macro F1.

| Model | Macro F1 | Accuracy | Weighted F1 | Log Loss | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|
| KNN | 0.2028 | 0.2588 | 0.2523 | 193.6096 | 0.9516 | 0.2852 |
| Random Forest | 0.1671 | 0.2215 | 0.2128 | 52.9627 | 0.9225 | 0.2572 |
| Decision Tree | 0.1551 | 0.2149 | 0.2074 | 503.4762 | 1.4927 | 0.7245 |
| Logistic Regression | 0.1394 | 0.2500 | 0.1945 | 1.8543 | 0.8553 | 0.1620 |
| MISTIQ-AMPA | 0.1280 | 0.2632 | 0.1995 | 1.7898 | 0.8177 | 0.0655 |
| Majority | 0.0595 | 0.2632 | 0.1096 | 1.7376 | 0.8135 | 0.0130 |
