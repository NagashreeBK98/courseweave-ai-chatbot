"""
CourseWeave.ai - PDF Data Extraction Pipeline
GCS PDFs → Semantic Chunking → Pinecone

Production-ready script for Apache Airflow DAG integration.
- Checksum-based deduplication via GCS tracker
- Structured error logging to GCS
- Semantic chunking with metadata tagging
- Upsert to Pinecone vector store
"""

import os
import re
import json
import hashlib
import fitz
from datetime import datetime, timezone
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from google.cloud import storage


# ============================================================================
# CONFIGURATION
# ============================================================================

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_FOLDER = os.getenv("GCS_FOLDER")
GCS_TRACKER_PATH = os.getenv("GCS_TRACKER_PATH")
GCS_ERROR_LOG_FOLDER = "error_logs"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

gcs_client = storage.Client()
bucket = gcs_client.bucket(GCS_BUCKET)


# ============================================================================
# ERROR LOGGING
# ============================================================================

def log_error_to_gcs(source_file, stage, error_message):
    """Log structured error to GCS as a JSON file."""
    timestamp = datetime.now(timezone.utc).isoformat()
    error_obj = {
        "source_file": source_file,
        "stage": stage,
        "error_message": str(error_message),
        "timestamp": timestamp
    }
    safe_name = re.sub(r"[^\w\-.]", "_", source_file)
    filename = f"{GCS_ERROR_LOG_FOLDER}/pdf_{safe_name}_{timestamp}.json"
    blob = bucket.blob(filename)
    blob.upload_from_string(json.dumps(error_obj, indent=2), content_type="application/json")


# ============================================================================
# TRACKER FUNCTIONS
# ============================================================================

def load_tracker():
    """Load the processed files tracker from GCS."""
    blob = bucket.blob(GCS_TRACKER_PATH)
    if blob.exists():
        data = blob.download_as_text()
        return json.loads(data)
    return {}


def save_tracker(tracker):
    """Save the processed files tracker to GCS."""
    blob = bucket.blob(GCS_TRACKER_PATH)
    blob.upload_from_string(json.dumps(tracker, indent=2), content_type="application/json")


# ============================================================================
# PDF LOADING FUNCTIONS
# ============================================================================

def load_and_merge_pdf_from_stream(blob_data, blob_name):
    """
    Load a PDF from bytes stream and merge all pages into a single Document.
    Each PDF = one course, so we combine all pages.
    """
    pdf_document = fitz.open(stream=blob_data, filetype="pdf")

    if pdf_document.page_count == 0:
        pdf_document.close()
        return None

    pages = []
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        pages.append(page.get_text())

    pdf_document.close()
    merged_content = "\n\n".join(pages)

    return Document(
        page_content=merged_content,
        metadata={"source_file": blob_name}
    )


def extract_course_code(text):
    """
    Extract course code (e.g., INFO 5100) from PDF content.
    Looks for patterns like 'DEPT 1234' in the first 500 chars.
    """
    header_text = text[:500]
    match = re.match(r".*?([A-Z]{2,5}\s\d{4})", header_text, re.DOTALL)
    if match:
        return match.group(1)
    return None


# ============================================================================
# ID GENERATION
# ============================================================================

