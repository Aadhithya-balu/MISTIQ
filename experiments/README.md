# Experiments

Run the Phase 4 comparison pipeline from the repository root:

```bash
python -m experiments.run_evaluation --seed 42 123 2026 7 99 --epochs 100
```

The runner records dataset path, chronological split sizes, seeds, feature configuration, model versions, metrics, and timestamps. Machine-readable outputs and reports are written under this directory. See [evaluation methodology](../docs/evaluation.md).
