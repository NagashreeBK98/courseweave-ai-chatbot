from unittest.mock import patch, mock_open
import json

FAKE_CAREERS = {
    "careers": {
        "data_engineer": {
            "core_skills": ["SQL", "Python"],
            "tools": ["Airflow", "Spark"],
            "nice_to_have": ["Terraform"]
        }
    }
}

def test_build_skill_query_returns_string():
    with patch("builtins.open", mock_open(read_data=json.dumps(FAKE_CAREERS))):
        with patch("os.path.exists", return_value=True):
            from src.models.query_builder import build_skill_query
            result = build_skill_query("Data Engineer")
    assert isinstance(result, str)
    assert "SQL" in result

def test_career_not_found_returns_raw_goal():
    with patch("builtins.open", mock_open(read_data=json.dumps(FAKE_CAREERS))):
        with patch("os.path.exists", return_value=True):
            from src.models.query_builder import build_skill_query
            result = build_skill_query("Unknown Career")
    assert result == "Unknown Career"