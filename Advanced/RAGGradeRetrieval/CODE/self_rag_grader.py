"""
crag_self_rag_ollama.py
=======================
Demonstrates Corrective RAG (CRAG) and Self-RAG using Ollama (Mistral model).
Each technique adds a grading feedback loop on top of standard RAG.

Run:
    pip install ollama
    ollama pull mistral
    python crag_self_rag_ollama.py
"""

import ollama  # Ollama Python client — calls local Mistral model
import json    # For parsing deterministic JSON responses from the grader LLM


# =============================================================================
# SHARED UTILITY: show_user_action()
# =============================================================================

def show_user_action(step: str, detail: str):
    """
    Prints a clear, formatted message to the user explaining exactly what
    the system is doing and why — especially when grading fails or fallbacks trigger.

    :param step:   Short label like "[CRAG] Grading" shown as a category
    :param detail: Human-readable explanation of the action being taken
    """
    # Print a separator line so each action is visually distinct in the console
    print("\n" + "=" * 60)

    # Print the step label (e.g. "[CRAG] Grading Doc") in uppercase for visibility
    print(f"  ACTION  >>  {step.upper()}")

    # Print the detailed explanation so the user knows WHY this is happening
    print(f"  DETAIL  >>  {detail}")

    # Print closing separator
    print("=" * 60)


# =============================================================================
# SECTION 1: CORRECTIVE RAG (CRAG)
# =============================================================================
# CRAG flow:
#   retrieve docs → grade each doc → keep relevant → generate answer
#   if no relevant docs → rewrite query → re-retrieve → generate answer


# --- CRAG Step 1: Grade a single retrieved chunk for relevance ---

def crag_grade_document(question: str, chunk: str) -> bool:
    """
    Calls Mistral at temperature=0 (deterministic) to decide if a retrieved
    chunk is relevant to the user's question.

    Returns True if relevant, False if not.
    """

    # System prompt instructs Mistral to act as a strict relevance grader.
    # We explicitly forbid markdown and explanation to avoid JSON parse errors.
    # This is the same pattern used in your existing guardrails pipeline.
    grader_system_prompt = (
        "You are a relevance grader.\n"
        "Given a user question and a retrieved document chunk, "
        "decide if the chunk is relevant to answering the question.\n"
        "Respond ONLY with valid JSON: {\"relevant\": true} or {\"relevant\": false}\n"
        "No explanation. No markdown. No extra text."
    )

    # Call Mistral via Ollama with temperature=0 for deterministic output
    # temperature=0 means the model always picks the most probable token
    # — critical for graders that must return consistent JSON every time
    response = ollama.chat(
        model="mistral",                    # Local Mistral model served by Ollama
        options={"temperature": 0},         # Deterministic — no randomness in grading
        messages=[
            {
                "role": "system",
                "content": grader_system_prompt  # Tell Mistral it is a grader
            },
            {
                "role": "user",
                # Embed both the question and the chunk into one user message
                # so Mistral can compare them directly
                "content": f"Question: {question}\n\nChunk: {chunk}"
            }
        ]
    )

    # Extract the raw text content from Mistral's response message
    raw = response["message"]["content"].strip()

    try:
        # Parse the JSON response — e.g. {"relevant": true}
        result = json.loads(raw)

        # Return the boolean value of the "relevant" key
        # Default to False if key is missing (safe fallback)
        return result.get("relevant", False)

    except json.JSONDecodeError:
        # Mistral occasionally returns malformed JSON despite the strict prompt
        # (known issue with escaped underscores / stray characters in Mistral)
        # Safe fallback: treat as NOT relevant to avoid bad context reaching LLM
        show_user_action(
            "[CRAG] Grader Parse Error",
            f"Mistral returned non-JSON output: '{raw}'. "
            f"Treating chunk as IRRELEVANT to be safe."
        )
        return False  # Fail safe — don't use a chunk we can't grade


# --- CRAG Step 2: Rewrite query when no relevant docs found ---

