"""
llm_comparator.py
-----------------
Runs the same retrieval results through multiple LLMs
and compares response quality for experiment tracking.

Models compared:
    1. Gemini 2.5 Flash  — via Vertex AI (GCP credits)
    2. Llama 3.3 70B     — via Groq (free tier)
    3. GPT-4o mini       — via OpenAI ($5 free credit)

How to use:
    # Run directly to see comparison:
    python src/evaluation/llm_comparator.py

    # Teammate wraps with MLflow:
    with mlflow.start_run(run_name="llm_comparison"):
        results = compare_llms_for_student(student_id=1)
        for llm_name, data in results["responses"].items():
            mlflow.log_metric(f"{llm_name}_latency",        data["latency_seconds"])
            mlflow.log_metric(f"{llm_name}_response_length", data["response_length"])
            mlflow.log_text(data["response"], f"{llm_name}_response.txt")

Setup:
    uv add groq openai
    Add to .env:
        GROQ_API_KEY=your_groq_key       # free at console.groq.com
        OPENAI_API_KEY=your_openai_key   # $5 free credit at platform.openai.com
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("."))

load_dotenv()
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION   = os.getenv("GCP_LOCATION", "us-central1")

# ── LLM Configurations ───────────────────────────────────────────────────────
LLM_CONFIGS = {
    "gemini_2_5_flash": {
        "provider":   "vertexai",
        "model":      "gemini-2.5-flash",
        "max_tokens": 500,
    },
    "llama3_70b": {
        "provider":   "groq",
        "model":      "llama-3.3-70b-versatile",
        "max_tokens": 500,
    },
    "gpt4o_mini": {
        "provider":   "openai",
        "model":      "gpt-4o-mini",
        "max_tokens": 500,
    },
}


def call_gemini(config: dict, prompt: str) -> str:
    """Call Gemini 2.5 Flash via Vertex AI."""
    from google import genai
    client = genai.Client(
        vertexai=True,
        project=GCP_PROJECT_ID,
        location=GCP_LOCATION
    )
    response = client.models.generate_content(
        model=config["model"],
        contents=prompt,
    )
    return response.text.strip()


def call_groq(config: dict, prompt: str) -> str:
    """Call Llama 3.3 70B via Groq free tier."""
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=config["max_tokens"]
    )
    return response.choices[0].message.content.strip()


def call_openai(config: dict, prompt: str) -> str:
    """Call GPT-4o mini via OpenAI."""
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=config["max_tokens"]
    )
    return response.choices[0].message.content.strip()


def run_llm(llm_name: str, config: dict, prompt: str) -> dict:
    """
    Route to correct provider, measure latency, return result.
    Returns dict with response, latency, status.
    """
    start = time.time()

    try:
        if config["provider"] == "vertexai":
            response = call_gemini(config, prompt)
        elif config["provider"] == "groq":
            response = call_groq(config, prompt)
        elif config["provider"] == "openai":
            response = call_openai(config, prompt)
        else:
            raise ValueError(f"Unknown provider: {config['provider']}")

        latency = round(time.time() - start, 2)
        return {
            "response":        response,
            "latency_seconds": latency,
            "response_length": len(response),
            "status":          "success",
        }

    except Exception as e:
        latency = round(time.time() - start, 2)
        logger.error("LLM call failed for %s: %s", llm_name, e)
        return {
            "response":        None,
            "latency_seconds": latency,
            "response_length": 0,
            "status":          f"failed: {str(e)[:100]}",
        }


def build_comparison_prompt(
    student_context: dict,
    courses: list[dict],
    prereq_status: list[dict],
    career_goal: str,
    career_skills: dict
) -> str:
    """
    Build the shared prompt sent to all LLMs.
    Same prompt = fair comparison.
    """
    prereq_lookup = {p["course_code"]: p for p in prereq_status}

    courses_text = ""
    for i, course in enumerate(courses, 1):
        code   = course["course_code"]
        name   = course["course_name"]
        text   = course["text"][:200]
        status = prereq_lookup.get(code, {})

        prereq_note = (
            f"Prerequisites satisfied"
            if status.get("prereqs_satisfied", True)
            else f"Missing prerequisites: {status.get('missing_prereqs', [])}"
        )

        courses_text += f"{i}. {code} — {name}\n   {text}...\n   {prereq_note}\n\n"

    core_skills = career_skills.get("core_skills", [])
    tools       = career_skills.get("tools", [])

    return f"""You are CourseWeave, a friendly academic advisor at Northeastern University.

STUDENT PROFILE:
- Name: {student_context['name']}
- Program: {student_context['program_code']}
- Career goal: {career_goal}
- Completed courses: {', '.join(student_context['completed_courses'])}
- Core courses still needed: {', '.join(student_context['core_remaining'])}

KEY SKILLS NEEDED FOR {career_goal.upper()} (from real job market data):
- Core skills: {', '.join(core_skills)}
- Tools: {', '.join(tools)}

RETRIEVED COURSES (only recommend from this list):
{courses_text}

