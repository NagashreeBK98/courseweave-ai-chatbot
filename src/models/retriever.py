"""
retriever.py
------------
CourseWeave.ai — Full RAG Retrieval Pipeline

Merged from:
    - rag_pipeline.py ( query rewriting, HyDE, hybrid search,
                       RRF fusion, cross-encoder reranking, MMR)
    - retriever.py    ( double guardrail fix, completed_courses check,
                       google-genai SDK, real Postgres test block)

Fixes applied (v3):
    - sparse_search: logs warning + returns [] gracefully when index
      does not support dotproduct (cosine index workaround)
    - rerank_candidates: `or ""` guard on metadata text to prevent
      NoneType errors in cross-encoder pairs
    - run_context_assembly: fallback to deduped order if MMR returns empty

Contract (unchanged):
    Input:  query (str), student_context (dict), top_k (int)
    Output: list of dicts with keys:
            course_code, course_name, score, source, text, metadata

Pipeline:
    1. Query rewriting + HyDE          
    2. Metadata pre-filter             
    3. Hybrid retrieval (dense+sparse) (sparse skipped if unsupported)
    4. RRF fusion                      
    5. Cross-encoder re-ranking        
    6. Context assembly + MMR          
    7. Guardrails + format             (merged: eligible + completed check)
"""

import os
import logging
import numpy as np
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from pinecone_text.sparse import BM25Encoder
from sentence_transformers import CrossEncoder
from google import genai

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
GCP_PROJECT_ID      = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION        = os.getenv("GCP_LOCATION", "us-central1")

EMBEDDING_MODEL_NAME   = "BAAI/bge-small-en-v1.5"
CROSS_ENCODER_MODEL    = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_SCORE_THRESHOLD = 0.0
CANDIDATE_POOL         = 20

logger = logging.getLogger(__name__)


# ============================================================
# MODEL & CLIENT INITIALIZATION
# ============================================================

def _init_embedding_model():
    logger.info("Loading BGE embedding model...")
    model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    logger.info("BGE embedding model loaded")
    return model


def _init_pinecone():
    logger.info("Connecting to Pinecone index: %s", PINECONE_INDEX_NAME)
    pc  = Pinecone(api_key=PINECONE_API_KEY)
    idx = pc.Index(PINECONE_INDEX_NAME)
    logger.info("Pinecone connected")
    return pc, idx


def _init_bm25(index):
    """
    Fetch corpus from Pinecone and fit BM25 encoder.
    BM25 is used for sparse scoring — falls back gracefully if
    Pinecone index does not support dotproduct (sparse) queries.
    Runs once at module load.
    """
    encoder = BM25Encoder()
    logger.info("Fetching corpus from Pinecone for BM25 fitting...")
    corpus_texts = []

    try:
        for id_batch in index.list(limit=99):
            fetch_response = index.fetch(ids=id_batch)
            for vid, vec in fetch_response.vectors.items():
                text = vec.metadata.get("text", "") if vec.metadata else ""
                if text and isinstance(text, str) and text.strip():
                    corpus_texts.append(text.strip())

        if not corpus_texts:
            raise ValueError("Corpus is empty — no text found in Pinecone metadata.")

        logger.info("Fetched %d documents — fitting BM25...", len(corpus_texts))
        encoder.fit(corpus_texts)
        logger.info("BM25 encoder fitted successfully")

    except Exception as e:
        logger.error("BM25 init failed: %s", e)
        raise

    return encoder


def _init_cross_encoder():
    logger.info("Loading cross-encoder reranker...")
    model = CrossEncoder(CROSS_ENCODER_MODEL)
    logger.info("Cross-encoder loaded")
    return model


def _init_gemini():
    """
    Initialize Gemini client using google-genai SDK with Vertex AI.
    Uses Application Default Credentials locally.
    On GCP infrastructure, uses metadata server automatically.
    """
    logger.info("Initializing Gemini 2.5 Flash via Vertex AI...")
    client = genai.Client(
        vertexai=True,
        project=GCP_PROJECT_ID,
        location=GCP_LOCATION
    )
    logger.info("Gemini 2.5 Flash ready")
    return client


# Initialize all models and clients once at module load
embedding_model = _init_embedding_model()
pc, index       = _init_pinecone()
bm25_encoder    = _init_bm25(index)
cross_encoder   = _init_cross_encoder()
gemini_client   = _init_gemini()

logger.info("All models and clients initialized — pipeline ready")


# ============================================================
# STEP 1 — QUERY LAYER (teammate)
# ============================================================

