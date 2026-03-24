"""
MLflow wrapper for LLM comparison (Gemini vs Llama).
It compares responses from different LLMs and logs results to DagsHub.
"""
import os
import sys
import mlflow
import dagshub
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Initializing DagsHub + MLflow
dagshub.init(
    repo_owner=os.getenv("DAGSHUB_USERNAME"),
    repo_name="courseweave-ai",
    mlflow=True
)
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
mlflow.set_experiment("courseweave-llm-comparison")

# Importing the comparison function
from src.evaluation.llm_comparator import compare_llms_for_student

# Running comparison and logging to MLflow
with mlflow.start_run(run_name="llm_comparison"):
    results = compare_llms_for_student(student_id=1)

    for llm_name, data in results["responses"].items():
        mlflow.log_metric(f"{llm_name}_latency_seconds", data["latency_seconds"])
        mlflow.log_metric(f"{llm_name}_response_length", data["response_length"])
        mlflow.log_param(f"{llm_name}_status", data["status"])
        if data["response"]:
            mlflow.log_text(data["response"], f"{llm_name}_response.txt")

    print("LLM comparison complete! Results logged to MLflow.")
    print(f"View: https://dagshub.com/SIDDHARTH107/courseweave-ai.mlflow")