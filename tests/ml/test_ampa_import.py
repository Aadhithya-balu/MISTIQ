from backend.ml.ampa import MISTIQAMPA


def test_ampa_model_imports():
    assert MISTIQAMPA().fitted_ is False