def crag_rewrite_query(question: str) -> str:
    """
    When all retrieved docs are graded as irrelevant, we ask Mistral to
    rewrite the original question into a better retrieval query.

    Real example: "acetaminophen kids dose" → "pediatric acetaminophen dosage guidelines"
    """

    # Notify the user clearly that query rewrite is happening and why
    show_user_action(
        "[CRAG] Query Rewrite Triggered",
        f"All retrieved chunks were graded IRRELEVANT for question: '{question}'.\n"
        f"  >> Asking Mistral to rewrite the query for better retrieval."
    )

    # Ask Mistral to produce a better retrieval-optimized version of the question
    response = ollama.chat(
        model="mistral",
        options={"temperature": 0},  # Deterministic — we want one clean rewrite
        messages=[
            {
                "role": "system",
                # Tell Mistral to act as a search query optimizer
                "content": (
                    "You are a search query optimizer.\n"
                    "Rewrite the given question to improve document retrieval from a knowledge base.\n"
                    "Return ONLY the rewritten question. No explanation. No markdown."
                )
            },
            {
                "role": "user",
                "content": question  # Original question to rewrite
            }
        ]
    )

    # Extract and return the rewritten query as plain text
    rewritten = response["message"]["content"].strip()

    # Show user the rewritten query so they understand what changed
    show_user_action(
        "[CRAG] Rewritten Query",
        f"Original : '{question}'\n"
        f"  >> Rewritten : '{rewritten}'\n"
        f"  >> Re-retrieval would now run against your Solr/pgvector with this new query."
    )

    return rewritten  # Return rewritten query (caller would re-retrieve with this)


# --- CRAG Step 3: Generate final answer from clean, relevant context ---