Write a friendly, conversational recommendation for {student_context['name']}.
Explain why each course fits their {career_goal} goal.
Flag any prerequisite warnings clearly.
Keep response under 250 words.
Only recommend courses from the list above."""


def compare_llms_for_student(
    student_id: int,
    career_goal: str = None,
    top_k: int = 3,
    llm_names: list = None
) -> dict:
    """
    Run the same retrieval results through multiple LLMs.
    Returns comparison dict for MLflow logging.

    Args:
        student_id:  Postgres student ID
        career_goal: Override career goal
        top_k:       Number of courses to retrieve
        llm_names:   Which LLMs to compare (default: all three)

    Returns:
    {
        "student_id":   1,
        "career_goal":  "Data Engineer",
        "courses":      [...],
        "prompt":       "shared prompt sent to all LLMs",
        "responses": {
            "gemini_2_5_flash": {
                "response":        "Hi Aisha...",
                "latency_seconds": 1.2,
                "response_length": 312,
                "status":          "success"
            },
            "llama3_70b": { ... },
            "gpt4o_mini":  { ... }
        },
        "summary": {
            "fastest":  "llama3_70b",
            "longest":  "gemini_2_5_flash",
            "all_succeeded": True
        }
    }

    ── TEAMMATE MLflow INSTRUCTIONS ────────────────────────────────────────
    import mlflow, json

    with mlflow.start_run(run_name="llm_comparison_student_1"):
        results = compare_llms_for_student(student_id=1)

        for llm_name, data in results["responses"].items():
            mlflow.log_metric(f"{llm_name}_latency_seconds", data["latency_seconds"])
            mlflow.log_metric(f"{llm_name}_response_length", data["response_length"])
            mlflow.log_param(f"{llm_name}_status",           data["status"])
            if data["response"]:
                mlflow.log_text(data["response"], f"{llm_name}_response.txt")

        mlflow.log_text(results["prompt"], "shared_prompt.txt")

        with open("data/llm_comparison.json", "w") as f:
            json.dump(results, f, indent=2)
        mlflow.log_artifact("data/llm_comparison.json")
    ────────────────────────────────────────────────────────────────────────
    """
    from src.models.postgres_filter import get_student_context, reorder_by_prerequisites
    from src.models.query_builder import build_query
    from src.models.retriever import get_relevant_courses

    if llm_names is None:
        llm_names = list(LLM_CONFIGS.keys())

    # ── Get student context + retrieve courses ───────────────────────────────
    student_context = get_student_context(student_id)
    if not student_context:
        return {"error": f"Student {student_id} not found."}

    if not career_goal:
        career_goal = student_context.get("target_career", "Data Engineer")

    query_result  = build_query(career_goal)
    query         = query_result["skill_query"]
    career_skills = query_result["career_skills"]
    courses       = get_relevant_courses(query, student_context, top_k=top_k)

    if not courses:
        return {"error": "No courses retrieved."}

    course_codes  = [c["course_code"] for c in courses]
    prereq_status = reorder_by_prerequisites(
        course_codes,
        student_context["completed_courses"],
        student_context["prereq_map"]
    )

    # ── Build shared prompt ──────────────────────────────────────────────────
    prompt = build_comparison_prompt(
        student_context, courses, prereq_status,
        career_goal, career_skills
    )

    # ── Run all LLMs ─────────────────────────────────────────────────────────
    print(f"\nRunning LLM comparison for student {student_id} ({career_goal})...\n")
    responses = {}

    for llm_name in llm_names:
        if llm_name not in LLM_CONFIGS:
            print(f"  ⚠️  Unknown LLM: {llm_name} — skipping")
            continue

        config = LLM_CONFIGS[llm_name]
        print(f"  Calling {llm_name}...", end=" ", flush=True)
        result = run_llm(llm_name, config, prompt)
        responses[llm_name] = result

        if result["status"] == "success":
            print(f"✅ {result['latency_seconds']}s | {result['response_length']} chars")
        else:
            print(f"❌ {result['status']}")

    # ── Summary ──────────────────────────────────────────────────────────────
    successful = {k: v for k, v in responses.items() if v["status"] == "success"}

    fastest = min(successful, key=lambda k: successful[k]["latency_seconds"]) if successful else None
    longest = max(successful, key=lambda k: successful[k]["response_length"]) if successful else None

    summary = {
        "fastest":       fastest,
        "longest":       longest,
        "all_succeeded": len(successful) == len(llm_names),
        "success_count": len(successful),
    }

    return {
        "student_id":    student_id,
        "career_goal":   career_goal,
        "courses":       courses,
        "prompt":        prompt,
        "responses":     responses,
        "summary":       summary,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("CourseWeave AI — LLM Comparator")
    print("=" * 60)
    print("\nNote: Groq and OpenAI keys needed for full comparison.")
    print("Gemini runs on GCP credits (always available).\n")

    # Run comparison for Aisha Patel
    # Start with Gemini only — add others once API keys are set
    available_llms = ["gemini_2_5_flash"]

    if os.getenv("GROQ_API_KEY"):
        available_llms.append("llama3_70b")
        print("Groq key found — adding Llama 3.3 70B")

    if os.getenv("OPENAI_API_KEY"):
        available_llms.append("gpt4o_mini")
        print("OpenAI key found — adding GPT-4o mini")

    results = compare_llms_for_student(
        student_id=1,
        llm_names=available_llms
    )

    if "error" not in results:
        print(f"\n{'=' * 60}")
        print("COMPARISON RESULTS")
        print(f"{'=' * 60}")
        print(f"Student:     {results['courses'][0]['course_code']} and others")
        print(f"Career goal: {results['career_goal']}")
        print(f"Fastest LLM: {results['summary']['fastest']}")
        print(f"Success:     {results['summary']['success_count']}/{len(available_llms)}")

        for llm_name, data in results["responses"].items():
            print(f"\n{'─' * 40}")
            print(f"MODEL: {llm_name}")
            print(f"Latency: {data['latency_seconds']}s | Length: {data['response_length']} chars")
            print(f"{'─' * 40}")
            if data["response"]:
                print(data["response"])
            else:
                print(f"FAILED: {data['status']}")

        # Save results
        os.makedirs("data", exist_ok=True)
        with open("data/llm_comparison.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nFull results saved to: data/llm_comparison.json")
        print("Share with MLflow teammate for logging.")
    else:
        print("Error:", results["error"])