# mirage_eval.py
# MIRAGE — Medical Information Retrieval-Augmented Generation Evaluation.
# Offline benchmark specifically designed for clinical RAG pipelines.
# Tests retrieval and generation quality against medical question datasets
# (e.g. MedQA, MedMCQA, PubMedQA).
# Results are logged to Langfuse via the centralised tracker.
#
# MIRAGE GitHub: https://github.com/Teddy-XiongGZ/MIRAGE
# Install: pip install mirage-bench (or clone and install from GitHub)

import json                                                      # for loading benchmark dataset files
from tracking.langfuse_tracker import create_trace, log_score   # centralised Langfuse logging


# ---------------------------------------------------------------------------
# MIRAGE covers multiple medical QA datasets.
# Each benchmark_id maps to a dataset MIRAGE uses for retrieval + generation eval.
# ---------------------------------------------------------------------------
MIRAGE_BENCHMARKS = {
    "MedQA"    : "US medical licensing exam questions (USMLE style)",
    "MedMCQA"  : "Indian medical entrance exam multiple choice questions",
    "PubMedQA" : "Biomedical research question answering from PubMed abstracts",
    "MMLU_Med" : "Massive Multitask Language Understanding — medical subset"
}


# ---------------------------------------------------------------------------
# Sample MIRAGE-style data — simulates what MIRAGE loads from its dataset files.
# In real usage, MIRAGE loads these automatically from its benchmark datasets.
# Replace with actual MIRAGE pipeline output when running against real corpora.
# ---------------------------------------------------------------------------
SAMPLE_MIRAGE_DATA = [
    {
        "benchmark": "MedQA",
        # The multiple-choice clinical question
        "question": "A 4-year-old presents with barking cough and inspiratory stridor. What is the most likely diagnosis?",
        # The answer your RAG pipeline selected
        "rag_answer": "Croup (Laryngotracheobronchitis)",
        # The correct answer from the benchmark dataset
        "gold_answer": "Croup",
        # Retrieved context chunks passed to the LLM
        "retrieved_contexts": [
            "Croup is characterised by a barking cough, stridor, and hoarseness in children aged 6 months to 3 years.",
            "Laryngotracheobronchitis (croup) is the most common cause of acute upper airway obstruction in children."
        ]
    },
    {
        "benchmark": "PubMedQA",
        "question": "Does palivizumab prophylaxis reduce RSV hospitalisation in premature infants?",
        "rag_answer": "Yes, palivizumab significantly reduces RSV-related hospitalisation in high-risk premature infants.",
        "gold_answer": "yes",
        "retrieved_contexts": [
            "Palivizumab prophylaxis has been shown to reduce RSV hospitalisation by approximately 55% in premature infants.",
        ]
    }
]


def compute_exact_match(rag_answer: str, gold_answer: str) -> float:
    """
    Compute exact match score between RAG answer and gold answer.
    Case-insensitive and strips whitespace for fair comparison.

    Args:
        rag_answer : Answer produced by your RAG pipeline.
        gold_answer: Correct answer from MIRAGE benchmark dataset.

    Returns:
        1.0 if answers match, 0.0 otherwise.
    """
    # Normalise both answers: lowercase and strip surrounding whitespace
    normalised_rag = rag_answer.strip().lower()
    normalised_gold = gold_answer.strip().lower()

    # Check if gold answer string appears within the RAG answer (partial match)
    return 1.0 if normalised_gold in normalised_rag else 0.0


def compute_retrieval_hit(retrieved_contexts: list, gold_answer: str) -> float:
    """
    Check if the gold answer appears in any of the retrieved context chunks.
    This measures retrieval quality — did the retriever surface the right chunk?

    Args:
        retrieved_contexts: List of text chunks returned by the retriever.
        gold_answer       : Correct answer from benchmark.

    Returns:
        1.0 if gold answer found in any context chunk, 0.0 otherwise.
    """
    gold_lower = gold_answer.strip().lower()  # normalise gold answer
    for chunk in retrieved_contexts:
        if gold_lower in chunk.lower():       # check each retrieved chunk
            return 1.0                        # hit — correct chunk was retrieved
    return 0.0                                # miss — correct answer not in any chunk


def run_mirage_benchmark(data: list = None) -> dict:
    """
    Run MIRAGE-style offline benchmark evaluation.

    Computes:
        - Exact Match (EM)  : did the RAG answer match the gold answer?
        - Retrieval Hit Rate : did the retriever surface the relevant chunk?

    Args:
        data: List of MIRAGE-format dicts. Defaults to SAMPLE_MIRAGE_DATA.

    Returns:
        Dict with aggregate scores: avg_exact_match, avg_retrieval_hit_rate.
    """
    eval_data = data or SAMPLE_MIRAGE_DATA

    exact_match_scores = []     # collect EM scores across all samples
    retrieval_hit_scores = []   # collect retrieval hit scores across all samples

    for item in eval_data:
        # Compute exact match for this sample
        em_score = compute_exact_match(item["rag_answer"], item["gold_answer"])

        # Compute retrieval hit rate for this sample
        hit_score = compute_retrieval_hit(item["retrieved_contexts"], item["gold_answer"])

        exact_match_scores.append(em_score)
        retrieval_hit_scores.append(hit_score)

        # Create a Langfuse trace per benchmark question
        trace = create_trace(
            query=item["question"],
            metadata={"evaluator": "MIRAGE", "benchmark": item["benchmark"]}
        )

        # Log exact match score to Langfuse
        log_score(
            trace_id=trace.id,
            metric_name="mirage_exact_match",
            score=em_score,
            comment=f"MIRAGE [{item['benchmark']}] — rag='{item['rag_answer']}' gold='{item['gold_answer']}'"
        )

        # Log retrieval hit rate to Langfuse
        log_score(
            trace_id=trace.id,
            metric_name="mirage_retrieval_hit",
            score=hit_score,
            comment=f"MIRAGE [{item['benchmark']}] retrieval hit rate"
        )

        print(f"\n[MIRAGE] Benchmark: {item['benchmark']}")
        print(f"  Question : {item['question'][:80]}...")
        print(f"  EM Score : {em_score} | Retrieval Hit: {hit_score}")

    # Compute aggregate averages across all benchmark samples
    avg_em = sum(exact_match_scores) / len(exact_match_scores)
    avg_hit = sum(retrieval_hit_scores) / len(retrieval_hit_scores)

    print(f"\n[MIRAGE] Aggregate — Avg Exact Match: {avg_em:.4f} | Avg Retrieval Hit: {avg_hit:.4f}")

    return {
        "avg_exact_match": avg_em,
        "avg_retrieval_hit_rate": avg_hit
    }


# ---------------------------------------------------------------------------
# Entry point — run directly to test with sample data
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_mirage_benchmark()
