"""
postgres_filter.py
------------------
Fetches student context from PostgreSQL.
This is the FIRST step in the recommendation pipeline.

Answers two questions with certainty before any vector search:
1. What has the student already completed?
2. What courses are they eligible to take next?

Eligibility rules:
- Must be in student's program
- Must not already be completed
- Must be active
- Core incomplete courses returned FIRST (academic policy)
"""

import os
import logging
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_connection():
    """Create and return a PostgreSQL connection."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def get_student_context(student_id: int) -> dict:
    """
    Fetch full student context from PostgreSQL.

    Returns:
    {
        "student_id":        1,
        "name":              "Aisha Patel",
        "email":             "patel.ai@northeastern.edu",
        "program_code":      "MS_DAE",
        "target_career":     "Data Engineer",
        "completed_courses": ["IE6400", "IE6700", "IE6200"],
        "eligible_courses":  ["IE7275", "IE6600", ...],  # core first
        "core_remaining":    ["IE7275", "IE6600"],       # incomplete core
        "electives_available": ["IE7615", "IE7500", ...]
    }

    Returns None if student not found.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # Step 1: Get student profile
            cur.execute("""
                SELECT id, name, email, program_code, target_career
                FROM students
                WHERE id = %s
            """, (student_id,))

            student = cur.fetchone()
            if not student:
                logger.warning("Student %d not found.", student_id)
                return None

            student = dict(student)

            # Step 2: Get completed courses
            cur.execute("""
                SELECT course_code
                FROM student_courses
                WHERE student_id = %s
            """, (student_id,))

            completed = [row["course_code"] for row in cur.fetchall()]

            # Step 3: Get all active courses for student's program
            # excluding already completed ones
            # Core courses come FIRST — academic policy
            cur.execute("""
                SELECT course_code, course_name, course_type
                FROM courses
                WHERE program_code = %s
                  AND is_active = TRUE
                  AND course_code NOT IN (
                      SELECT course_code FROM student_courses
                      WHERE student_id = %s
                  )
                ORDER BY
                    CASE WHEN course_type = 'Core' THEN 0 ELSE 1 END,
                    course_code
            """, (student["program_code"], student_id))

            eligible_rows = cur.fetchall()
            eligible      = [row["course_code"] for row in eligible_rows]
            core_remaining = [
                row["course_code"] for row in eligible_rows
                if row["course_type"] == "Core"
            ]
            electives_available = [
                row["course_code"] for row in eligible_rows
                if row["course_type"] == "Elective"
            ]

            # Step 4: Get prerequisite graph for eligible courses
            # Used later for reordering recommendations
            if eligible:
                cur.execute("""
                    SELECT course_code, required_course_code
                    FROM prerequisites
                    WHERE course_code = ANY(%s)
                """, (eligible,))

                prereq_rows = cur.fetchall()
                prereq_map  = {}
                for row in prereq_rows:
                    course   = row["course_code"]
                    required = row["required_course_code"]
                    if course not in prereq_map:
                        prereq_map[course] = []
                    prereq_map[course].append(required)
            else:
                prereq_map = {}

            return {
                "student_id":          student["id"],
                "name":                student["name"],
                "email":               student["email"],
                "program_code":        student["program_code"],
                "target_career":       student["target_career"],
                "completed_courses":   completed,
                "eligible_courses":    eligible,       # full list, core first
                "core_remaining":      core_remaining,
                "electives_available": electives_available,
                "prereq_map":          prereq_map,     # course → [required courses]
            }

    except Exception as e:
        logger.error("Failed to fetch student context for %d: %s", student_id, e)
        raise
    finally:
        conn.close()


def check_prerequisites_satisfied(
    course_code: str,
    completed_courses: list[str],
    prereq_map: dict
) -> tuple[bool, list[str]]:
    """
    Check if a student has satisfied prerequisites for a course.

    Returns:
        (True, [])                    — all prereqs satisfied
        (False, ["IE6400", "IE6700"]) — list of missing prereqs
    """
    required = prereq_map.get(course_code, [])
    missing  = [r for r in required if r not in completed_courses]

    if missing:
        return False, missing
    return True, []


def reorder_by_prerequisites(
    recommended_courses: list[str],
    completed_courses: list[str],
    prereq_map: dict
) -> list[dict]:
    """
    Takes a list of recommended course codes.
    Returns them reordered so prerequisites come before dependents.
    Flags courses that require a prerequisite not yet completed.

    Returns list of dicts:
    [
        {
            "course_code": "IE7275",
            "prereqs_satisfied": True,
            "missing_prereqs": []
        },
        {
            "course_code": "IE7615",
            "prereqs_satisfied": False,
            "missing_prereqs": ["IE7275"]
        }
    ]
    """
    result = []

    for course in recommended_courses:
        satisfied, missing = check_prerequisites_satisfied(
            course, completed_courses, prereq_map
        )
        result.append({
            "course_code":       course,
            "prereqs_satisfied": satisfied,
            "missing_prereqs":   missing
        })

    # Sort: courses with satisfied prereqs first
    result.sort(key=lambda x: (0 if x["prereqs_satisfied"] else 1))

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with student ID 1 — Aisha Patel, MS_DAE, Data Engineer
    print("\n=== Testing postgres_filter.py ===\n")

    context = get_student_context(1)

    if context:
        print(f"Student:          {context['name']}")
        print(f"Program:          {context['program_code']}")
        print(f"Target career:    {context['target_career']}")
        print(f"Completed:        {context['completed_courses']}")
        print(f"Core remaining:   {context['core_remaining']}")
        print(f"Electives avail:  {context['electives_available']}")
        print(f"Prereq map:       {context['prereq_map']}")

        print("\n--- Prereq check for eligible courses ---")
        for course in context["eligible_courses"][:5]:
            satisfied, missing = check_prerequisites_satisfied(
                course,
                context["completed_courses"],
                context["prereq_map"]
            )
            status = "✅" if satisfied else f"❌ needs {missing}"
            print(f"  {course}: {status}")

        print("\n--- Reorder test ---")
        sample = context["eligible_courses"][:5]
        reordered = reorder_by_prerequisites(
            sample,
            context["completed_courses"],
            context["prereq_map"]
        )
        for r in reordered:
            print(f"  {r}")