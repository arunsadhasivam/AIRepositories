# bertscore_eval.py
# BERTScore evaluation — measures semantic similarity between RAG response
# and clinical ground truth using contextual BERT embeddings.
# Better than exact-match metrics (BLEU/ROUGE) for medical text because
# it captures meaning rather than word overlap.
# Results are logged to Langfuse via the centralised tracker.

from bert_score import score as bert_score_fn                    # BERTScore library
from tracking.langfuse_tracker import create_trace, log_score   # centralised Langfuse logging


# ---------------------------------------------------------------------------
# Sample clinical query-response pairs — replace with real pipeline output.
# 'response'     : what your RAG pipeline generated.
# 'ground_truth' : the clinically validated correct answer.
# ---------------------------------------------------------------------------
SAMPLE_DATA = [
    {
        "query": "What are the symptoms of pediatric asthma?",
        # RAG pipeline response
        "response": "Children with asthma often experience wheezing, coughing at night, shortness of breath, and chest tightness.",
        # Clinically validated reference answer
        "ground_truth": "Pediatric asthma symptoms include wheezing, breathlessness, chest tightness, and nocturnal coughing."
    },
    {
        "query": "How is RSV treated in premature infants?",
        "response": "RSV in premature infants is treated with supportive care including oxygen and hydration. Palivizumab is used prophylactically.",
        "ground_truth": "Treatment for RSV in premature infants involves supportive care such as supplemental oxygen and IV fluids. Palivizumab prophylaxis is recommended for high-risk infants."
    }
]


def run_bertscore_evaluation(data: list = None) -> list:
    """
    Compute BERTScore F1 for each RAG response vs its ground truth.

    BERTScore returns three values per pair:
        Precision (P) : how much of the response matches the reference.
        Recall    (R) : how much of the reference is covered by the response.
        F1            : harmonic mean of P and R — primary metric we track.

    Args:
        data: List of dicts with keys: query, response, ground_truth.
              Defaults to SAMPLE_DATA.

    Returns:
        List of result dicts with query, f1_score, precision, recall.
    """
    eval_data = data or SAMPLE_DATA

    # Separate responses and ground truths into parallel lists for BERTScore
    responses = [item["response"] for item in eval_data]          # RAG-generated answers
    references = [item["ground_truth"] for item in eval_data]     # clinical ground truths

    # Compute BERTScore using clinical/biomedical BERT model for better accuracy
    # 'microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract' is ideal for clinical text
    # Fallback to 'bert-base-uncased' if biomedical model is not available
    precision_scores, recall_scores, f1_scores = bert_score_fn(
        cands=responses,                                  # candidate: RAG responses
        refs=references,                                  # reference: ground truth
        model_type="microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract",  # biomedical BERT
        lang="en",                                        # English language
        verbose=True                                      # print progress to console
    )

    results = []

    # Iterate each sample and pair scores with original data
    for i, item in enumerate(eval_data):
        f1 = f1_scores[i].item()           # convert tensor to Python float
        precision = precision_scores[i].item()
        recall = recall_scores[i].item()

        # Create a Langfuse trace for this individual query evaluation
        trace = create_trace(
            query=item["query"],
            metadata={"evaluator": "BERTScore"}
        )

        # Log F1 as the primary clinical accuracy score to Langfuse
        log_score(
            trace_id=trace.id,
            metric_name="bertscore_f1",
            score=f1,
            comment=f"BERTScore F1 — precision={precision:.4f}, recall={recall:.4f}"
        )

        print(f"\n[BERTScore] Query: '{item['query']}'")
        print(f"  F1={f1:.4f}  Precision={precision:.4f}  Recall={recall:.4f}")

        results.append({
            "query": item["query"],
            "f1_score": f1,
            "precision": precision,
            "recall": recall
        })

    return results


# ---------------------------------------------------------------------------
# Entry point — run directly to test with sample data
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_bertscore_evaluation()
