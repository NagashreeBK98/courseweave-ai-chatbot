"""
careers_builder.py
------------------
Takes raw scraped skills from Adzuna.
Gemini enriches with its own knowledge to fill gaps.
Outputs final careers.json — saved locally + uploaded to GCS + DVC versioned.

LLM role: structured enrichment ONLY.
Primary source is always Adzuna data.
llm_additions field makes LLM contribution fully transparent + traceable.
"""

import os
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from google.cloud import storage
from google import genai

from src.data.adzuna_scraper import scrape_careers

load_dotenv()

logger = logging.getLogger(__name__)

GCP_PROJECT_ID    = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION      = os.getenv("GCP_LOCATION", "us-central1")
GCS_BUCKET        = os.getenv("GCS_BUCKET")
CAREERS_JSON_PATH = "data/careers.json"

_gemini_client = None

def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT_ID,
            location=GCP_LOCATION
        )
    return _gemini_client


def enrich_with_gemini(career_key: str, raw_data: dict) -> dict:
    """
    Gemini receives Adzuna skills as ground truth.
    Adds its own knowledge to fill gaps.
    Returns structured skill categories.

    Gemini is a FORMATTER + ENRICHER here — not a decision maker.
    The llm_additions field tracks exactly what Gemini added
    beyond what Adzuna provided, for full traceability.
    """
    

    prompt = f"""
You are a structured data formatter for a university course recommendation system.

Here are REAL skills extracted from {raw_data['postings_scraped']} actual 
{career_key.replace('_', ' ')} job postings scraped from Adzuna 
(scraped {datetime.now().strftime('%B %Y')}):

Raw skills from Adzuna: {raw_data['raw_skills']}

Sample job titles seen: {raw_data['sample_titles']}

Your tasks:
1. Organize the Adzuna skills into: core_skills, tools, nice_to_have
2. Add any commonly required skills for {career_key.replace('_', ' ')} 
   roles that are MISSING from the Adzuna data above
3. Keep Adzuna data as primary source
4. Track what YOU added beyond Adzuna in the llm_additions field

Rules:
- core_skills: fundamental technical skills needed daily
- tools: specific software, platforms, frameworks
- nice_to_have: bonus skills that appear occasionally
- llm_additions: skills you added that were NOT in the Adzuna raw_skills list above

Return ONLY valid JSON. No explanation. No markdown. No backticks.
Exactly this structure:
{{
    "core_skills": ["skill1", "skill2"],
    "tools": ["tool1", "tool2"],
    "nice_to_have": ["skill1", "skill2"],
    "llm_additions": ["skills Gemini added beyond Adzuna data"]
}}
"""

    try:
        response = _get_gemini_client().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = response.text.strip()
        # Strip markdown if Gemini adds it anyway
        text = text.replace("```json", "").replace("```", "").strip()

        structured = json.loads(text)
        logger.info("Gemini enrichment successful for %s", career_key)
        return structured

    except json.JSONDecodeError as e:
        logger.error(
            "Gemini returned invalid JSON for %s: %s\nRaw: %s",
            career_key, e, text
        )
        # Fallback — use raw Adzuna skills without LLM structuring
        return {
            "core_skills":   raw_data["raw_skills"],
            "tools":         [],
            "nice_to_have":  [],
            "llm_additions": []
        }

    except Exception as e:
        logger.error("Gemini enrichment failed for %s: %s", career_key, e)
        return {
            "core_skills":   raw_data["raw_skills"],
            "tools":         [],
            "nice_to_have":  [],
            "llm_additions": []
        }


def save_to_gcs(local_path: str, gcs_path: str) -> None:
    """Upload careers.json to GCS bucket."""
    if not GCS_BUCKET:
        logger.warning("GCS_BUCKET not set — skipping GCS upload.")
        return

    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob   = bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        logger.info("Uploaded to GCS: gs://%s/%s", GCS_BUCKET, gcs_path)
        print(f"  Uploaded to GCS: gs://{GCS_BUCKET}/{gcs_path}")
    except Exception as e:
        logger.error("GCS upload failed: %s", e)


def build_careers_json() -> dict:
    """
    Master builder:
    1. Scrape Adzuna for all careers
    2. Enrich each career with Gemini
    3. Save careers.json locally
    4. Upload to GCS

    Returns the full careers dict for inspection.
    """

    # Step 1: Scrape Adzuna
    print("\n=== Step 1: Scraping Adzuna ===")
    raw_careers = scrape_careers()

    # Step 2: Enrich with Gemini
    print("\n=== Step 2: Enriching with Gemini ===")
    careers = {}

    for career_key, raw_data in raw_careers.items():
        print(f"\nEnriching: {career_key}...")

        if raw_data["postings_scraped"] == 0:
            logger.warning(
                "No Adzuna data for %s — skipping enrichment.", career_key
            )
            continue

        structured = enrich_with_gemini(career_key, raw_data)

        careers[career_key] = {
            "source":            "adzuna_api + gemini_enrichment",
            "scraped_at":        datetime.now(timezone.utc).isoformat(),
            "postings_analyzed": raw_data["postings_scraped"],
            "adzuna_raw_skills": raw_data["raw_skills"],  # original Adzuna data
            "core_skills":       structured.get("core_skills", []),
            "tools":             structured.get("tools", []),
            "nice_to_have":      structured.get("nice_to_have", []),
            "llm_additions":     structured.get("llm_additions", []),
        }

        print(f"  Core skills:    {careers[career_key]['core_skills']}")
        print(f"  Tools:          {careers[career_key]['tools']}")
        print(f"  LLM additions:  {careers[career_key]['llm_additions']}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "careers":      careers
    }

    # Step 3: Save locally
    print("\n=== Step 3: Saving careers.json ===")
    os.makedirs("data", exist_ok=True)
    with open(CAREERS_JSON_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved locally: {CAREERS_JSON_PATH}")

    # Step 4: Upload to GCS
    print("\n=== Step 4: Uploading to GCS ===")
    save_to_gcs(CAREERS_JSON_PATH, "data/careers.json")

    return output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = build_careers_json()

    print("\n\n=== FINAL careers.json ===")
    print(json.dumps(result, indent=2))