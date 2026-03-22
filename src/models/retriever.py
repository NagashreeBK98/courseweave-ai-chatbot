"""
retriever.py
------------
Simple Pinecone dense search — PLACEHOLDER implementation.

⚠️  TEAMMATE SWAP NOTICE:
This entire file is a placeholder using simple dense vector search.
Once the full RAG pipeline is ready, teammate replaces the contents
of get_relevant_courses() with the full pipeline.

The ONLY contract that must be maintained:
    Input:  query (str), student_context (dict), top_k (int)
    Output: list of dicts with keys:
            course_code, course_name, score, source, text, metadata

Everything outside get_relevant_courses() — postgres_filter,
query_builder, recommendation_agent — stays untouched.

CURRENT implementation:
    BGE-small-en-v1.5 dense embeddings → Pinecone cosine search
    → filter by eligible courses from Postgres

TEAMMATE replaces with:
    HyDE query expansion
    → Hybrid search (dense BGE + sparse BM25)
    → Cross-encoder reranking
    → MMR diversity filtering
    → Returns same output format
"""

import os
import logging
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

logger = logging.getLogger(__name__)

PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX     = os.getenv("PINECONE_INDEX_NAME")

# ============================================================================
# ⚠️  SWAP POINT 1 — Embedding Model
# Current:  BGE-small-en-v1.5 (384 dimensions, CPU)
# Teammate: Can upgrade to bge-large or add sparse encoder alongside this
# ============================================================================
def load_embedding_model():
    """Load BGE embedding model for query encoding."""
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

# Initialize once at module level — avoid reloading on every call
embedding_model = load_embedding_model()


def normalize_course_code(code: str) -> str:
    """
    Normalize course code for comparison.
    Postgres stores: "IE7275"
    Pinecone stores: "IE 7275"
    This function strips spaces for consistent comparison.
    """
    return code.replace(" ", "").upper().strip()


def format_pinecone_results(matches: list, eligible_normalized: set) -> list[dict]:
    """
    Format raw Pinecone matches into clean output dicts.
    Filters out any results not in the eligible courses list.

    Returns list of:
    {
        "course_code": "IE7275",      # normalized (no space)
        "course_name": "Data Mining in Engineering",
        "score":       0.91,
        "source":      "web_catalog",
        "text":        "IE 7275. Data Mining...",
        "metadata":    { full raw metadata dict }
    }
    """
    results = []

    for match in matches:
        meta          = match.get("metadata", {})
        raw_code      = meta.get("course_code", "")
        norm_code     = normalize_course_code(raw_code)

        # Only include courses that are in the eligible list
        if norm_code not in eligible_normalized:
            continue

        results.append({
            "course_code": norm_code,
            "course_name": meta.get("title", ""),
            "score":       round(match["score"], 4),
            "source":      meta.get("source", ""),
            "text":        meta.get("text", ""),
            "metadata":    meta,
        })

    return results


# ============================================================================
# ⚠️  SWAP POINT 2 — THE MAIN RETRIEVAL FUNCTION
#
# THIS is the function teammate replaces entirely.
# Keep the function signature identical:
#   get_relevant_courses(query, student_context, top_k) → list[dict]
#
# Current implementation:
#   1. Embed query with BGE
#   2. Query Pinecone with cosine similarity
#   3. Filter by eligible courses
#   4. Return top_k results
#
# Teammate replaces steps 1-4 with:
#   1. HyDE query expansion (generate hypothetical course description)
#   2. Dense embedding (BGE) + Sparse encoding (BM25)
#   3. Hybrid Pinecone search (dense + sparse fusion)
#   4. Cross-encoder reranking
#   5. MMR diversity filtering
#   6. Return top_k results in SAME format below
# ============================================================================
def get_relevant_courses(
    query: str,
    student_context: dict,
    top_k: int = 3
) -> list[dict]:
    """
    Retrieve relevant courses from Pinecone for a given query.

    Args:
        query:           Enriched skill query from query_builder.py
        student_context: Dict from postgres_filter.get_student_context()
                         Must contain 'eligible_courses' key
        top_k:           Number of courses to return

    Returns:
        List of course dicts sorted by relevance score descending.
        Each dict has: course_code, course_name, score, source, text, metadata
    """
    eligible_courses = student_context.get("eligible_courses", [])

    if not eligible_courses:
        logger.warning("No eligible courses for student — returning empty.")
        return []

    # Normalize eligible course codes for comparison with Pinecone metadata
    eligible_normalized = {
        normalize_course_code(c) for c in eligible_courses
    }

    # ── SWAP POINT 2a: Query embedding ──────────────────────────────────────
    # Current: BGE dense embedding only
    # Teammate adds: sparse BM25 encoding alongside this
    # ────────────────────────────────────────────────────────────────────────
    try:
        query_vector = embedding_model.embed_query(query)
    except Exception as e:
        logger.error("Embedding failed: %s", e)
        return []

    # ── SWAP POINT 2b: Pinecone query ────────────────────────────────────────
    # Current: Simple dense cosine search, top_k * 3 candidates
    # Teammate replaces with: hybrid query (dense + sparse vectors)
    # and increases candidate pool before reranking
    # ────────────────────────────────────────────────────────────────────────
    try:
        pc    = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(PINECONE_INDEX)

        raw_results = index.query(
            vector=query_vector,
            top_k=top_k * 3,      # fetch more, filter down
            include_metadata=True
        )
        matches = raw_results.get("matches", [])

    except Exception as e:
        logger.error("Pinecone query failed: %s", e)
        return []

    # ── SWAP POINT 2c: Reranking + MMR ──────────────────────────────────────
    # Current: No reranking — just cosine similarity order
    # Teammate adds:
    #   - Cross-encoder reranking (query + course text scored together)
    #   - MMR diversity (penalize overlap with completed courses)
    # ────────────────────────────────────────────────────────────────────────

    # Format and filter by eligibility
    results = format_pinecone_results(matches, eligible_normalized)

    # Return top_k after eligibility filtering
    final = results[:top_k]

    logger.info(
        "Retrieved %d courses for query: '%s...'",
        len(final), query[:50]
    )

    return final


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.abspath("."))

    logging.basicConfig(level=logging.INFO)

    from src.models.postgres_filter import get_student_context
    from src.models.query_builder import build_query

    print("\n=== Testing retriever.py ===\n")

    # Get Aisha Patel's context — MS_DAE, Data Engineer
    context = get_student_context(1)
    print(f"Student:       {context['name']}")
    print(f"Career goal:   {context['target_career']}")
    print(f"Completed:     {context['completed_courses']}")
    print(f"Eligible:      {context['eligible_courses']}")

    # Build enriched query
    query_result = build_query(context["target_career"])
    query        = query_result["skill_query"]
    print(f"\nQuery (first 100 chars): {query[:100]}...")

    # Retrieve courses
    print("\n--- Pinecone Results ---")
    courses = get_relevant_courses(query, context, top_k=3)

    if courses:
        for i, course in enumerate(courses, 1):
            print(f"\n{i}. {course['course_code']} — {course['course_name']}")
            print(f"   Score:  {course['score']}")
            print(f"   Source: {course['source']}")
            print(f"   Text:   {course['text'][:120]}...")
    else:
        print("No results returned.")