"""
Unit tests for MLflow tracking module and data validation.
Run with: pytest tests/unit/test_mlflow_tracker.py -v
"""
import pytest
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

mlflow = pytest.importorskip("mlflow", reason="mlflow not installed")


def test_tracker_module_imports():
    """Test that the tracking module can be imported."""
    from src.tracking.mlflow_tracker import (
        init_tracking,
        track_embedding_experiment,
        track_rag_query,
        track_prompt_experiment,
        track_experiment
    )
    assert callable(init_tracking)
    assert callable(track_embedding_experiment)
    assert callable(track_rag_query)
    assert callable(track_prompt_experiment)
    assert callable(track_experiment)


def test_tracker_functions_have_docstrings():
    """Verify all tracking functions are documented."""
    from src.tracking.mlflow_tracker import (
        init_tracking,
        track_embedding_experiment,
        track_rag_query,
        track_prompt_experiment,
        track_experiment
    )
    assert init_tracking.__doc__ is not None
    assert track_embedding_experiment.__doc__ is not None
    assert track_rag_query.__doc__ is not None
    assert track_prompt_experiment.__doc__ is not None
    assert track_experiment.__doc__ is not None


def test_eval_dataset_structure():
    """Validate eval_dataset.json has correct structure."""
    dataset_path = os.path.join("data", "eval_dataset.json")
    if not os.path.exists(dataset_path):
        pytest.skip("eval_dataset.json not found")

    with open(dataset_path) as f:
        data = json.load(f)

    assert "metadata" in data
    assert "eval_dataset" in data
    assert data["metadata"]["total_cases"] == len(data["eval_dataset"])

    for case in data["eval_dataset"]:
        assert "test_id" in case
        assert "student_id" in case
        assert "program" in case
        assert "career_goal" in case
        assert "completed_courses" in case
        assert "expected_top_courses" in case
        assert "should_not_recommend" in case


def test_careers_json_structure():
    """Validate careers.json has correct structure."""
    careers_path = os.path.join("data", "careers.json")
    if not os.path.exists(careers_path):
        pytest.skip("careers.json not found")

    with open(careers_path) as f:
        data = json.load(f)

    assert "careers" in data
    expected_careers = ["data_engineer", "data_scientist", "ml_engineer", "data_analyst"]
    for career in expected_careers:
        assert career in data["careers"], f"Missing career: {career}"
        career_data = data["careers"][career]
        assert "core_skills" in career_data
        assert "tools" in career_data


def test_env_example_has_all_keys():
    """Check .env.example contains all required variables."""
    env_example_path = ".env.example"
    if not os.path.exists(env_example_path):
        pytest.skip(".env.example not found")

    with open(env_example_path) as f:
        content = f.read()

    required_keys = [
        "DAGSHUB_USERNAME",
        "DAGSHUB_TOKEN",
        "MLFLOW_TRACKING_URI",
        "DB_HOST",
        "PINECONE_API_KEY",
        "GCP_PROJECT_ID",
    ]
    for key in required_keys:
        assert key in content, f"Missing key in .env.example: {key}"