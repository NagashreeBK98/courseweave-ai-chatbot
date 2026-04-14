"""
Comparing MLflow experiment runs side by side.
Prints a summary table of all runs in an experiment.

Usage:
    python scripts/compare_experiments.py
"""
import os
import sys
import mlflow
import dagshub
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

dagshub.init(
    repo_owner=os.getenv("DAGSHUB_USERNAME"),
    repo_name="courseweave-ai",
    mlflow=True
)
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))


def compare_rag_runs():
    """Compare all RAG evaluation runs."""
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("courseweave-rag-evaluation")

    if not experiment:
        print("No RAG evaluation experiments found.")
        return

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"],
        max_results=10
    )

    if not runs:
        print("No runs found.")
        return

    print(f"\n{'='*80}")
    print(f"CourseWeave RAG Evaluation — Run Comparison ({len(runs)} runs)")
    print(f"{'='*80}")
    print(f"{'Run Name':<30} {'Precision@3':<14} {'Recall@3':<12} {'Violations':<12} {'Prereq Acc':<12} {'Date':<12}")
    print(f"{'-'*80}")

    for run in runs:
        name = run.info.run_name or "unnamed"
        metrics = run.data.metrics
        date_str = datetime.fromtimestamp(run.info.start_time / 1000).strftime("%m/%d/%Y")

        print(f"{name:<30} "
              f"{metrics.get('avg_precision_at_3', 0):<14.4f} "
              f"{metrics.get('avg_recall_at_3', 0):<12.4f} "
              f"{metrics.get('guardrail_violations', 0):<12.0f} "
              f"{metrics.get('prereq_flag_accuracy', 0):<12.4f} "
              f"{date_str:<12}")

    print(f"{'='*80}")
    print(f"Dashboard: https://dagshub.com/SIDDHARTH107/courseweave-ai.mlflow")


def compare_llm_runs():
    """Comparing all LLM comparison runs."""
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("courseweave-llm-comparison")

    if not experiment:
        print("No LLM comparison experiments found!")
        return

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"],
        max_results=10
    )

    if not runs:
        print("No runs found.")
        return

    print(f"\n{'='*80}")
    print(f"CourseWeave LLM Comparison - Run Comparison ({len(runs)} runs)")
    print(f"{'='*80}")

    for run in runs:
        metrics = run.data.metrics
        params = run.data.params
        date_str = datetime.fromtimestamp(run.info.start_time / 1000).strftime("%m/%d/%Y %H:%M")

        print(f"\nRun: {run.info.run_name} ({date_str})")
        print(f"  {'Model':<25} {'Latency (s)':<15} {'Response Length':<18} {'Status'}")
        print(f"  {'-'*70}")

        for model in ["gemini_2_5_flash", "llama3_70b", "gpt4o_mini"]:
            latency = metrics.get(f"{model}_latency_seconds", 0)
            length = metrics.get(f"{model}_response_length", 0)
            status = params.get(f"{model}_status", "unknown")
            print(f"  {model:<25} {latency:<15.2f} {int(length):<18} {status}")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    print("Fetching experiment data from DagsHub MLflow...")
    compare_rag_runs()
    compare_llm_runs()