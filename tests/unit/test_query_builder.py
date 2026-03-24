from src.models.query_builder import build_query

def test_build_query_returns_dict():
    result = build_query("Data Engineer")
    assert isinstance(result, dict)
    assert "skill_query" in result
    assert "career_skills" in result

def test_query_not_empty():
    result = build_query("Data Engineer")
    assert len(result["skill_query"]) > 0