def crag_generate_answer(question: str, relevant_chunks: list) -> str:
    """
    After filtering/correcting the retrieved context, generate the final answer.
    Only relevant chunks are passed — this is the 'corrected' part of CRAG.
    """

    # Join all relevant chunks with double newline as separator
    # This becomes the grounded context passed to the generation LLM
    context = "\n\n".join(relevant_chunks)

    # Notify user that generation is starting with clean context
    show_user_action(
        "[CRAG] Generating Answer",
        f"Using {len(relevant_chunks)} relevant chunk(s) as grounded context.\n"
        f"  >> Calling Mistral to generate the final answer."
    )

    # Call Mistral for final answer generation
    # temperature=0.3 gives slightly more natural answer vs strict temperature=0
    response = ollama.chat(
        model="mistral",
        options={"temperature": 0.3},   # Slight creativity for generation (not grading)
        messages=[
            {
                "role": "system",
                # Restrict Mistral to only use what's in the context — no hallucination
                "content": "Answer the user question using ONLY the provided context. Do not use outside knowledge."
            },
            {
                "role": "user",
                # Provide the grounded context + the original question
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
    )

    # Return the generated answer text
    return response["message"]["content"].strip()


# --- CRAG Main Pipeline ---

def run_crag(question: str, retrieved_chunks: list) -> str:
    """
    Full CRAG pipeline:
      1. Grade each retrieved chunk
      2. Keep only relevant chunks
      3. If none relevant → rewrite query → simulate re-retrieval
      4. Generate answer from clean context
    """

    print(f"\n{'#' * 60}")
    print(f"  CRAG PIPELINE START")
    print(f"  Question: {question}")
    print(f"  Retrieved Chunks Count: {len(retrieved_chunks)}")
    print(f"{'#' * 60}")

    relevant_chunks = []  # Will hold only the chunks that pass the grader

    # --- Grade each retrieved chunk one by one ---
    for i, chunk in enumerate(retrieved_chunks):

        # Notify user which chunk is being graded right now
        show_user_action(
            f"[CRAG] Grading Chunk {i + 1}/{len(retrieved_chunks)}",
            f"Chunk preview: '{chunk[:80]}...'\n"
            f"  >> Asking Mistral: is this chunk relevant to the question?"
        )

        # Call grader — returns True (relevant) or False (irrelevant)
        is_relevant = crag_grade_document(question, chunk)

        if is_relevant:
            # Chunk passed — add to the clean context list
            show_user_action(
                f"[CRAG] Chunk {i + 1} → RELEVANT ✓",
                "This chunk will be included in the context for answer generation."
            )
            relevant_chunks.append(chunk)  # Keep this chunk

        else:
            # Chunk failed — do NOT pass it to the generation LLM
            show_user_action(
                f"[CRAG] Chunk {i + 1} → IRRELEVANT ✗",
                "This chunk was graded irrelevant and will be DROPPED.\n"
                "  >> It will NOT be passed to the answer generation step.\n"
                "  >> This prevents hallucination from bad context."
            )
            # We simply don't append it — it's discarded silently

    # --- Check if we have any relevant chunks left ---
    if not relevant_chunks:
        # No relevant docs found at all — trigger query rewrite fallback
        show_user_action(
            "[CRAG] FALLBACK TRIGGERED",
            "Zero chunks passed the relevance grader.\n"
            "  >> The retrieved documents do not match the question.\n"
            "  >> Initiating query rewrite + simulated re-retrieval."
        )

        # Rewrite the original query for better retrieval
        rewritten_query = crag_rewrite_query(question)

        # In your real pipeline: re-run hybrid retrieval (pgvector + Solr BM25 with RRF)
        # using the rewritten_query. Here we simulate with a placeholder chunk.
        simulated_fallback_chunk = (
            f"[Simulated re-retrieved chunk for rewritten query: '{rewritten_query}']\n"
            f"This is where your Solr/pgvector results would appear after re-retrieval."
        )

        # Use the simulated fallback chunk as the context
        relevant_chunks = [simulated_fallback_chunk]

        show_user_action(
            "[CRAG] Re-retrieval Simulated",
            f"In production: pgvector + Solr BM25 RRF would run with: '{rewritten_query}'.\n"
            f"  >> Proceeding with simulated fallback context for this demo."
        )

    # --- Generate final answer using only clean, relevant context ---
    final_answer = crag_generate_answer(question, relevant_chunks)

    print(f"\n{'#' * 60}")
    print(f"  CRAG PIPELINE COMPLETE")
    print(f"  Final Answer:\n  {final_answer}")
    print(f"{'#' * 60}\n")

    return final_answer  # Return answer to caller


# =============================================================================
# SECTION 2: SELF-RAG
# =============================================================================
# Self-RAG flow:
#   LLM decides: need retrieval? → grade each chunk → generate per chunk
#   → LLM grades its own answer → return best-supported answer


# --- Self-RAG Step 1: Should we retrieve at all? ---

def selfrag_should_retrieve(question: str) -> bool:
    """
    The LLM decides if retrieval is necessary for this question.
    Simple factual questions (e.g. "what is 2+2") don't need retrieval.
    Clinical/domain questions always need retrieval.
    """

    show_user_action(
        "[Self-RAG] Retrieval Decision",
        f"Asking Mistral: does this question need external document retrieval?\n"
        f"  >> Question: '{question}'"
    )

    # Ask Mistral if retrieval is needed — strict JSON output
    response = ollama.chat(
        model="mistral",
        options={"temperature": 0},  # Deterministic decision
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a retrieval decision agent.\n"
                    "Decide if the question requires external documents to answer accurately.\n"
                    "Respond ONLY with valid JSON: {\"retrieve\": true} or {\"retrieve\": false}\n"
                    "No explanation. No markdown."
                )
            },
            {
                "role": "user",
                "content": question  # The question to evaluate
            }
        ]
    )

    # Extract the raw text response from Mistral
    raw = response["message"]["content"].strip()

    try:
        # Parse JSON and extract the boolean retrieval decision
        result = json.loads(raw)
        decision = result.get("retrieve", True)  # Default True — safer to retrieve

        # Tell the user what was decided and why it matters
        show_user_action(
            "[Self-RAG] Retrieval Decision Result",
            f"Mistral decided: retrieve = {decision}\n"
            f"  >> {'Will retrieve external docs.' if decision else 'Will answer from model knowledge only (no retrieval).'}"
        )

        return decision  # True = retrieve, False = use parametric knowledge

    except json.JSONDecodeError:
        # JSON parsing failed — default to retrieve (safer)
        show_user_action(
            "[Self-RAG] Retrieval Decision Parse Error",
            f"Mistral returned non-JSON: '{raw}'. Defaulting to retrieve=True."
        )
        return True  # Fail safe — retrieve rather than risk wrong answer


# --- Self-RAG Step 2: Grade relevance of a chunk ---

