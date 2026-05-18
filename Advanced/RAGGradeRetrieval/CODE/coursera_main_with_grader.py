"""
main_with_grader.py
===================
Extends the Weaviate + text2vec-transformers RAG pipeline with a Retrieval Grader.

What is added vs original main.py:
- grade_document()      : Calls Ollama/Mistral to grade each retrieved chunk
- grade_all_results()   : Grades all retrieved docs, flags irrelevant ones
- run_rag_with_grader() : Full pipeline — retrieve → grade → pass only relevant docs forward

Grader output per document:
  - status = "Relevant"               → safe to use for generation
  - status = "Transformation Required" → irrelevant, blocked from generation

Requirements:
  - docker compose up -d              (Weaviate + text2vec-transformers)
  - ollama pull mistral               (local Mistral for grading)
  - pip install ollama
  - python main_with_grader.py
"""

from __future__ import annotations

import os
import json
import time
import ollama                          # Ollama client — calls local Mistral for grading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ---------------------------------------------------------------------------
# Config — same as original main.py
# ---------------------------------------------------------------------------

WEAVIATE_URL   = os.getenv("WEAVIATE_URL", "http://localhost:8080").rstrip("/")
WEAVIATE_CLASS = os.getenv("WEAVIATE_CLASS", "CourseDoc").strip()


# ---------------------------------------------------------------------------
# Document dataclass — same as original main.py
# ---------------------------------------------------------------------------

@dataclass
class Document:
    doc_id: str
    title: str
    text: str
    source: str = "sample"


# ---------------------------------------------------------------------------
# Sample docs — same as original main.py
# ---------------------------------------------------------------------------

SAMPLE_DOCS: List[Document] = [
    Document(
        doc_id="d1",
        title="Corrective RAG Overview",
        text=(
            "Corrective RAG (CRAG) adds a retrieval evaluator that grades retrieved documents. "
            "If context is incorrect, insufficient, or ambiguous, the system triggers corrective actions such as query rewrite "
            "or external search before generation. This prevents the model from generating from bad context."
        ),
    ),
    Document(
        doc_id="d2",
        title="Self-RAG Overview",
        text=(
            "Self-RAG validates the generated answer against retrieved sources. The model critiques its own output and checks groundedness. "
            "If unsupported by sources, it can regenerate, refuse, or tighten prompts. Self-RAG is post-generation validation."
        ),
    ),
    Document(
        doc_id="d3",
        title="Agentic RAG Pattern",
        text=(
            "Agentic RAG turns retrieval into a tool used by an agent. The agent decomposes complex queries into sub-queries, "
            "retrieves in multiple hops, and synthesizes results. This helps for multi-part questions and multi-step reasoning."
        ),
    ),
    Document(
        doc_id="d4",
        title="RAG Evaluation: The RAG Triad",
        text=(
            "RAG evaluation can measure faithfulness (answer supported by sources), answer relevance (answers the question), "
            "and context precision (retrieved documents are relevant). A/B testing compares variants on the same query set."
        ),
    ),
    Document(
        doc_id="d5",
        title="Embedding Strategy Tradeoffs",
        text=(
            "Embedding service choice involves cost, performance, and control. External APIs offer high quality but usage-based costs and limited control. "
            "Local models provide privacy and control but require infrastructure and maintenance. Evaluate end-to-end via A/B tests."
        ),
    ),
]


# ---------------------------------------------------------------------------
# HTTP helpers — same as original main.py (no changes)
# ---------------------------------------------------------------------------

def http_json(method: str, path: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Any:
    url  = f"{WEAVIATE_URL}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req  = Request(url=url, data=data, method=method.upper(),
                   headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return None if not body else json.loads(body)
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} {method} {path}: {body or e.reason}")
    except URLError as e:
        raise RuntimeError(f"Connection error calling {url}: {e}")


def wait_for_weaviate(max_wait_s: int = 60) -> None:
    start, last_err = time.time(), None
    while time.time() - start < max_wait_s:
        try:
            meta    = http_json("GET", "/v1/meta")
            version = meta.get("version")
            print(f"Weaviate is up. Version: {version}")
            return
        except Exception as e:
            last_err = e
            time.sleep(1.0)
    raise RuntimeError(f"Weaviate not reachable after {max_wait_s}s. Last error: {last_err}")


# ---------------------------------------------------------------------------
# Schema management — same as original main.py (no changes)
# ---------------------------------------------------------------------------