def rewrite_query(query: str) -> str:
    """
    Use Gemini to rewrite the user query into retrieval-friendly language.
    Converts conversational phrasing into vocabulary closer to course descriptions.
    Falls back to original query if Gemini call fails.
    """
    prompt = f"""You are helping a university course recommendation system.
Rewrite the following student query into clear, academic language that would
match university course catalog descriptions. Return only the rewritten query,
nothing else.

Student query: {query}
Rewritten query:"""

    try:
        response  = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        rewritten = response.text.strip()
        logger.info("Query rewritten: '%s' → '%s'", query[:60], rewritten[:60])
        return rewritten
    except Exception as e:
        logger.warning("Query rewriting failed, using original: %s", e)
        return query


def generate_hyde_vector(query: str) -> list:
    """
    HyDE: Generate a hypothetical course description for the query,
    then embed it. The hypothesis lives closer to real course chunks
    in embedding space than the raw question does.
    Falls back to direct embedding if Gemini call fails.
    """
    prompt = f"""Write a generic university course description (2-3 sentences)
that would be highly relevant to a student interested in: {query}

Return only the course description text, nothing else."""

    try:
        response    = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        hypothesis  = response.text.strip()
        hyde_vector = embedding_model.embed_query(hypothesis)
        logger.info("HyDE hypothesis generated (%d chars)", len(hypothesis))
        return hyde_vector
    except Exception as e:
        logger.warning("HyDE generation failed, falling back to direct embedding: %s", e)
        return embedding_model.embed_query(query)


def run_query_layer(query: str) -> dict:
    """Run the full query layer. Returns original_query, rewritten_query, hyde_vector."""
    rewritten_query = rewrite_query(query)
    hyde_vector     = generate_hyde_vector(rewritten_query)

    return {
        "original_query" : query,
        "rewritten_query": rewritten_query,
        "hyde_vector"    : hyde_vector
    }


# ============================================================
# STEP 2 — METADATA PRE-FILTER (teammate)
# ============================================================

def build_pinecone_filter(student_context: dict) -> dict:
    """
    Build a Pinecone metadata pre-filter from student context.
    Filters by department when eligible course set is narrow enough.
    Eligibility filtering is handled post-retrieval in guardrails.
    """
    pinecone_filter  = {}
    eligible_courses = student_context.get("eligible_courses", [])

    departments = set()
    for code in eligible_courses:
        normalized = code.replace(" ", "").upper()
        dept = ''.join(filter(str.isalpha, normalized))
        if dept:
            departments.add(dept)

    if len(departments) == 1:
        pinecone_filter["department"] = {"$eq": list(departments)[0]}
        logger.info("Pre-filter: department = %s", list(departments)[0])
    elif len(departments) <= 3:
        pinecone_filter["department"] = {"$in": list(departments)}
        logger.info("Pre-filter: departments in %s", list(departments))
    else:
        logger.info("Pre-filter: skipped — too many departments (%d)", len(departments))

    return pinecone_filter


# ============================================================
# STEPS 3 & 4 — HYBRID RETRIEVAL + RRF FUSION (teammate)
# ============================================================

def dense_search(hyde_vector: list, pinecone_filter: dict, top_k: int) -> list:
    """Dense vector search using HyDE-generated vector."""
    query_params = {
        "vector"          : hyde_vector,
        "top_k"           : top_k,
        "include_metadata": True
    }
    if pinecone_filter:
        query_params["filter"] = pinecone_filter

    try:
        response = index.query(**query_params)
        matches = response.get("matches", [])
        return [
            {
                "id":       m["id"],
                "score":    m["score"],
                "metadata": m.get("metadata", {}) or {}
            }
        for m in matches
        ]
    except Exception as e:
        logger.error("Dense search failed: %s", e)
        return []


def sparse_search(rewritten_query: str, pinecone_filter: dict, top_k: int) -> list:
    """
    Sparse BM25 search using Pinecone native sparse vectors.
    Uses zero dense vector to isolate sparse signal.

    FIX: Returns [] gracefully when Pinecone index uses cosine metric
    instead of dotproduct. Sparse vectors require dotproduct index.
    Pipeline continues with dense-only results via RRF fallback.
    """
    try:
        sparse_vector = bm25_encoder.encode_queries(rewritten_query)
    except Exception as e:
        logger.warning("BM25 encoding failed — skipping sparse search: %s", e)
        return []

    zero_dense_vector = [0.0] * 384

    query_params = {
        "vector"          : zero_dense_vector,
        "sparse_vector"   : sparse_vector,
        "top_k"           : top_k,
        "include_metadata": True
    }
    if pinecone_filter:
        query_params["filter"] = pinecone_filter

    try:
        response = index.query(**query_params)
        return [
            {
                "id":       m["id"],
                "score":    m["score"],
                "metadata": m.get("metadata", {}) or {}
            }
        for m in matches
        ]
    except Exception as e:
        # FIX: Downgrade to WARNING not ERROR — this is expected when
        # index uses cosine metric. Pipeline continues with dense-only.
        logger.warning(
            "Sparse search unavailable (index may use cosine not dotproduct) "
            "— continuing with dense-only retrieval: %s", e
        )
        return []