def selfrag_grade_relevance(question: str, chunk: str) -> str:
    """
    Grade if the chunk is relevant to the question.
    Returns 'relevant' or 'irrelevant' as a string.
    """

    response = ollama.chat(
        model="mistral",
        options={"temperature": 0},  # Deterministic grading
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a document relevance grader.\n"
                    "Is the document chunk relevant to answering the question?\n"
                    "Respond ONLY with valid JSON: {\"isrel\": \"relevant\"} or {\"isrel\": \"irrelevant\"}\n"
                    "No explanation. No markdown."
                )
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nChunk: {chunk}"
            }
        ]
    )

    raw = response["message"]["content"].strip()

    try:
        result = json.loads(raw)
        return result.get("isrel", "irrelevant")  # Default irrelevant if missing

    except json.JSONDecodeError:
        # Parse failed — safe fallback is irrelevant
        show_user_action(
            "[Self-RAG] Relevance Grade Parse Error",
            f"Mistral returned non-JSON: '{raw}'. Treating chunk as irrelevant."
        )
        return "irrelevant"


# --- Self-RAG Step 3: Grade if answer is supported by the chunk ---

def selfrag_grade_support(answer: str, chunk: str) -> str:
    """
    After generating an answer, the LLM grades itself:
    Is this answer fully/partially/not supported by the chunk?

    Returns: 'fully', 'partially', or 'no'
    """

    response = ollama.chat(
        model="mistral",
        options={"temperature": 0},  # Deterministic self-grading
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a faithfulness grader.\n"
                    "Does the answer faithfully use the document chunk as its source?\n"
                    "Respond ONLY with valid JSON:\n"
                    "{\"issup\": \"fully\"} or {\"issup\": \"partially\"} or {\"issup\": \"no\"}\n"
                    "No explanation. No markdown."
                )
            },
            {
                "role": "user",
                "content": f"Answer: {answer}\n\nChunk: {chunk}"
            }
        ]
    )

    raw = response["message"]["content"].strip()

    try:
        result = json.loads(raw)
        return result.get("issup", "no")  # Default no support if key missing

    except json.JSONDecodeError:
        # Parse failed — assume no support to avoid surfacing hallucinated answers
        show_user_action(
            "[Self-RAG] Support Grade Parse Error",
            f"Mistral returned non-JSON: '{raw}'. Treating support as 'no'."
        )
        return "no"


# --- Self-RAG Main Pipeline ---

