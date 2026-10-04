"""Decision tree baseline; not MISTIQ-AMPA."""

from sklearn.tree import DecisionTreeClassifier

from .common import SklearnBaseline


class DecisionTreeBaseline(SklearnBaseline):
    model_name = "Decision Tree"

    def __init__(self, seed=42):
        super().__init__(DecisionTreeClassifier(random_state=seed, class_weight=None))