def class_exists(class_name: str) -> bool:
    schema  = http_json("GET", "/v1/schema")
    classes = schema.get("classes", []) if isinstance(schema, dict) else []
    return any(c.get("class") == class_name for c in classes)


def create_class_if_missing(class_name: str) -> None:
    if class_exists(class_name):
        print(f"Schema ok: class '{class_name}' already exists.")
        return
    payload = {
        "class": class_name,
        "description": "Course documents for RAG retrieval exercises",
        "vectorizer": "text2vec-transformers",
        "moduleConfig": {
            "text2vec-transformers": {"vectorizeClassName": False}
        },
        "properties": [
            {"name": "doc_id", "dataType": ["text"], "description": "Stable doc id"},
            {"name": "title",  "dataType": ["text"], "description": "Title"},
            {"name": "text",   "dataType": ["text"], "description": "Body text"},
            {"name": "source", "dataType": ["text"], "description": "Source label"},
        ],
    }
    http_json("POST", "/v1/schema", payload)
    print(f"Created schema class '{class_name}'.")


# ---------------------------------------------------------------------------
# Data loading — same as original main.py (no changes)
# ---------------------------------------------------------------------------

def count_objects(class_name: str) -> int:
    query = {"query": f"{{ Aggregate {{ {class_name} {{ meta {{ count }} }} }} }}"}
    out   = http_json("POST", "/v1/graphql", query)
    try:
        return int(out["data"]["Aggregate"][class_name][0]["meta"]["count"])
    except Exception:
        return 0


def insert_docs_if_empty(class_name: str, docs: List[Document]) -> None:
    existing = count_objects(class_name)
    if existing > 0:
        print(f"Data ok: class '{class_name}' already has {existing} objects. Skipping insert.")
        return
    print(f"Inserting {len(docs)} sample docs into '{class_name}'...")
    objects = [
        {"class": class_name,
         "properties": {"doc_id": d.doc_id, "title": d.title, "text": d.text, "source": d.source}}
        for d in docs
    ]
    resp   = http_json("POST", "/v1/batch/objects", {"objects": objects})
    errors = []
    if isinstance(resp, dict) and resp.get("errors"):
        errors.append(resp["errors"])
    if isinstance(resp, dict) and "result" in resp:
        for r in resp["result"]:
            if r.get("result", {}).get("errors"):
                errors.append(r["result"]["errors"])
    if errors:
        raise RuntimeError(f"Batch insert had errors: {json.dumps(errors)[:2000]}")
    time.sleep(0.5)
    print("Insert complete.")


# ---------------------------------------------------------------------------
# Retrieval — same as original main.py (no changes)
# ---------------------------------------------------------------------------

