"""Majority-class baseline; not MISTIQ-AMPA."""

from sklearn.dummy import DummyClassifier

from .common import SklearnBaseline


class MajorityBaseline(SklearnBaseline):
    model_name = "Majority"

    def __init__(self, seed=42):
        super().__init__(DummyClassifier(strategy="prior", random_state=seed))
