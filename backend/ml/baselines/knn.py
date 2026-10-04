"""K-nearest-neighbors baseline; not MISTIQ-AMPA."""

from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .common import SklearnBaseline


class KNNBaseline(SklearnBaseline):
    model_name = "KNN"

    def __init__(self, neighbors=5):
        self.neighbors = neighbors
        super().__init__(make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=neighbors, weights="distance")))

    def fit(self, X, y):
        if len(X) < self.neighbors:
            self.estimator.set_params(n_neighbors=max(1, len(X)))
        return super().fit(X, y)
