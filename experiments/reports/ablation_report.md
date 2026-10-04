# AMPA feature ablation

Delta is ablation macro F1 minus the full model for the same seed.

| Removed feature | Seed | Macro F1 | Delta F1 |
|---|---:|---:|---:|
| None (all features) | 42 | 0.1259 | +0.0000 |
| None (all features) | 123 | 0.1300 | +0.0000 |
| mistake_frequency | 42 | 0.1261 | +0.0002 |
| mistake_recency | 42 | 0.1258 | -0.0001 |
| repetition_score | 42 | 0.1230 | -0.0028 |
| difficulty_sensitivity | 42 | 0.1247 | -0.0012 |
| behavior_pressure | 42 | 0.1229 | -0.0029 |
| concept_confusion | 42 | 0.1259 | +0.0000 |
| learning_stability | 42 | 0.1185 | -0.0074 |
| mistake_momentum | 42 | 0.1345 | +0.0086 |
| mistake_frequency | 123 | 0.1319 | +0.0018 |
| mistake_recency | 123 | 0.1299 | -0.0001 |
| repetition_score | 123 | 0.1214 | -0.0087 |
| difficulty_sensitivity | 123 | 0.1243 | -0.0058 |
| behavior_pressure | 123 | 0.1213 | -0.0088 |
| concept_confusion | 123 | 0.1317 | +0.0017 |
| learning_stability | 123 | 0.1205 | -0.0096 |
| mistake_momentum | 123 | 0.1325 | +0.0024 |
