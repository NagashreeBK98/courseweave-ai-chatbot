"""
This module will provide functions to log experiments to DagsHub's hosted MLflow server.
Used for tracking embedding generation, RAG query performance, and prompt tuning as well.

Setup:
    1. We always have to ensure .env file has DAGSHUB_USERNAME, DAGSHUB_TOKEN, MLFLOW_TRACKING_URI
    2. Consider: pip install mlflow dagshub python-dotenv

Usage:
    from src.tracking.mlflow_tracker import init_tracking, track_embedding_experiment
    
    init_tracking()
    track_embedding_experiment(model_name="all-MiniLM-L6-v2", ...)
"""

import os
import json
import time
import tempfile
import mlflow
import dagshub
from dotenv import load_dotenv

load_dotenv()

# Initializing

def init_tracking():
    """
    Initializing the DagsHub + MLflow connection.
    """
    dagshub.init(
        repo_owner=os.getenv("DAGSHUB_USERNAME"),
        repo_name="courseweave-ai",
        mlflow=True
    )
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
    print(f"MLflow tracking initialized for {os.getenv('DAGSHUB_USERNAME')}/courseweave-ai")


# 1. Embedding Experiment Tracking

def track_embedding_experiment(
    model_name: str,
    chunk_size: int,
    chunk_overlap: int,
    total_courses: int,
    embedding_dim: int,
    generation_time_sec: float,
    vector_store: str = "Pinecone",
    additional_params: dict = None,
    artifacts: dict = None
):
    """
    Tracking an embedding generation run.
    
    We need to use this when we generate/regenerate embeddings with different models
    or chunking strategies and want to compare them.
    
    Args:
        model_name: Name of embedding model (e.g., "all-MiniLM-L6-v2")
        chunk_size: Size of text chunks in characters
        chunk_overlap: Overlap between chunks in characters
        total_courses: Number of courses processed
        embedding_dim: Dimension of output embeddings
        generation_time_sec: Time taken to generate all embeddings
        vector_store: Vector DB used (default: "Pinecone")
        additional_params: Any extra parameters to log
        artifacts: Dict of {name: file_path} to log as artifacts
    
    """
    mlflow.set_experiment("courseweave-embeddings")

    with mlflow.start_run(run_name=f"embed_{model_name}_chunk{chunk_size}"):
        # Logging parameters
        mlflow.log_param("embedding_model", model_name)
        mlflow.log_param("chunk_size", chunk_size)
        mlflow.log_param("chunk_overlap", chunk_overlap)
        mlflow.log_param("total_courses", total_courses)
        mlflow.log_param("vector_store", vector_store)

        # Logging additional params if provided
        if additional_params:
            mlflow.log_params(additional_params)

        # Logging metrics
        mlflow.log_metric("embedding_dim", embedding_dim)
        mlflow.log_metric("generation_time_sec", generation_time_sec)
        mlflow.log_metric("courses_per_second", total_courses / generation_time_sec if generation_time_sec > 0 else 0)

        # Logging artifacts if provided
        if artifacts:
            for name, path in artifacts.items():
                mlflow.log_artifact(path)

        print(f"Logged embedding experiment: {model_name}, chunk_size={chunk_size}")



# RAG Query Tracking