def rrf_fusion(dense_matches: list, sparse_matches: list, k: int = 60) -> list:
    """
    Reciprocal Rank Fusion — merges dense and sparse ranked lists.
    score(doc) = 1/(k + rank_dense) + 1/(k + rank_sparse)
    k=60 is the standard default from the original RRF paper.

    Works correctly with sparse_matches=[] — just returns dense ranking.
    """
    rrf_scores = {}

    for rank, match in enumerate(dense_matches):
        mid = match["id"]
        rrf_scores.setdefault(mid, {"score": 0.0, "match": match})
        rrf_scores[mid]["score"] += 1.0 / (k + rank + 1)

    for rank, match in enumerate(sparse_matches):
        mid = match["id"]
        rrf_scores.setdefault(mid, {"score": 0.0, "match": match})
        rrf_scores[mid]["score"] += 1.0 / (k + rank + 1)

    fused = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)

    results = []
    for item in fused:
        m = item["match"].copy()
        m["rrf_score"] = round(item["score"], 6)
        results.append(m)

    return results


def run_hybrid_retrieval(
    query_output: dict,
    pinecone_filter: dict,
    candidate_pool: int = CANDIDATE_POOL
) -> list:
    """
    Run dense + sparse retrieval and fuse with RRF.
    If sparse returns empty (cosine index), RRF gracefully uses dense only.
    """
    rewritten_query = query_output["rewritten_query"]
    hyde_vector     = query_output["hyde_vector"]

    dense_matches  = dense_search(hyde_vector, pinecone_filter, top_k=candidate_pool)
    sparse_matches = sparse_search(rewritten_query, pinecone_filter, top_k=candidate_pool)

    logger.info("Dense: %d | Sparse: %d", len(dense_matches), len(sparse_matches))

    if not dense_matches and not sparse_matches:
        logger.warning("Both dense and sparse returned empty — no candidates.")
        return []

    fused = rrf_fusion(dense_matches, sparse_matches)
    logger.info("Fused candidates after RRF: %d", len(fused))
    return fused


# ============================================================
# STEP 5 — CROSS-ENCODER RE-RANKING (teammate + NoneType fix)
# ============================================================

def rerank_candidates(
    rewritten_query: str,
    candidates: list,
    score_threshold: float = RERANK_SCORE_THRESHOLD
) -> list:
    """
    Re-rank candidates using cross-encoder.
    Falls back to RRF order if reranking fails.

    FIX: Added `or ""` guard on metadata text to prevent NoneType
    errors when course metadata has null/missing text field.
    """
    if not candidates:
        return []

    # FIX: `or ""` prevents NoneType being passed to cross-encoder
    pairs = [
        [rewritten_query, c.get("metadata", {}).get("text", "") or ""]
        for c in candidates
    ]

    try:
        scores = cross_encoder.predict(pairs)
    except Exception as e:
        logger.error("Cross-encoder scoring failed, using RRF order: %s", e)
        return candidates

    scored = []
    for candidate, score in zip(candidates, scores):
        if score >= score_threshold:
            c = candidate.copy()
            c["rerank_score"] = round(float(score), 4)
            scored.append(c)

    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    logger.info(
        "Re-ranking: %d → %d passed threshold (%.2f)",
        len(candidates), len(scored), score_threshold
    )
    return scored


# ============================================================
# STEP 6 — CONTEXT ASSEMBLY + MMR DIVERSITY (teammate)
# ============================================================

