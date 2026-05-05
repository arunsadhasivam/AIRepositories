# RAGAS Evaluation — How It Works & Langfuse Integration

---

## 1. What is RAGAS?

RAGAS (Retrieval Augmented Generation Assessment) is an open-source framework
that evaluates your RAG pipeline automatically — without needing manually
labeled ground truth for every single metric.

It sits **outside** your pipeline and evaluates after the fact.

---

## 2. What RAGAS Needs as Input

For every question you want to evaluate, you provide:

```
{
  "question":        "What are visiting hours at Stanford Children's?",
  "answer":          "Visiting hours are 8am to 8pm daily.",        ← LLM generated
  "contexts":        ["...retrieved chunk 1...", "...chunk 2..."],   ← from retriever
  "ground_truth":    "Visiting hours are 8am to 8pm."               ← optional, for some metrics
}
```

---

## 3. RAGAS Metrics Explained

| Metric | Needs Ground Truth? | What it checks |
|---|---|---|
| **Faithfulness** | No | Every claim in answer backed by context? |
| **Answer Relevance** | No | Does answer address the question? |
| **Context Precision** | Yes | Are retrieved chunks ranked well? |
| **Context Recall** | Yes | Did retriever get all relevant chunks? |

> Faithfulness + Answer Relevance work WITHOUT ground truth.
> This is the key differentiator RAGAS has over manual eval.

---

## 4. How RAGAS Evaluates Internally

RAGAS itself uses an LLM under the hood to score each metric.

### Faithfulness (step by step):
1. Breaks the generated answer into individual claims
2. For each claim, asks LLM: "Is this claim supported by the context?"
3. Score = supported claims / total claims

### Answer Relevance (step by step):
1. Takes the generated answer
2. Asks LLM to generate N questions that this answer could be answering
3. Measures cosine similarity between generated questions and original question
4. High similarity = answer is relevant to the question

### Context Precision:
1. For each retrieved chunk, asks LLM: "Is this chunk useful for answering the question?"
2. Checks if useful chunks are ranked higher than useless ones

### Context Recall:
1. Breaks ground truth into sentences
2. Checks if each sentence can be attributed to a retrieved chunk

---

## 5. RAGAS — Standalone Setup (without Langfuse)

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

# Your pipeline output collected into a dataset
data = {
    "question":     ["What are visiting hours?"],
    "answer":       ["Visiting hours are 8am to 8pm daily."],
    "contexts":     [["...chunk1...", "...chunk2..."]],
    "ground_truth": ["Visiting hours are 8am to 8pm."]
}

dataset = Dataset.from_dict(data)

# Run evaluation
result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)

print(result)
# Output:
# {'faithfulness': 0.95, 'answer_relevancy': 0.88, 'context_precision': 0.90, 'context_recall': 0.85}
```

---

## 6. Langfuse — What It Does vs RAGAS

These are TWO separate tools that complement each other:

| | RAGAS | Langfuse |
|---|---|---|
| **Purpose** | Evaluate quality metrics | Observe/trace pipeline execution |
| **What it captures** | Faithfulness, relevance, precision, recall scores | Latency, token usage, inputs, outputs per step |
| **When it runs** | Post-pipeline, batch evaluation | Real-time, every request |
| **Ground truth needed** | For some metrics | No |

---

## 7. How RAGAS + Langfuse Work Together

Langfuse has native RAGAS integration via its **evaluation/scoring API**.

### Flow:
```
User Query
    ↓
RAG Pipeline runs (LangChain / LangGraph)
    ↓
Langfuse traces the full run (retrieval + generation)
    ↓
RAGAS evaluates the output (faithfulness, relevance, etc.)
    ↓
Scores pushed back into Langfuse trace via scoring API
    ↓
Langfuse dashboard shows scores alongside traces
```

---

## 8. Langfuse + RAGAS Integration Code

```python
from langfuse import Langfuse
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset

langfuse = Langfuse()

# After your RAG pipeline runs and you have question/answer/contexts
def evaluate_and_log(trace_id, question, answer, contexts):

    # Step 1: Build RAGAS dataset
    data = {
        "question": [question],
        "answer":   [answer],
        "contexts": [contexts]
    }
    dataset = Dataset.from_dict(data)

    # Step 2: Run RAGAS evaluation
    result = evaluate(dataset, metrics=[faithfulness, answer_relevancy])

    # Step 3: Push scores back into Langfuse trace
    langfuse.score(
        trace_id=trace_id,
        name="faithfulness",
        value=result["faithfulness"]
    )
    langfuse.score(
        trace_id=trace_id,
        name="answer_relevancy",
        value=result["answer_relevancy"]
    )
```

Now in Langfuse UI you can see:
- The full trace (retrieval chunks, LLM call, latency)
- RAGAS scores attached to that exact trace
- Filter traces by score threshold (e.g., show all where faithfulness < 0.7)

---

## 9. Langfuse Native Evaluators (Alternative to RAGAS)

Langfuse also has its own built-in LLM-as-Judge evaluators (since 2024):

```
Langfuse UI → Evaluations → Configure Evaluator
    → Pick metric (hallucination, relevance, toxicity)
    → Pick judge model (GPT-4, Claude, etc.)
    → Runs automatically on sampled traces
```

This means you can skip RAGAS entirely and use Langfuse's own eval pipeline —
but RAGAS gives more RAG-specific metrics (context precision/recall).

---

## 10. Recommended Setup for Your Stanford Pipeline

```
Production traffic
    ↓
Langfuse traces every request (already doing this)
    ↓
Sample 5-10% of traces nightly
    ↓
Run RAGAS on sampled traces
    ↓
Push scores to Langfuse
    ↓
Alert if faithfulness < 0.75 or answer_relevancy < 0.80
```

This gives you:
- Real-time observability (Langfuse)
- Periodic quality evaluation (RAGAS)
- Historical score trends to catch regressions after code changes

---

## Summary

| Question | Answer |
|---|---|
| Is RAGAS inside Langfuse? | No — separate library, but integrates via scoring API |
| Does RAGAS need ground truth? | Only for context precision/recall. Faithfulness + relevance do not. |
| What does Langfuse add? | Tracing, latency, token cost, score history, dashboard |
| When to use RAGAS alone? | Offline batch evaluation, CI/CD regression testing |
| When to combine both? | Production pipelines needing both observability + quality scores |
