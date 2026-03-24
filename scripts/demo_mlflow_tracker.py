"""
This is the demo script to test all MLflow tracking functions for CourseWeave AI that we have created.
We have to run this script to verify everything works and populate the DagsHub UI.

Usage:
    python scripts/demo_mlflow_tracker.py
"""

import sys
import os

# Adding project root to path so we can import from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tracking.mlflow_tracker import (
    init_tracking,
    track_embedding_experiment,
    track_rag_query,
    track_prompt_experiment,
    track_experiment
)

def main():
    # Initializing the connection
    print("=" * 60)
    print("CourseWeave AI - MLflow Tracking Demo")
    print("=" * 60)
    init_tracking()
    print()

    # Demo 1: Embedding experiment
    print("[1/4] Logging embedding experiment...")
    track_embedding_experiment(
        model_name="all-MiniLM-L6-v2",
        chunk_size=512,
        chunk_overlap=50,
        total_courses=487,
        embedding_dim=384,
        generation_time_sec=12.8,
        vector_store="Pinecone",
        additional_params={"preprocessing": "lowercase_strip"}
    )
    print()

    # Logging a second embedding run with different settings for comparison
    print("[1b/4] Logging second embedding experiment for comparison...")
    track_embedding_experiment(
        model_name="text-embedding-ada-002",
        chunk_size=1024,
        chunk_overlap=100,
        total_courses=487,
        embedding_dim=1536,
        generation_time_sec=25.4,
        vector_store="Pinecone",
        additional_params={"preprocessing": "lowercase_strip"}
    )
    print()

    # Demo 2: RAG query tracking
    print("[2/4] Logging RAG query experiment...")
    track_rag_query(
        llm_model="gpt-3.5-turbo",
        temperature=0.3,
        top_k=5,
        query="I want to become a data engineer. What courses should I take in the MSDAE program?",
        retrieved_courses=["IE6750", "IE6740", "CS5200", "IE7374", "CS5800"],
        response="Based on your goal of becoming a data engineer, I recommend starting with IE 6750 (Data Warehousing) and CS 5200 (Database Management). These build your foundation in data infrastructure...",
        response_time_sec=2.3,
        relevance_score=0.87,
        prompt_version="v1"
    )
    print()

    # Demo 3: Prompt tuning experiment
    print("[3/4] Logging prompt tuning experiment...")
    track_prompt_experiment(
        prompt_version="v1_basic",
        prompt_template="""You are CourseWeave AI, an academic planning assistant or advisor for Northeastern University students.
Given the student's career goal and the retrieved course information, recommend the most relevant courses.
Include prerequisite information and suggest a semester by semester plan as well.

Career Goal: {career_goal}
Retrieved Courses: {courses}

Provide your recommendation:""",
        llm_model="gpt-3.5-turbo",
        test_queries=[
            "I want to be a data engineer",
            "Best ML courses for someone targeting research",
            "What electives help with cloud computing careers?",
            "I want to work in NLP after graduation"
        ],
        avg_relevance_score=0.82,
        avg_response_time_sec=2.1
    )
    print()

    # Demo 4: Generic experiment (data pipeline)
    print("[4/4] Logging data pipeline experiment...")
    track_experiment(
        experiment_name="courseweave-data-pipeline",
        run_name="scrape_spring2026_catalog",
        params={
            "source": "NEU Course Catalog",
            "semester": "Spring 2026",
            "scraper": "langchain_web_crawler"
        },
        metrics={
            "courses_scraped": 487,
            "programs_covered": 18,
            "scrape_time_sec": 42.5,
            "failed_pages": 3
        },
        tags={
            "team_member": "siddharth",
            "milestone": "model_development"
        }
    )
    print()

    # ─────────────────────────────────────────         
    print("=" * 60)
    print("All experiments logged successfully!")
    print(f"View dashboard: https://dagshub.com/SIDDHARTH107/courseweave-ai.mlflow")
    print("=" * 60)


if __name__ == "__main__":
    main()