def run_self_rag(question: str, retrieved_chunks: list) -> dict:
    """
    Full Self-RAG pipeline:
      1. LLM decides if retrieval is needed
      2. Grade each chunk for relevance
      3. Generate an answer grounded in each relevant chunk
      4. LLM grades its own answer for faithfulness to the chunk
      5. Return the best-supported answer across all chunks
    """

    print(f"\n{'#' * 60}")
    print(f"  SELF-RAG PIPELINE START")
    print(f"  Question: {question}")
    print(f"  Retrieved Chunks Count: {len(retrieved_chunks)}")
    print(f"{'#' * 60}")

    # --- Step 1: Should we retrieve at all? ---
    needs_retrieval = selfrag_should_retrieve(question)

    if not needs_retrieval:
        # LLM decided no retrieval needed — answer from parametric knowledge
        show_user_action(
            "[Self-RAG] Skipping Retrieval",
            "Mistral decided retrieval is NOT needed for this question.\n"
            "  >> Answering from model's parametric (trained) knowledge.\n"
            "  >> No chunks will be used."
        )

        # Generate answer directly without any context
        response = ollama.chat(
            model="mistral",
            options={"temperature": 0.3},   # Slight creativity for generation
            messages=[
                {
                    "role": "user",
                    "content": question  # Just the question — no context
                }
            ]
        )

        answer = response["message"]["content"].strip()

        print(f"\n{'#' * 60}")
        print(f"  SELF-RAG COMPLETE (Parametric — no retrieval used)")
        print(f"  Final Answer:\n  {answer}")
        print(f"{'#' * 60}\n")

        # Return answer with metadata indicating no retrieval was used
        return {"answer": answer, "source": "parametric", "support": "n/a"}

    # --- Step 2: Grade each chunk and generate candidate answers ---

    # Support rank mapping — used to compare which answer is best supported
    # fully=3 is best, partially=2 is okay, no=1 means hallucinated/unsupported
    support_rank = {"fully": 3, "partially": 2, "no": 1}

    best_answer = None    # Will hold the best answer found so far
    best_support = "no"   # Will hold the support level of the best answer
    best_chunk_index = -1 # Track which chunk produced the best answer

    for i, chunk in enumerate(retrieved_chunks):

        # --- Grade chunk relevance before generating from it ---
        show_user_action(
            f"[Self-RAG] Grading Relevance of Chunk {i + 1}/{len(retrieved_chunks)}",
            f"Chunk preview: '{chunk[:80]}...'\n"
            f"  >> Asking Mistral: is this chunk relevant to the question?"
        )

        relevance = selfrag_grade_relevance(question, chunk)  # 'relevant' or 'irrelevant'

        if relevance == "irrelevant":
            # Skip this chunk entirely — don't generate from bad context
            show_user_action(
                f"[Self-RAG] Chunk {i + 1} → IRRELEVANT ✗",
                "This chunk was graded IRRELEVANT.\n"
                "  >> Skipping answer generation for this chunk.\n"
                "  >> Moving to next chunk."
            )
            continue  # Move to next chunk in the loop

        # Chunk is relevant — proceed to generate an answer grounded in it
        show_user_action(
            f"[Self-RAG] Chunk {i + 1} → RELEVANT ✓",
            "This chunk passed relevance grading.\n"
            "  >> Generating a candidate answer grounded in this chunk."
        )

        # --- Generate candidate answer from this chunk ---
        response = ollama.chat(
            model="mistral",
            options={"temperature": 0.3},  # Slight creativity for generation
            messages=[
                {
                    "role": "system",
                    "content": "Answer the question using ONLY the provided context. Do not use outside knowledge."
                },
                {
                    "role": "user",
                    # Provide only this single chunk as context — Self-RAG grades per chunk
                    "content": f"Context:\n{chunk}\n\nQuestion: {question}"
                }
            ]
        )

        # Extract the candidate answer text
        candidate_answer = response["message"]["content"].strip()

        # --- Grade if the generated answer is supported by the chunk ---
        show_user_action(
            f"[Self-RAG] Grading Answer Support for Chunk {i + 1}",
            f"Answer preview: '{candidate_answer[:80]}...'\n"
            f"  >> Asking Mistral: is this answer faithfully supported by the chunk?"
        )

        support = selfrag_grade_support(candidate_answer, chunk)  # 'fully', 'partially', 'no'

        # Tell the user the support grade and what it means
        support_explanation = {
            "fully":     "Answer is FULLY supported by the chunk. Excellent — no hallucination detected.",
            "partially": "Answer is PARTIALLY supported. Some content may not be grounded in the chunk.",
            "no":        "Answer is NOT supported by the chunk. Possible hallucination — will not use this answer."
        }

        show_user_action(
            f"[Self-RAG] Support Grade for Chunk {i + 1}: '{support.upper()}'",
            support_explanation.get(support, "Unknown support level.")
        )

        # --- Compare this candidate to the current best ---
        # Use the rank map to compare: fully(3) > partially(2) > no(1)
        if support_rank.get(support, 0) > support_rank.get(best_support, 0):
            # This answer is better supported than the previous best
            best_answer = candidate_answer   # Replace best answer
            best_support = support           # Update best support level
            best_chunk_index = i + 1         # Track which chunk won

            show_user_action(
                f"[Self-RAG] New Best Answer Found",
                f"Chunk {i + 1} produced the best-supported answer so far.\n"
                f"  >> Support level: '{best_support}'\n"
                f"  >> This answer is now the current best candidate."
            )

        # If we already have a fully-supported answer, no need to check more chunks
        if best_support == "fully":
            show_user_action(
                "[Self-RAG] Early Exit",
                f"Chunk {i + 1} produced a FULLY supported answer.\n"
                "  >> No need to evaluate remaining chunks.\n"
                "  >> Stopping early to save LLM calls."
            )
            break  # Stop iterating — we have the best possible answer

    # --- Handle case where no chunk produced a usable answer ---
    if best_answer is None:
        show_user_action(
            "[Self-RAG] NO USABLE ANSWER FOUND",
            "All chunks were either irrelevant or produced unsupported answers.\n"
            "  >> Could not generate a grounded answer for this question.\n"
            "  >> Returning a failure message to the user.\n"
            "  >> Consider: expanding the retrieval corpus, rewriting the query, or web search fallback."
        )
        best_answer = (
            "I was unable to find a sufficiently grounded answer in the retrieved documents. "
            "Please try rephrasing your question or expanding the knowledge base."
        )

    # --- Print final result summary ---
    print(f"\n{'#' * 60}")
    print(f"  SELF-RAG PIPELINE COMPLETE")
    print(f"  Winning Chunk      : {best_chunk_index}")
    print(f"  Final Support Level: {best_support.upper()}")
    print(f"  Final Answer:\n  {best_answer}")
    print(f"{'#' * 60}\n")

    # Return full result dict — answer + metadata for observability (e.g. Langfuse)
    return {
        "answer": best_answer,          # The final generated answer
        "support": best_support,        # Faithfulness grade: fully / partially / no
        "winning_chunk": best_chunk_index  # Which chunk produced the best answer
    }