def near_text_search(class_name: str, query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Vector search using nearText — returns top-k docs from Weaviate."""
    safe_query = query.replace('"', '\\"')   # Escape quotes before embedding in GraphQL string
    gql = {
        "query": f"""
        {{
          Get {{
            {class_name}(
              nearText: {{ concepts: ["{safe_query}"] }}
              limit: {limit}
            ) {{
              doc_id title text source
              _additional {{ distance id }}
            }}
          }}
        }}
        """
    }
    out = http_json("POST", "/v1/graphql", gql)
    try:
        return out["data"]["Get"][class_name]   # Return list of matching doc dicts
    except Exception:
        return []                                # Return empty list on any parse failure


# ===========================================================================
# NEW: RETRIEVAL GRADER
# ===========================================================================

# System prompt used by Mistral to grade each retrieved document.
# Strict JSON-only output — same pattern as your existing guardrails pipeline.
GRADER_SYSTEM_PROMPT = (
    "You are a retrieval relevance grader.\n"
    "Given a user question and a retrieved document, decide if the document "
    "is relevant enough to help answer the question.\n"
    "Respond ONLY with valid JSON — one of:\n"
    "  {\"relevant\": true}\n"
    "  {\"relevant\": false}\n"
    "No explanation. No markdown. No extra text."
)


def grade_document(question: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grades a single retrieved Weaviate document for relevance to the question.

    Calls Mistral at temperature=0 (deterministic) — same as your guardrail graders.

    Returns the original doc dict enriched with two new keys:
      - "grade_status" : "Relevant" or "Transformation Required"
      - "grade_reason" : short explanation of the decision for user visibility
    """

    # Extract the text field from the Weaviate result dict
    # This is the body text of the retrieved document
    doc_text = doc.get("text", "")

    # Extract title for logging — helps user identify which doc was graded
    doc_title = doc.get("title", "unknown")

    print(f"\n  [Grader] Grading doc: '{doc_title}'")
    print(f"  [Grader] Chunk preview: '{doc_text[:80]}...'")

    try:
        # Call local Mistral via Ollama at temperature=0 for deterministic grading
        # temperature=0 ensures the same chunk always gets the same grade
        response = ollama.chat(
            model="mistral",                  # Local Mistral served by Ollama
            options={"temperature": 0},       # Deterministic — no randomness
            messages=[
                {
                    "role": "system",
                    "content": GRADER_SYSTEM_PROMPT   # Instruct Mistral to act as grader
                },
                {
                    "role": "user",
                    # Embed both the question and doc text so Mistral can compare them
                    "content": f"Question: {question}\n\nDocument: {doc_text}"
                }
            ]
        )

        # Extract raw text from Mistral's response
        raw = response["message"]["content"].strip()

        # Parse the JSON response — e.g. {"relevant": true}
        result = json.loads(raw)

        # Read the boolean relevance decision
        is_relevant = result.get("relevant", False)  # Default False if key missing

    except json.JSONDecodeError:
        # Mistral returned malformed JSON — known issue with stray characters
        # Safe fallback: treat as irrelevant to avoid bad context reaching generation
        print(f"  [Grader] WARNING: Mistral returned non-JSON. Treating as irrelevant.")
        is_relevant = False   # Fail safe

    except Exception as e:
        # Any other error (Ollama not running, model not pulled, etc.)
        print(f"  [Grader] ERROR calling Ollama: {e}. Treating as irrelevant.")
        is_relevant = False   # Fail safe

    # Build the grade result to attach to the doc
    if is_relevant:
        # Document passed grading — safe to use for answer generation
        grade_status = "Relevant"
        grade_reason = "Document contains information relevant to the question."
    else:
        # Document failed grading — flag it for transformation/rewrite
        # "Transformation Required" = CRAG term for docs that need corrective action
        grade_status = "Transformation Required"
        grade_reason = (
            "Document does not sufficiently address the question. "
            "Flagged for query rewrite or alternative retrieval."
        )

    # Print grade result so user can see exactly what was decided and why
    print(f"  [Grader] Grade: {grade_status}")
    print(f"  [Grader] Reason: {grade_reason}")

    # Return the original doc dict with grade metadata attached
    # Caller can filter on "grade_status" to decide what to do next
    return {
        **doc,                            # All original Weaviate fields preserved
        "grade_status": grade_status,     # "Relevant" or "Transformation Required"
        "grade_reason": grade_reason      # Human-readable reason for the grade
    }


def grade_all_results(question: str, results: List[Dict[str, Any]]) -> Dict[str, List]:
    """
    Grades ALL retrieved documents from Weaviate for a given question.

    Splits them into two buckets:
      - relevant_docs   : passed grading → safe for generation
      - flagged_docs    : failed grading → "Transformation Required"

    Returns a dict with both buckets so the caller can handle each appropriately.
    """

    relevant_docs = []   # Will hold docs that passed the grader
    flagged_docs  = []   # Will hold docs flagged as "Transformation Required"

    print(f"\n{'=' * 60}")
    print(f"  RETRIEVAL GRADER — Grading {len(results)} retrieved docs")
    print(f"  Question: '{question}'")
    print(f"{'=' * 60}")

    # Grade each retrieved document one by one
    for i, doc in enumerate(results):

        print(f"\n  --- Document {i + 1} of {len(results)} ---")

        # Call grader — returns doc dict with grade_status and grade_reason added
        graded_doc = grade_document(question, doc)

        # Route the graded doc into the correct bucket based on grade_status
        if graded_doc["grade_status"] == "Relevant":
            relevant_docs.append(graded_doc)   # Safe to use for generation
        else:
            flagged_docs.append(graded_doc)    # Blocked — needs corrective action

    # Print summary so user can see overall grading outcome
    print(f"\n{'=' * 60}")
    print(f"  GRADING COMPLETE")
    print(f"  Relevant docs           : {len(relevant_docs)}")
    print(f"  Transformation Required : {len(flagged_docs)}")
    print(f"{'=' * 60}")

    # If any docs were flagged, show user what will happen to them
    if flagged_docs:
        print(f"\n  [Pipeline] The following docs were BLOCKED from generation:")
        for d in flagged_docs:
            print(f"    - [{d.get('doc_id')}] {d.get('title')} → {d['grade_status']}")
        print(f"\n  [Pipeline] In production: flagged docs trigger query rewrite")
        print(f"             or web search fallback before re-retrieval.")

    # If no docs passed, warn the user clearly
    if not relevant_docs:
        print(f"\n  [Pipeline] WARNING: ZERO docs passed grading for this query.")
        print(f"  [Pipeline] Generation will NOT proceed with current context.")
        print(f"  [Pipeline] Corrective action required: rewrite query or expand corpus.")

    return {
        "relevant": relevant_docs,   # Ready for generation
        "flagged":  flagged_docs     # Needs corrective action
    }


# ---------------------------------------------------------------------------
# Full RAG pipeline with grader integrated
# ---------------------------------------------------------------------------

def run_rag_with_grader(class_name: str, question: str, limit: int = 3) -> None:
    """
    Full pipeline:
      1. Retrieve top-k docs from Weaviate using nearText (vector search)
      2. Grade each doc for relevance using Mistral
      3. Pass ONLY relevant docs forward to generation
      4. Block flagged docs and explain what corrective action would follow
    """

    print(f"\n{'#' * 60}")
    print(f"  RAG PIPELINE WITH RETRIEVAL GRADER")
    print(f"  Question: {question}")
    print(f"{'#' * 60}")

    # --- Step 1: Retrieve from Weaviate ---
    print(f"\n  [Retrieval] Running nearText search in Weaviate...")
    results = near_text_search(class_name, question, limit=limit)
    print(f"  [Retrieval] Retrieved {len(results)} docs from Weaviate.")

    # If Weaviate returned nothing at all, stop early
    if not results:
        print("  [Pipeline] No docs retrieved from Weaviate. Check your corpus.")
        return

    # --- Step 2: Grade all retrieved docs ---
    # grade_all_results splits docs into relevant vs flagged buckets
    graded = grade_all_results(question, results)

    relevant_docs = graded["relevant"]   # Passed grading
    flagged_docs  = graded["flagged"]    # Failed grading — "Transformation Required"

    # --- Step 3: Use only relevant docs for generation ---
    if not relevant_docs:
        # No relevant docs — in real pipeline this triggers CRAG query rewrite
        print(f"\n  [Pipeline] No relevant docs — generation SKIPPED.")
        print(f"  [Pipeline] Next step in CRAG: rewrite query and re-retrieve.")
        return

    # Build the grounded context from relevant docs only
    # Irrelevant/flagged docs are completely excluded from this context
    context = "\n\n".join(
        f"[{d.get('doc_id')}] {d.get('title')}:\n{d.get('text', '')}"
        for d in relevant_docs
    )

    print(f"\n  [Generation] Generating answer from {len(relevant_docs)} relevant doc(s)...")

    # Call Mistral for final answer generation using only graded, relevant context
    response = ollama.chat(
        model="mistral",
        options={"temperature": 0.3},   # Slight creativity for generation (not grading)
        messages=[
            {
                "role": "system",
                # Restrict Mistral to only use the provided context — no hallucination
                "content": "Answer the question using ONLY the provided context. Do not use outside knowledge."
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
    )

    # Extract the final generated answer
    answer = response["message"]["content"].strip()

    # Print the final answer clearly
    print(f"\n{'=' * 60}")
    print(f"  FINAL ANSWER")
    print(f"{'=' * 60}")
    print(f"  {answer}")
    print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"WEAVIATE_URL={WEAVIATE_URL}")
    print(f"WEAVIATE_CLASS={WEAVIATE_CLASS}")

    # Wait for Weaviate to be ready (same as original main.py)
    wait_for_weaviate(max_wait_s=60)

    # Create schema if missing (same as original main.py)
    create_class_if_missing(WEAVIATE_CLASS)

    # Insert sample docs if collection is empty (same as original main.py)
    insert_docs_if_empty(WEAVIATE_CLASS, SAMPLE_DOCS)

    # Demo queries — same as original main.py, now with grader in the pipeline
    demo_queries = [
        "What is the difference between Corrective RAG and Self-RAG?",
        "How do you evaluate a RAG pipeline?",
        "What is Agentic RAG and why is it useful?",
        "How do you choose an embedding service?",
    ]

    # Run the full RAG pipeline with grader for each demo query
    for q in demo_queries:
        run_rag_with_grader(WEAVIATE_CLASS, q, limit=3)

    # Optional interactive mode — same as original main.py
    print("\nType a query (or press Enter to exit):")
    while True:
        try:
            q = input("> ").strip()
        except EOFError:
            break
        if not q:
            break
        run_rag_with_grader(WEAVIATE_CLASS, q, limit=5)


if __name__ == "__main__":
    main()
