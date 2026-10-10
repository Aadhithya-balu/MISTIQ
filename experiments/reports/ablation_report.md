# AMPA feature ablation

Delta is ablation macro F1 minus the full model for the same seed.

| Removed feature | Seed | Macro F1 | Delta F1 |
|---|---:|---:|---:|
| None (all features) | 42 | 0.3127 | +0.0000 |
| None (all features) | 123 | 0.3125 | +0.0000 |
| mistake_frequency | 42 | 0.3066 | -0.0061 |
| mistake_recency | 42 | 0.3150 | +0.0023 |
| repetition_score | 42 | 0.3134 | +0.0007 |
| difficulty_sensitivity | 42 | 0.3117 | -0.0010 |
| behavior_pressure | 42 | 0.3069 | -0.0058 |
| concept_confusion | 42 | 0.3088 | -0.0039 |
| learning_stability | 42 | 0.3072 | -0.0055 |
| mistake_momentum | 42 | 0.3158 | +0.0031 |
| mistake_frequency | 123 | 0.3064 | -0.0061 |
| mistake_recency | 123 | 0.3139 | +0.0014 |
| repetition_score | 123 | 0.3132 | +0.0007 |
| difficulty_sensitivity | 123 | 0.3115 | -0.0010 |
| behavior_pressure | 123 | 0.3069 | -0.0056 |
| concept_confusion | 123 | 0.3088 | -0.0037 |
| learning_stability | 123 | 0.3056 | -0.0069 |
| mistake_momentum | 123 | 0.3152 | +0.0027 |