# =============================================================================
# MAIN: Demo both pipelines with realistic clinical knowledge examples
# =============================================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  DEMO: CRAG and Self-RAG with Ollama (Mistral)")
    print("  Simulating your Stanford Children's Health RAG pipeline")
    print("=" * 60)

    # --- Demo Question ---
    # Simulating a clinical knowledge search question from the patient portal
    demo_question = "What is the recommended acetaminophen dose for children under 12?"

    # --- Simulated Retrieved Chunks ---
    # In your real pipeline, these come from pgvector + Solr BM25 with RRF hybrid retrieval.
    # Here we manually provide 3 chunks: 1 relevant, 1 partially relevant, 1 irrelevant.
    demo_chunks = [

        # Chunk 1: Clearly relevant — correct topic and age group
        (
            "Acetaminophen (Tylenol) dosing for pediatric patients is weight-based. "
            "The standard dose is 10-15 mg/kg every 4-6 hours as needed, not exceeding 5 doses in 24 hours. "
            "For children under 12, always use the pediatric formulation."
        ),

        # Chunk 2: Irrelevant — about adult dosage, not pediatric
        (
            "For adults, the standard acetaminophen dose is 500-1000mg every 4-6 hours. "
            "Maximum daily dose for adults is 4000mg. "
            "Patients with liver conditions should use lower doses."
        ),

        # Chunk 3: Slightly related but about a different drug
        (
            "Ibuprofen is an alternative to acetaminophen for fever management in children. "
            "Dosing is 5-10 mg/kg every 6-8 hours. "
            "Do not use ibuprofen in infants under 6 months."
        )
    ]

    # =========================================================================
    # RUN CRAG
    # =========================================================================
    print("\n\n" + "*" * 60)
    print("  RUNNING CORRECTIVE RAG (CRAG)")
    print("*" * 60)

    # Run the full CRAG pipeline — grades docs BEFORE generation
    crag_result = run_crag(
        question=demo_question,      # The user's clinical question
        retrieved_chunks=demo_chunks  # Chunks from hybrid retrieval
    )

    # =========================================================================
    # RUN SELF-RAG
    # =========================================================================
    print("\n\n" + "*" * 60)
    print("  RUNNING SELF-RAG")
    print("*" * 60)

    # Run the full Self-RAG pipeline — LLM grades itself at each step
    self_rag_result = run_self_rag(
        question=demo_question,      # Same clinical question
        retrieved_chunks=demo_chunks  # Same retrieved chunks
    )

    # =========================================================================
    # FINAL SIDE-BY-SIDE SUMMARY
    # =========================================================================
    print("\n" + "=" * 60)
    print("  FINAL RESULTS COMPARISON")
    print("=" * 60)
    print(f"\n  [CRAG]     Answer: {crag_result[:120]}...")
    print(f"\n  [Self-RAG] Answer: {self_rag_result['answer'][:120]}...")
    print(f"  [Self-RAG] Support Level : {self_rag_result['support'].upper()}")
    print(f"  [Self-RAG] Winning Chunk : {self_rag_result['winning_chunk']}")
    print("\n" + "=" * 60)
