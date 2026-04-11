# Contributing to CourseWeave AI

## Setup

1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your credentials
6. For MLflow tracking: `pip install -r requirements-mlflow.txt`

## Branch Naming

- `feature/` — new features
- `fix/` — bug fixes
- `docs/` — documentation updates

## MLflow Experiment Tracking

Dashboard: https://dagshub.com/SIDDHARTH107/courseweave-ai.mlflow

To run evaluation with tracking: python scripts/run_eval_with_mlflow.py
To run LLM comparison with tracking: python scripts/run_llm_comparison_mlflow.py
To compare past experiment runs: python scripts/compare_experiments.py
To check MLflow server health: python scripts/check_mlflow_health.py

## Running Tests
pytest tests/ -v

## Project Structure

- `src/tracking/` — MLflow experiment tracking module
- `src/evaluation/` — RAG evaluation and LLM comparison
- `src/models/` — retriever, query builder, postgres filter
- `src/agents/` — recommendation agent
- `src/data/` — data scraping and career skill building
- `scripts/` — MLflow wrapper scripts and utilities
- `Data-Pipeline/` — Airflow DAG and ingestion scripts
- `configs/` — configuration files
- `tests/` — unit and integration tests