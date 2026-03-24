import sys
from unittest.mock import MagicMock

# Mock careers.json loading
mock_careers = {
    "careers": {
        "data_engineer": {
            "core_skills": ["Python", "SQL"],
            "tools": ["Airflow"],
            "nice_to_have": ["Spark"]
        }
    }
}

mock_module = MagicMock()
mock_module.load_careers = MagicMock(return_value=mock_careers)

sys.modules["src.models.query_builder"].load_careers = MagicMock(return_value=mock_careers)

from src.models.query_builder import build_query


def test_build_query_returns_dict():
    result = build_query("Data Engineer")
    assert isinstance(result, dict)
    assert "skill_query" in result
    assert "career_skills" in result


def test_query_not_empty():
    result = build_query("Data Engineer")
    assert len(result["skill_query"]) > 0