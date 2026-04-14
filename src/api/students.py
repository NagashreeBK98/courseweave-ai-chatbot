"""
students.py
-----------
Layer 2: Postgres inserts and student write operations.

Sits between main.py (HTTP layer) and recommendation_agent.py (AI layer).
Responsible for all DB inserts — main.py never writes to Postgres directly.

Flow:
    main.py  →  register_student()  →  Postgres INSERT
                                    →  generate_recommendation()  →  AI pipeline
"""

import os
import logging
import bcrypt
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "34.23.27.68"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "courseweave"),
        user=os.getenv("DB_USER", "courseweave_user"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    conn.autocommit = True
    return conn


def create_student(
    name: str,
    email: str,
    password: str,
    program_code: str,
    target_career: str,
    degree_path: str = None,
) -> dict:
    """
    Insert new student into Postgres only. Returns the student row immediately.
    Does NOT trigger the AI pipeline — call warm_up_recommendation() separately
    as a background task so signup never blocks on Gemini/Pinecone.

    Raises:
        psycopg2.errors.UniqueViolation  if email already exists
        Exception                        for any other DB error
    """
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    degree_path = degree_path or 'coursework'

    logger.info("Registering student: %s (%s)", email, program_code)
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        INSERT INTO students (name, email, program_code, target_career, password_hash, degree_path)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, name, email, program_code, target_career, degree_path
        """,
        (name, email, program_code, target_career, hashed, degree_path),
    )
    student = dict(cur.fetchone())
    conn.close()
    logger.info("Student %d inserted into Postgres", student["id"])
    return student


def warm_up_recommendation(student_id: int) -> None:
    """
    Fire-and-forget: pre-generate the first recommendation after signup.
    Intended to run as a BackgroundTask so the signup response is not blocked.
    Errors are logged but never raised.
    """
    try:
        from src.agents.recommendation_agent import generate_recommendation
        generate_recommendation(student_id=student_id)
        logger.info("Background recommendation ready for student %d", student_id)
    except Exception as e:
        logger.error("Background recommendation failed for student %d: %s", student_id, e)


def register_student(
    name: str,
    email: str,
    password: str,
    program_code: str,
    target_career: str,
    degree_path: str = None,
) -> dict:
    """
    Legacy helper kept for backwards compatibility with any direct callers.
    Prefer create_student() + warm_up_recommendation() (as a BackgroundTask) for
    HTTP endpoints where you don't want to block on the AI pipeline.
    """
    student = create_student(
        name=name,
        email=email,
        password=password,
        program_code=program_code,
        target_career=target_career,
        degree_path=degree_path,
    )
    try:
        from src.agents.recommendation_agent import generate_recommendation
        recommendation = generate_recommendation(student_id=student["id"])
    except Exception as e:
        logger.error("Recommendation pipeline failed for new student %d: %s", student["id"], e)
        recommendation = None
    return {
        "student": student,
        "recommendation": recommendation,
    }
