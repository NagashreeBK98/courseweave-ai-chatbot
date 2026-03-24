import importlib
import sys


def test_retriever_interface():
    # Remove any previous mocks
    if "src.models.retriever" in sys.modules:
        del sys.modules["src.models.retriever"]

    retriever = importlib.import_module("src.models.retriever")

    result = retriever.normalize_course_code("ie 6400")

    assert result == "IE6400"