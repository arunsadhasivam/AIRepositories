# ragas_eval.py
# Evaluates RAG pipeline output using RAGAS framework.
# Metrics covered: Faithfulness, Context Precision, Answer Correctness.
# Results are logged to Langfuse via the centralised tracker.

from datasets import Dataset                          # RAGAS expects HuggingFace Dataset format
from ragas import evaluate                            # main RAGAS evaluation entry point
from ragas.metrics import (
    faithfulness,        # is the answer grounded in the retrieved context?
    context_precision,   # are the retrieved chunks actually relevant to the question?
    answer_correctness   # does the answer match the ground truth?
)
from tracking.langfuse_tracker import create_trace, log_score  # centralised Langfuse logging


# ---------------------------------------------------------------------------
# Sample clinical data — replace with your real RAG pipeline output.
# Each entry represents one query-response cycle from your RAG system.
# ---------------------------------------------------------------------------
SAMPLE_DATA = [
    {
        # The original user question sent to the RAG pipeline
        "question": "What are the symptoms of pediatric asthma?",

        # The answer your RAG pipeline generated
        "answer": "Pediatric asthma symptoms include wheezing, shortness of breath, chest tightness, and coughing especially at night.",

        # The text chunks retrieved from pgvector / Solr and passed to the LLM
        "contexts": [
            "Asthma in children causes recurring episodes of wheezing, breathlessness, chest tightness, and night-time coughing.",
            "Pediatric asthma is the most common chronic disease in children and is triggered by allergens, exercise, or infections."
        ],

        # The expected correct answer — used for answer_correctness metric
        "ground_truth": "Symptoms of pediatric asthma include wheezing, shortness of breath, chest tightness, and coughing."
    },
    {
        "question": "What is the recommended treatment for RSV in infants?",
        "answer": "RSV in infants is managed with supportive care including hydration, oxygen therapy, and nasal suctioning.",
        "contexts": [
            "Respiratory syncytial virus (RSV) treatment in infants focuses on supportive care: maintaining hydration, supplemental oxygen, and nasal suctioning.",
            "Palivizumab is given prophylactically to high-risk infants to prevent severe RSV disease."
        ],
        "ground_truth": "RSV treatment in infants involves supportive care such as hydration, oxygen, and nasal suctioning."
    }
]


def run_ragas_evaluation(data: list = None) -> dict:
    """
    Run RAGAS evaluation on a list of RAG query results.

    Args:
        data: List of dicts with keys: question, answer, contexts, ground_truth.
              Defaults to SAMPLE_DATA if not provided.

    Returns:
        Dict of metric name -> average score across all samples.
    """
    # Use provided data or fall back to sample data
    eval_data = data or SAMPLE_DATA

    # Convert list of dicts to HuggingFace Dataset — required by RAGAS
    dataset = Dataset.from_list(eval_data)

    # Run RAGAS evaluation with the three chosen metrics
    # RAGAS internally calls an LLM to score faithfulness and correctness
    results = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,       # score: is every claim in the answer supported by context?
            context_precision,  # score: are retrieved chunks ranked well for the question?
            answer_correctness  # score: semantic + factual match against ground truth
        ]
    )

    # Convert results to plain dict for easy logging
    scores = results.to_pandas().mean().to_dict()  # average each metric across all rows
    return scores


def evaluate_and_log(query: str, data: list = None) -> None:
    """
    Run RAGAS evaluation and log all metric scores to Langfuse.

    Args:
        query: Representative query string used to create the Langfuse trace.
        data : RAG output data to evaluate.
    """
    # Create a Langfuse trace to group all RAGAS scores under one query run
    trace = create_trace(query=query, metadata={"evaluator": "RAGAS"})

    # Run the evaluation
    scores = run_ragas_evaluation(data)

    # Log each metric score to Langfuse under the same trace
    for metric_name, score_value in scores.items():
        log_score(
            trace_id=trace.id,          # link to this query's trace
            metric_name=f"ragas_{metric_name}",  # prefix with 'ragas_' for clarity
            score=float(score_value),   # cast numpy float to Python float
            comment=f"RAGAS {metric_name} evaluation"
        )

    print(f"\n[RAGAS] Evaluation complete. Scores: {scores}")


# ---------------------------------------------------------------------------
# Entry point — run directly to test with sample data
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    evaluate_and_log(query="pediatric asthma symptoms")