def fetch_parent_chunk(course_code: str) -> str:
    """For PDF chunks, fetch sibling chunks and merge for richer context."""
    try:
        parent_ids = [
            f"pdf_{course_code.replace(' ', '_')}_chunk_{i}"
            for i in range(3)
        ]
        fetch_response = index.fetch(ids=parent_ids)
        vectors = fetch_response.vectors if hasattr(fetch_response, "vectors") else {}

        if not vectors:
            return ""

        chunks = sorted(
            vectors.values(),
            key=lambda v: v.get("metadata", {}).get("chunk_index", 0)
        )
        merged = "\n\n".join(
            c.get("metadata", {}).get("text", "")
            for c in chunks
            if c.get("metadata", {}).get("text")
        )
        return merged
    except Exception as e:
        logger.warning("Parent chunk fetch failed for %s: %s", course_code, e)
        return ""


def deduplicate_candidates(candidates: list) -> list:
    """Keep highest-scoring chunk per course_code."""
    seen = {}
    for c in candidates:
        code = c.get("metadata", {}).get("course_code", c["id"])
        if code not in seen:
            seen[code] = c
    return list(seen.values())


def compute_text_similarity(text1: str, text2: str) -> float:
    """Jaccard token overlap similarity — lightweight, no extra model needed."""
    set1 = set((text1 or "").lower().split())
    set2 = set((text2 or "").lower().split())
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


def mmr_diversity(
    candidates: list,
    completed_courses: list,
    top_k: int,
    lambda_param: float = 0.7
) -> list:
    """
    Maximal Marginal Relevance diversity filtering.
    Balances relevance vs diversity, penalizing overlap with
    already-selected results AND completed courses from Postgres.

    lambda_param: 1.0 = pure relevance, 0.0 = pure diversity.
    """
    if not candidates:
        return []

    completed_texts = []
    for code in completed_courses:
        norm = code.replace(" ", "").upper()
        for c in candidates:
            c_code = c.get("metadata", {}).get("course_code", "").replace(" ", "").upper()
            if c_code == norm:
                completed_texts.append(c.get("metadata", {}).get("text", "") or "")

    selected  = []
    remaining = candidates.copy()

    while remaining and len(selected) < top_k:
        best_score = -np.inf
        best_idx   = 0

        for i, candidate in enumerate(remaining):
            cand_text = candidate.get("metadata", {}).get("text", "") or ""
            relevance = candidate.get("rerank_score", 0.0)

            sim_selected = max(
                (compute_text_similarity(cand_text, s.get("metadata", {}).get("text", "") or "")
                 for s in selected),
                default=0.0
            )
            sim_completed = max(
                (compute_text_similarity(cand_text, t) for t in completed_texts),
                default=0.0
            )

            mmr_score = (
                (lambda_param * relevance) -
                ((1 - lambda_param) * max(sim_selected, sim_completed))
            )

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx   = i

        selected.append(remaining.pop(best_idx))

    logger.info("MMR selected %d diverse candidates from %d", len(selected), len(candidates))
    return selected


def run_context_assembly(reranked: list, student_context: dict, top_k: int) -> list:
    """
    Full context assembly:
    1. Enrich PDF chunks with parent context
    2. Deduplicate (one chunk per course)
    3. MMR diversity filtering using completed_courses from Postgres

    FIX: If MMR returns empty (edge case with all zero scores),
    falls back to deduped order to ensure pipeline always returns results.
    """
    completed_courses = student_context.get("completed_courses", [])

    enriched = []
    for c in reranked:
        source      = c.get("metadata", {}).get("source", "")
        course_code = c.get("metadata", {}).get("course_code", "")
        c = c.copy()

        if source == "pdf" and course_code:
            parent_text = fetch_parent_chunk(course_code)
            if parent_text:
                c["metadata"] = c.get("metadata", {}).copy()
                c["metadata"]["text"] = parent_text

        enriched.append(c)

    deduped = deduplicate_candidates(enriched)
    logger.info("After dedup: %d candidates", len(deduped))

    diverse = mmr_diversity(deduped, completed_courses, top_k=top_k)

    # FIX: fallback if MMR returns empty
    if not diverse and deduped:
        logger.warning("MMR returned empty — falling back to deduped order")
        diverse = deduped[:top_k]

    return diverse


# ============================================================
# STEP 7 — GUARDRAILS (merged: teammate + our completed check)
# ============================================================

def normalize_course_code(code: str) -> str:
    """Normalize course code — no space, uppercase."""
    return code.replace(" ", "").upper().strip()


