from src.models import query_builder


def mock_load_careers():
    return {
        "careers": {
            "data_engineer": {
                "core_skills": ["Python", "SQL"],
                "tools": ["Airflow"],
                "nice_to_have": ["Spark"],
            }
        }
    }


def test_build_query_returns_dict(monkeypatch):
    monkeypatch.setattr(query_builder, "load_careers", mock_load_careers)

    result = query_builder.build_query("Data Engineer")

    assert isinstance(result, dict)
    assert "skill_query" in result
    assert "career_skills" in result


def test_query_not_empty(monkeypatch):
    monkeypatch.setattr(query_builder, "load_careers", mock_load_careers)

    result = query_builder.build_query("Data Engineer")

    assert len(result["skill_query"]) > 0