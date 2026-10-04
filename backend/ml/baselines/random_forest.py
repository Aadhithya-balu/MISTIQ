"""Random forest baseline; not MISTIQ-AMPA."""

from sklearn.ensemble import RandomForestClassifier

from .common import SklearnBaseline


class RandomForestBaseline(SklearnBaseline):
    model_name = "Random Forest"

    def __init__(self, seed=42):
        super().__init__(RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1))