def apply_guardrails(
    assembled: list,
    student_context: dict,
    top_k: int
) -> list:
    """
    Final guardrails before returning results.

    Two checks (merged from both sides):
    1. Eligibility filter — course must be in eligible_courses from Postgres
    2. Completed check   — course must NOT be in completed_courses (hard guardrail)

    Also normalizes course codes and formats output to match contract.
    """
    eligible_courses    = student_context.get("eligible_courses", [])
    completed_courses   = student_context.get("completed_courses", [])

    eligible_normalized  = {normalize_course_code(c) for c in eligible_courses}
    completed_normalized = {normalize_course_code(c) for c in completed_courses}

    final_results = []

    for item in assembled:
        meta      = item.get("metadata", {})
        raw_code  = meta.get("course_code", "")
        norm_code = normalize_course_code(raw_code)

        # Guardrail 1: must be in eligible courses
        if norm_code not in eligible_normalized:
            logger.debug("Dropping %s — not in eligible courses", norm_code)
            continue

        # Guardrail 2: must NOT be completed (hard stop)
        if norm_code in completed_normalized:
            logger.warning(
                "Guardrail triggered: %s is completed but appeared in results",
                norm_code
            )
            continue

        final_results.append({
            "course_code": norm_code,
            "course_name": meta.get("title", ""),
            "score"      : round(item.get("rerank_score", item.get("rrf_score", 0.0)), 4),
            "source"     : meta.get("source", ""),
            "text"       : meta.get("text", "") or "",
            "metadata"   : meta
        })

    final_results = final_results[:top_k]

    if final_results and final_results[0]["score"] < 0.1:
        logger.warning(
            "Top result score is very low (%.4f) — retrieval quality may be poor.",
            final_results[0]["score"]
        )

    if not final_results:
        logger.warning("No results passed guardrails — returning empty list.")

    logger.info("Guardrails: %d results passed for top_k=%d", len(final_results), top_k)
    return final_results


# ============================================================
# MAIN INTEGRATION FUNCTION
# ============================================================

def get_relevant_courses(
    query:           str,
    student_context: dict,
    top_k:           int = 3
) -> list[dict]:
    """
    Full RAG retrieval pipeline.

    Contract (unchanged):
        Input:  query (str), student_context (dict), top_k (int)
        Output: list of dicts with keys:
                course_code, course_name, score, source, text, metadata

    Pipeline:
        1. Query rewriting + HyDE
        2. Metadata pre-filter
        3. Hybrid retrieval (dense + sparse, sparse gracefully skipped if unsupported)
        4. RRF fusion
        5. Cross-encoder re-ranking
        6. Context assembly + MMR diversity
        7. Guardrails (eligible + completed check)
    """
    eligible_courses = student_context.get("eligible_courses", [])

    if not eligible_courses:
        logger.warning("No eligible courses in student_context — returning empty.")
        return []

    try:
        query_output     = run_query_layer(query)
        pinecone_filter  = build_pinecone_filter(student_context)
        fused_candidates = run_hybrid_retrieval(
            query_output, pinecone_filter, candidate_pool=CANDIDATE_POOL
        )

        if not fused_candidates:
            logger.warning("No candidates returned from retrieval.")
            return []

        reranked  = rerank_candidates(query_output["rewritten_query"], fused_candidates)
        assembled = run_context_assembly(reranked, student_context, top_k=top_k * 2)
        final     = apply_guardrails(assembled, student_context, top_k=top_k)

        logger.info(
            "Pipeline complete — %d results for query: '%s...'",
            len(final), query[:50]
        )
        return final

    except Exception as e:
        import traceback
        logger.error("Pipeline failed for query '%s': %s\n%s", query[:50], e, traceback.format_exc())
        return []


# ============================================================
# TEST BLOCK — uses real Postgres data
# ============================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    logging.basicConfig(level=logging.INFO)

    from src.models.postgres_filter import get_student_context
    from src.models.query_builder import build_query

    print("\n=== Testing retriever.py (full RAG pipeline) ===\n")

    # Aisha Patel — MS_DAE, Data Engineer
    context = get_student_context(1)
    print(f"Student:    {context['name']}")
    print(f"Career:     {context['target_career']}")
    print(f"Completed:  {context['completed_courses']}")
    print(f"Eligible:   {context['eligible_courses']}")

    query_result = build_query(context["target_career"])
    query        = query_result["skill_query"]
    print(f"\nQuery: {query[:100]}...\n")

    results = get_relevant_courses(query, context, top_k=3)

    if results:
        print(f"\n--- Top {len(results)} Results ---")
        for i, course in enumerate(results, 1):
            print(f"\n{i}. {course['course_code']} — {course['course_name']}")
            print(f"   Score:  {course['score']}")
            print(f"   Source: {course['source']}")
            print(f"   Text:   {course['text'][:120]}...")
    else:
        print("No results returned — check logs above.")