"""
MLflow wrapper for CourseWeave RAG evaluation.
It runs the full evaluation pipeline and logs all metrics to DagsHub.
"""

import os
import sys
import json
import mlflow
import dagshub
from dotenv import load_dotenv

load_dotenv()

# Adding project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Initializing DagsHub + MLflow
dagshub.init(
    repo_owner=os.getenv("DAGSHUB_USERNAME"),
    repo_name="courseweave-ai",
    mlflow=True
)
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
mlflow.set_experiment("courseweave-rag-evaluation")

# Importing the evaluation function
from src.evaluation.eval_runner import run_evaluation

# RAG pipeline config
config = {
    "embedding_model": "bge-small-en-v1.5",
    "top_k": 3,
    "reranking": True,
    "mmr": True,
    "hyde": True,
    "hybrid_search": True,
}

# Running evaluation and logging to MLflow
with mlflow.start_run(run_name="courseweave_full_rag"):
    # Logging all config parameters
    for k, v in config.items():
        mlflow.log_param(k, v)

    # Running the actual evaluation
    metrics = run_evaluation(pipeline_config=config)

    # Logging metrics
    mlflow.log_metric("avg_precision_at_3", metrics["avg_precision_at_3"])
    mlflow.log_metric("avg_recall_at_3", metrics["avg_recall_at_3"])
    mlflow.log_metric("guardrail_violations", metrics["total_guardrail_violations"])
    mlflow.log_metric("prereq_flag_accuracy", metrics["prereq_flag_accuracy"])
    mlflow.log_metric("pass_rate", metrics["pass_rate"])
    mlflow.log_metric("gemini_calls_total", metrics["gemini_calls_total"])
    mlflow.log_metric("gemini_fallback_count", metrics["gemini_fallback_count"])

    # Saving and logging artifacts
    with open("data/eval_results.json", "w") as f:
        json.dump(metrics, f, indent=2)
    mlflow.log_artifact("data/eval_results.json")
    mlflow.log_artifact("data/eval_dataset.json")

    print("Evaluation complete! Metrics logged to MLflow.")
    print(f"View: https://dagshub.com/SIDDHARTH107/courseweave-ai.mlflow")