def prepare_pdf_ids(chunks):
    """Generate deterministic IDs for PDF chunks."""
    ids = []
    for chunk in chunks:
        code = chunk.metadata.get("course_code", "UNKNOWN").replace(" ", "_")
        idx = chunk.metadata.get("chunk_index", 0)
        ids.append(f"pdf_{code}_chunk_{idx}")
    return ids


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_pipeline():
    """Main pipeline execution."""

    # Initialize embedding model
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    pc.Index(PINECONE_INDEX_NAME)

    # Initialize semantic chunker
    semantic_chunker = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=85
    )

    # Load tracker
    tracker = load_tracker()

    # List PDFs from GCS
    try:
        prefix = f"{GCS_FOLDER}/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        pdf_blobs = [b for b in blobs if b.name.lower().endswith(".pdf")]
    except Exception as e:
        log_error_to_gcs("GLOBAL", "gcs_list_blobs", e)
        raise

    pipeline_results = {"success": [], "failed": [], "skipped": []}

    for blob in pdf_blobs:
        blob_name = blob.name

        # Stage 1: Download and checksum
        try:
            blob_data = blob.download_as_bytes()
            checksum = hashlib.md5(blob_data).hexdigest()
        except Exception as e:
            log_error_to_gcs(blob_name, "gcs_download", e)
            pipeline_results["failed"].append(blob_name)
            continue

        # Stage 2: Check tracker for deduplication
        if blob_name in tracker and tracker[blob_name]["checksum"] == checksum:
            pipeline_results["skipped"].append(blob_name)
            continue

        # Stage 3: Parse PDF
        try:
            doc = load_and_merge_pdf_from_stream(blob_data, blob_name)
            if not doc:
                log_error_to_gcs(blob_name, "pdf_parsing", "No content extracted from PDF")
                pipeline_results["failed"].append(blob_name)
                continue
            doc.metadata["checksum"] = checksum
        except Exception as e:
            log_error_to_gcs(blob_name, "pdf_parsing", e)
            pipeline_results["failed"].append(blob_name)
            continue

        # Stage 4: Extract course code
        try:
            code = extract_course_code(doc.page_content)
            if not code:
                log_error_to_gcs(blob_name, "course_code_extraction", "Could not extract course code")
                pipeline_results["failed"].append(blob_name)
                continue
            doc.metadata["course_code"] = code
            doc.metadata["department"] = code.split()[0]
        except Exception as e:
            log_error_to_gcs(blob_name, "course_code_extraction", e)
            pipeline_results["failed"].append(blob_name)
            continue

        # Stage 5: Semantic chunking
        try:
            chunks = semantic_chunker.split_documents([doc])
            for i, chunk in enumerate(chunks):
                chunk.metadata["course_code"] = doc.metadata["course_code"]
                chunk.metadata["department"] = doc.metadata["department"]
                chunk.metadata["source"] = "pdf"
                chunk.metadata["source_file"] = doc.metadata["source_file"]
                chunk.metadata["checksum"] = doc.metadata["checksum"]
                chunk.metadata["chunk_index"] = i
        except Exception as e:
            log_error_to_gcs(blob_name, "semantic_chunking", e)
            pipeline_results["failed"].append(blob_name)
            continue

        # Stage 6: Upsert to Pinecone
        try:
            chunk_ids = prepare_pdf_ids(chunks)
            PineconeVectorStore.from_documents(
                documents=chunks,
                embedding=embeddings,
                index_name=PINECONE_INDEX_NAME,
                ids=chunk_ids
            )
        except Exception as e:
            log_error_to_gcs(blob_name, "pinecone_upsert", e)
            pipeline_results["failed"].append(blob_name)
            continue

        # Stage 7: Update tracker
        try:
            tracker[blob_name] = {
                "checksum": checksum,
                "processed_date": datetime.now(timezone.utc).isoformat(),
                "course_code": doc.metadata["course_code"],
                "chunks_created": len(chunks)
            }
            save_tracker(tracker)
        except Exception as e:
            log_error_to_gcs(blob_name, "tracker_update", e)

        pipeline_results["success"].append({
            "source_file": blob_name,
            "course_code": doc.metadata["course_code"],
            "chunks": len(chunks)
        })

    # Write pipeline summary
    summary = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_pdfs_found": len(pdf_blobs),
        "successful": len(pipeline_results["success"]),
        "skipped": len(pipeline_results["skipped"]),
        "failed": len(pipeline_results["failed"]),
        "details": pipeline_results
    }

    summary_blob = bucket.blob(
        f"pdf_output/pipeline_summary_{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}.json"
    )
    summary_blob.upload_from_string(json.dumps(summary, indent=2), content_type="application/json")

    return summary


if __name__ == "__main__":
    result = run_pipeline()
    print(json.dumps(result, indent=2))