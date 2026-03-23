from unittest.mock import patch, mock_open
import json
from src.models.query_builder import build_skill_query

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
        result = build_skill_query("Data Engineer")
    assert "SQL" in result
    assert isinstance(result, str)