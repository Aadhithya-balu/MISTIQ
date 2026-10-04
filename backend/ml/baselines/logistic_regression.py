"""Logistic regression baseline; not MISTIQ-AMPA."""

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .common import SklearnBaseline


class LogisticRegressionBaseline(SklearnBaseline):
    model_name = "Logistic Regression"

    def __init__(self, seed=42):
        estimator = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed))
        super().__init__(estimator)
