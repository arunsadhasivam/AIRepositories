import ollama
import os
import json
import re
import logging
from datetime import datetime, timezone
import uuid
from indexer.SolrIndexer import SolrIndexer
from rag.retriever.Document import Document as RetrieverDocument

logger = logging.getLogger(__name__)

# Config
LLM_MODEL = os.getenv('LLM_MODEL', 'mistral:7b-instruct-q2_K')
FAITHFULNESS_HARD_BLOCK = 0.4
OVERALL_PASS_THRESHOLD = 0.8
OVERALL_RETRY_THRESHOLD = 0.5
solrIndexer = SolrIndexer()



def run_judge_pipeline(query, answer, context_chunks, primary_retriever, llm) -> dict:

    attempt = 0
    use_hybrid = True
    current_answer = answer
    current_chunks = context_chunks

    while attempt <= 1:
        attempt += 1

        # Build judge prompt
        formatted_chunks = "\n\n".join(f"Chunk {i+1}:\n{c}" for i, c in enumerate(current_chunks))
        prompt = f"""You are an expert AI evaluator.
Question: {query}
Context: {formatted_chunks}
Answer: {current_answer}
Score each 0.0 to 1.0: faithfulness, answer_relevance, context_relevance, completeness, overall.
Respond ONLY in JSON:
{{"faithfulness":0.0,"answer_relevance":0.0,"context_relevance":0.0,"completeness":0.0,"overall":0.0,"reason":""}}"""

        # Call ollama judge
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json"
        )
        raw = response["message"]["content"]

        # Parse scores
        try:
            cleaned = re.sub(r"```json|```", "", raw).strip()
            scores = json.loads(cleaned)
        except Exception as e:
            logger.error(f"Judge parse failed: {e}")
            scores = {"faithfulness": 0.0, "answer_relevance": 0.0, "context_relevance": 0.0,
                      "completeness": 0.0, "overall": 0.0, "reason": "parse failed"}

        strategy = "hybrid" if use_hybrid else "pgvector"
        logger.info(f"Attempt {attempt} | Strategy: {strategy} | Scores: {scores}")

        # Hard block — hallucination
        if scores["faithfulness"] < FAITHFULNESS_HARD_BLOCK:
            _log(query, current_answer, current_chunks, scores, strategy, attempt, "blocked")
            return {"status": "blocked", "reason": "Hallucination detected", "scores": scores}

        # Pass
        if scores["overall"] >= OVERALL_PASS_THRESHOLD:
            _log(query, current_answer, current_chunks, scores, strategy, attempt, "passed")
            return {"status": "passed", "answer": current_answer, "scores": scores}

        # Retry with pgvector only
        if scores["overall"] < OVERALL_RETRY_THRESHOLD and use_hybrid:
            _log(query, current_answer, current_chunks, scores, strategy, attempt, "retried")
            pgvector_retriever = primary_retriever.as_langchain_retriever()
            fallback_docs = pgvector_retriever.get_relevant_documents(query)
            current_chunks = [doc["document"]["docs"] for doc in fallback_docs]
            context = "\n\n".join(current_chunks)
            current_answer = llm.invoke(f"Context:\n{context}\n\nQuestion:\n{query}\n\nAnswer:")
            use_hybrid = False
            continue

        # Low confidence
        _log(query, current_answer, current_chunks, scores, strategy, attempt, "low_confidence")
        return {"status": "low_confidence", "answer": current_answer, "scores": scores}

    return {"status": "blocked", "reason": "Exhausted retries", "scores": scores}


def _log(query, answer, chunks, scores, strategy, attempt, action):
    # Log judge result to Elasticsearch
    try:
        
        judge_response = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "answer": answer,
            "context_chunks": chunks,
            "faithfulness": scores["faithfulness"],
            "answer_relevance": scores["answer_relevance"],
            "context_relevance": scores["context_relevance"],
            "completeness": scores["completeness"],
            "overall": scores["overall"],
            "reason": scores["reason"],
            "retrieval_strategy": strategy,
            "attempt_number": attempt,
            "final_action": action
        }
        content  = json.dumps(judge_response)
        solr_doc = RetrieverDocument(
            id=judge_response["id"],
            content=content, # full judge response as JSON string
            metadata={"type": "judge_log"},
            score=0.0
        )
        solrIndexer.index_to_solr( chunks=[solr_doc])
    except Exception as e:
        logger.error(f"ES logging failed: {e}")