def track_rag_query(
    llm_model: str,
    temperature: float,
    top_k: int,
    query: str,
    retrieved_courses: list,
    response: str,
    response_time_sec: float,
    relevance_score: float = None,
    prompt_version: str = "v1",
    additional_metrics: dict = None
):
    """
    Tracking a RAG retrieval + LLM generation run.
    
    We need to use this when testing different LLM configs, retrieval settings,
    or prompt templates to compare response quality.
    
    Args:
        llm_model: LLM used (e.g., "gpt-3.5-turbo", "gemini-pro")
        temperature: LLM temperature setting
        top_k: Number of documents retrieved from vector store
        query: The student's question
        retrieved_courses: List of course codes/names retrieved
        response: The LLM's generated response
        response_time_sec: Total time from query to response
        relevance_score: Optional quality score (0-1)
        prompt_version: Version identifier for the prompt template
        additional_metrics: Any extra metrics to log

    """
    mlflow.set_experiment("courseweave-rag-queries")

    with mlflow.start_run(run_name=f"rag_{llm_model}_topk{top_k}"):
        # Logging parameters
        mlflow.log_param("llm_model", llm_model)
        mlflow.log_param("temperature", temperature)
        mlflow.log_param("top_k_retrieval", top_k)
        mlflow.log_param("prompt_version", prompt_version)
        mlflow.log_param("query", query[:250])  # Here, 250 we have given because MLflow param limit is 500 chars

        # Logging metrics
        mlflow.log_metric("response_time_sec", response_time_sec)
        mlflow.log_metric("num_courses_retrieved", len(retrieved_courses))
        if relevance_score is not None:
            mlflow.log_metric("relevance_score", relevance_score)

        # Logging additional metrics if provided
        if additional_metrics:
            mlflow.log_metrics(additional_metrics)

        # Logging the full query/response as a JSON artifact
        io_log = {
            "query": query,
            "retrieved_courses": retrieved_courses,
            "response": response,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, prefix="rag_io_") as f:
            json.dump(io_log, f, indent=2)
            temp_path = f.name
        mlflow.log_artifact(temp_path, "rag_io_logs")
        os.unlink(temp_path)  # Cleaning up the temp file

        print(f"Logged RAG query: model={llm_model}, top_k={top_k}, time={response_time_sec}s")


# Prompt Version Tracking

def track_prompt_experiment(
    prompt_version: str,
    prompt_template: str,
    llm_model: str,
    test_queries: list,
    avg_relevance_score: float,
    avg_response_time_sec: float,
    additional_metrics: dict = None
):
    """
    Tracking a prompt template version and its performance.
    
    We need to use this when we change the system prompt and want to compare
    how different prompt versions perform across a set of test queries.
    
    Args:
        prompt_version: Version identifier (e.g., "v1", "v2_career_focused")
        prompt_template: The full prompt template text
        llm_model: LLM used for testing
        test_queries: List of queries tested against
        avg_relevance_score: Average relevance score across test queries
        avg_response_time_sec: Average response time across test queries
        additional_metrics: Any extra metrics to log
    
    """
    mlflow.set_experiment("courseweave-prompt-tuning")

    with mlflow.start_run(run_name=f"prompt_{prompt_version}"):
        # Logging parameters
        mlflow.log_param("prompt_version", prompt_version)
        mlflow.log_param("llm_model", llm_model)
        mlflow.log_param("num_test_queries", len(test_queries))

        # Logging metrics
        mlflow.log_metric("avg_relevance_score", avg_relevance_score)
        mlflow.log_metric("avg_response_time_sec", avg_response_time_sec)

        if additional_metrics:
            mlflow.log_metrics(additional_metrics)

        # Logging the prompt template as an artifact
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="prompt_") as f:
            f.write(f"Prompt Version: {prompt_version}\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(prompt_template)
            temp_path = f.name
        mlflow.log_artifact(temp_path, "prompt_templates")
        os.unlink(temp_path)

        # Logging test queries as artifact
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, prefix="test_queries_") as f:
            json.dump({"test_queries": test_queries}, f, indent=2)
            temp_path = f.name
        mlflow.log_artifact(temp_path, "test_queries")
        os.unlink(temp_path)

        print(f"Logged prompt experiment: {prompt_version}, avg_relevance={avg_relevance_score}")


# Generic Experiment Tracking

def track_experiment(
    experiment_name: str,
    run_name: str,
    params: dict,
    metrics: dict,
    artifacts: dict = None,
    tags: dict = None
):
    """
    Generic tracker for any experiment type.
    
    We need to use this as a flexible catch-all when the specific functions above
    don't fit our use case.
    
    Args:
        experiment_name: Name of the MLflow experiment
        run_name: Name for this specific run
        params: Dict of parameters to log
        metrics: Dict of metrics to log
        artifacts: Optional dict of {name: file_path} to log
        tags: Optional dict of tags to add to the run
    
    """
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)

        if tags:
            mlflow.set_tags(tags)

        if artifacts:
            for name, path in artifacts.items():
                mlflow.log_artifact(path)

        print(f"Logged experiment: {experiment_name}/{run_name}")