def test_retriever_interface():
    from src.models.retriever import normalize_course_code

    assert normalize_course_code("ie 6400") == "IE6400"