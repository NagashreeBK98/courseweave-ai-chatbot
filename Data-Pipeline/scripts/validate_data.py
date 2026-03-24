"""
validate_data.py
----------------
Schema validation + statistics generation for CourseWeave pipeline.

Uses pandas-based checks (Great Expectations style logic without the overhead).
Generates a statistics report saved to data/processed/stats_report.json.

Called as its own Airflow task AFTER preprocessing, BEFORE DB load.
"""

import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from datetime import timezone

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

VALID_PROGRAM_CODES = {"MS_DAE", "MS_DS", "MS_CS", "MS_DA", "MS_IS"}
VALID_COURSE_TYPES  = {"Core", "Elective"}


# ─────────────────────────────────────────
# Schema checks
# ─────────────────────────────────────────

def validate_courses(df: pd.DataFrame) -> list[dict]:
    """Run schema checks on courses DataFrame. Returns list of violations."""
    violations = []

    # Required columns present
    required_cols = {"course_code", "course_name", "credits", "program_code", "course_type"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        violations.append({"check": "required_columns", "detail": f"Missing: {missing_cols}"})

    # No nulls in required fields
    for col in required_cols & set(df.columns):
        null_count = df[col].isnull().sum()
        if null_count:
            violations.append({"check": "no_nulls", "column": col, "null_count": int(null_count)})

    # Unique course_code
    dupes = df["course_code"].duplicated().sum()
    if dupes:
        violations.append({"check": "unique_course_code", "duplicate_count": int(dupes)})

    # Valid program_codes
    invalid = df[~df["program_code"].isin(VALID_PROGRAM_CODES)]
    if len(invalid):
        violations.append({
            "check": "valid_program_code",
            "invalid_values": invalid["program_code"].unique().tolist()
        })

    # Valid course_types
    invalid = df[~df["course_type"].isin(VALID_COURSE_TYPES)]
    if len(invalid):
        violations.append({
            "check": "valid_course_type",
            "invalid_values": invalid["course_type"].unique().tolist()
        })

    # Credits must be positive integer
    if (df["credits"] <= 0).any():
        violations.append({"check": "positive_credits", "detail": "Credits <= 0 found"})

    return violations


def validate_prerequisites(df: pd.DataFrame, valid_codes: set) -> list[dict]:
    """Run schema checks on prerequisites DataFrame. Returns list of violations."""
    violations = []

    required_cols = {"course_code", "required_course_code"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        violations.append({"check": "required_columns", "detail": f"Missing: {missing_cols}"})
        return violations

    # No nulls
    for col in required_cols:
        null_count = df[col].isnull().sum()
        if null_count:
            violations.append({"check": "no_nulls", "column": col, "null_count": int(null_count)})

    # No duplicate pairs
    dupes = df.duplicated(subset=["course_code", "required_course_code"]).sum()
    if dupes:
        violations.append({"check": "unique_prereq_pairs", "duplicate_count": int(dupes)})

    # No self-referencing prerequisites
    self_refs = df[df["course_code"] == df["required_course_code"]]
    if len(self_refs):
        violations.append({
            "check": "no_self_reference",
            "self_refs": self_refs["course_code"].tolist()
        })

    # All referenced codes exist in courses
    orphaned_course = ~df["course_code"].isin(valid_codes)
    orphaned_req    = ~df["required_course_code"].isin(valid_codes)
    if orphaned_course.any() or orphaned_req.any():
        violations.append({
            "check": "valid_fk_references",
            "detail": "Prerequisite references non-existent course_code"
        })

    return violations


# ─────────────────────────────────────────
# Statistics generation
# ─────────────────────────────────────────

def generate_statistics(cleaned: dict) -> dict:
    """Compute descriptive statistics for the cleaned datasets."""
    courses = cleaned["courses"]
    prereqs = cleaned["prerequisites"]

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "courses": {
            "total_courses":         int(len(courses)),
            "by_program":            courses["program_code"].value_counts().to_dict(),
            "by_type":               courses["course_type"].value_counts().to_dict(),
            "avg_credits":           float(courses["credits"].mean()),
            "unique_programs":       int(courses["program_code"].nunique()),
        },
        "prerequisites": {
            "total_prereq_pairs":    int(len(prereqs)),
            "courses_with_prereqs":  int(prereqs["course_code"].nunique()),
            "most_required_course":  (
                prereqs["required_course_code"].value_counts().idxmax()
                if len(prereqs) else None
            ),
        },
    }
    return stats


# ─────────────────────────────────────────
# Master validate function (Airflow callable)
# ─────────────────────────────────────────

def validate_data(cleaned: dict) -> dict:
    """
    Master validation function called by Airflow task.
    Raises ValueError if critical violations found.
    Returns statistics report.
    """
    valid_codes = set(cleaned["courses"]["course_code"])

    course_violations = validate_courses(cleaned["courses"])
    prereq_violations = validate_prerequisites(cleaned["prerequisites"], valid_codes)

    all_violations = course_violations + prereq_violations

    if all_violations:
        for v in all_violations:
            logger.error("VALIDATION VIOLATION: %s", v)
        raise ValueError(f"Data validation failed with {len(all_violations)} violation(s). Check logs.")
    else:
        logger.info("All validation checks passed.")

    stats = generate_statistics(cleaned)

    # Save stats report
    report_path = PROCESSED_DIR / "stats_report.json"
    with open(report_path, "w") as f:
        json.dump(stats, f, indent=2)
    logger.info("Stats report saved to %s", report_path)

    return stats


if __name__ == "__main__":
    import logging
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from acquire_data import acquire_data
    from preprocess_data import preprocess_data

    logging.basicConfig(level=logging.INFO)
    raw     = acquire_data()
    cleaned = preprocess_data(raw)
    stats   = validate_data(cleaned)

    print("\n--- Validation passed. Statistics ---")
    print(json.dumps(stats, indent=2))