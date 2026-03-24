import sys
from unittest.mock import MagicMock

# Mock heavy external modules BEFORE import
sys.modules["src.models.retriever"] = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = MagicMock()

from src.agents.recommendation_agent import format_courses_for_prompt


def test_format_courses():
    courses = [
        {
            "course_code": "IE6400",
            "course_name": "Data Mining",
            "text": "Learn data mining techniques",
            "score": 0.9,
        }
    ]

    prereq = [
        {
            "course_code": "IE6400",
            "prereqs_satisfied": True,
            "missing_prereqs": [],
        }
    ]

    result = format_courses_for_prompt(courses, prereq)
    assert "IE6400" in result