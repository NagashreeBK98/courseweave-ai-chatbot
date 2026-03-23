"""
adzuna_scraper.py
-----------------
Fetches real job postings from Adzuna API for target careers.
Extracts raw skills from job descriptions using regex pattern matching.

No LLM involvement here — pure data extraction.
LLM enrichment happens downstream in careers_builder.py.

Output: dict of career → raw skills extracted from real postings
"""

import os
import re
import json
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ADZUNA_APP_ID   = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY  = os.getenv("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"

# Careers we support → Adzuna search terms
CAREER_QUERIES = {
    "data_engineer":    "data engineer",
    "data_scientist":   "data scientist",
    "ml_engineer":      "machine learning engineer",
    "data_analyst":     "data analyst",
}

# Technical skills to scan for in job descriptions
# Add more here as needed
SKILL_PATTERNS = [
    # Languages
    r"\bPython\b", r"\bSQL\b", r"\bScala\b", r"\bJava\b", r"\bR\b",
    # Data engineering tools
    r"\bAirflow\b", r"\bApache Airflow\b", r"\bSpark\b", r"\bApache Spark\b",
    r"\bKafka\b", r"\bApache Kafka\b", r"\bdbt\b", r"\bETL\b", r"\bELT\b",
    r"\bdata pipeline\b", r"\bdata pipelines\b", r"\bdata warehousing\b",
    r"\bdata warehouse\b", r"\bdata lake\b", r"\bdata modeling\b",
    # Cloud + storage
    r"\bBigQuery\b", r"\bSnowflake\b", r"\bRedshift\b", r"\bDatabricks\b",
    r"\bGCS\b", r"\bGoogle Cloud Storage\b", r"\bS3\b", r"\bAWS\b",
    r"\bGCP\b", r"\bAzure\b",
    # MLOps + ML
    r"\bMLflow\b", r"\bMLOps\b", r"\bmachine learning\b", r"\bdeep learning\b",
    r"\bPyTorch\b", r"\bTensorFlow\b", r"\bscikit-learn\b", r"\bsklearn\b",
    r"\bfeature engineering\b", r"\bmodel deployment\b", r"\bmodel serving\b",
    # Infrastructure
    r"\bTerraform\b", r"\bDocker\b", r"\bKubernetes\b", r"\bCI/CD\b",
    # Analytics
    r"\bTableau\b", r"\bPower BI\b", r"\bLooker\b",
    r"\bA/B testing\b", r"\bstatistics\b", r"\bstatistical analysis\b",
    r"\bdata visualization\b",
    # General
    r"\bREST API\b", r"\bAPI\b", r"\bgit\b", r"\bLinux\b",
    r"\bNoSQL\b", r"\bMongoDB\b", r"\bPostgreSQL\b", r"\bMySQL\b",
]


def fetch_jobs(career_query: str, results_per_page: int = 20) -> list[dict]:
    """
    Hit Adzuna API and return raw job postings for a career query.
    Returns empty list if API call fails — pipeline continues gracefully.
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise ValueError(
            "ADZUNA_APP_ID and ADZUNA_APP_KEY must be set in .env"
        )

    params = {
        "app_id":           ADZUNA_APP_ID,
        "app_key":          ADZUNA_APP_KEY,
        "results_per_page": results_per_page,
        "what":             career_query,
        "where":            "united states",
        "content-type":     "application/json",
    }

    try:
        response = requests.get(ADZUNA_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        jobs = response.json().get("results", [])
        logger.info(
            "Fetched %d jobs for query: '%s'", len(jobs), career_query
        )
        return jobs
    except requests.exceptions.RequestException as e:
        logger.error("Adzuna API request failed for '%s': %s", career_query, e)
        return []


def extract_skills_from_text(text: str) -> list[str]:
    """
    Regex-based skill extraction from raw job description text.
    Returns deduplicated list of matched skill terms.
    No LLM — pure pattern matching against known skill list.
    """
    found = set()

    for pattern in SKILL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            # Normalize: strip regex word boundary markers
            skill = pattern.replace(r"\b", "").strip()
            found.add(skill)

    return sorted(list(found))


def scrape_careers() -> dict:
    """
    Master scraper function.
    Fetches Adzuna jobs for all target careers.
    Extracts raw skills from descriptions.

    Returns dict structured for careers_builder.py to consume:
    {
        "data_engineer": {
            "query": "data engineer",
            "postings_scraped": 20,
            "raw_skills": [...],
            "sample_titles": [...],
            "raw_descriptions": [...]   # passed to LLM downstream
        },
        ...
    }
    """
    scraped = {}

    for career_key, query in CAREER_QUERIES.items():
        logger.info("Scraping Adzuna for: %s", career_key)
        print(f"\nFetching jobs for: {career_key}...")

        jobs = fetch_jobs(query, results_per_page=20)

        if not jobs:
            logger.warning("No jobs returned for %s — skipping.", career_key)
            scraped[career_key] = {
                "query":             query,
                "postings_scraped":  0,
                "raw_skills":        [],
                "sample_titles":     [],
                "raw_descriptions":  [],
            }
            continue

        # Collect skills and descriptions across all postings
        all_skills        = set()
        sample_titles     = []
        raw_descriptions  = []

        for job in jobs:
            description = job.get("description", "")
            title       = job.get("title", "")

            if description:
                skills = extract_skills_from_text(description)
                all_skills.update(skills)
                # Keep first 500 chars of each description for LLM downstream
                raw_descriptions.append(description[:500])

            if title:
                sample_titles.append(title)

        scraped[career_key] = {
            "query":             query,
            "postings_scraped":  len(jobs),
            "raw_skills":        sorted(list(all_skills)),
            "sample_titles":     sample_titles[:5],
            "raw_descriptions":  raw_descriptions[:10],  # top 10 for LLM
        }

        print(
            f"  Done — {len(jobs)} postings, "
            f"{len(all_skills)} skills extracted"
        )

    return scraped


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = scrape_careers()

    print("\n\n=== SCRAPE RESULTS ===")
    for career, info in data.items():
        print(f"\n{career}:")
        print(f"  Postings scraped: {info['postings_scraped']}")
        print(f"  Skills found:     {info['raw_skills']}")
        print(f"  Sample titles:    {info['sample_titles']}")