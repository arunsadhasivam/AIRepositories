# RAG Evaluation & Benchmarking — Clinical RAG Pipeline

Production-grade evaluation and benchmarking suite for a clinical RAG pipeline
(Stanford Children's Health patient portal). Covers evaluation metrics, HIPAA
compliance checks, semantic accuracy, and offline medical benchmarking — all
tracked via Langfuse observability.

---

## Project Structure

```
RAG_EVALUATION/
├── evaluation/
│   ├── ragas_eval.py          # RAGAS metrics: Faithfulness, Context Precision, Answer Correctness
│   ├── phi_leakage_check.py   # PHI/PII leakage detection — HIPAA compliance gate
│   └── bertscore_eval.py      # BERTScore semantic similarity vs clinical ground truth
├── benchmarking/
│   ├── mirage_eval.py         # MIRAGE offline clinical RAG benchmark
│   └── medrag_eval.py         # MedRAG benchmark across PubMed, textbooks, guidelines
├── tracking/
│   └── langfuse_tracker.py    # Centralised Langfuse logging used by all scripts
├── requirements.txt
└── README.md
```

---

## Evaluation Tools

| Tool | Type | What It Measures |
|---|---|---|
| RAGAS | Evaluation Framework | Faithfulness, Context Precision, Answer Correctness |
| PHI Leakage Check | Compliance Gate | PII/PHI exposure in RAG responses — HIPAA |
| BERTScore | Semantic Eval | Semantic similarity of response vs clinical ground truth |
| Langfuse | Observability | Tracks and monitors all metric scores over time |

## Benchmarking Tools

| Tool | Type | Corpora |
|---|---|---|
| MIRAGE | Offline Benchmark | MedQA, MedMCQA, PubMedQA, MMLU-Med |
| MedRAG | Offline Benchmark | PubMed abstracts, Medical textbooks, Clinical guidelines |

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables
Create a `.env` file in the project root:
```
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_HOST=http://localhost:3000
OPENAI_API_KEY=your-openai-key   # used by RAGAS internally as LLM judge
```

### 3. Start Langfuse locally (optional — skip if using Langfuse Cloud)
```bash
docker-compose up langfuse
```

---

## Running Each Evaluator

### RAGAS Evaluation
```bash
python evaluation/ragas_eval.py
```
Scores logged to Langfuse: `ragas_faithfulness`, `ragas_context_precision`, `ragas_answer_correctness`

### PHI Leakage Check
```bash
python evaluation/phi_leakage_check.py
```
Scores logged to Langfuse: `phi_leakage_score` (1.0 = clean, 0.0 = PHI detected)

### BERTScore Evaluation
```bash
python evaluation/bertscore_eval.py
```
Scores logged to Langfuse: `bertscore_f1`

### MIRAGE Benchmark
```bash
python benchmarking/mirage_eval.py
```
Scores logged to Langfuse: `mirage_exact_match`, `mirage_retrieval_hit`

### MedRAG Benchmark
```bash
python benchmarking/medrag_eval.py
```
Scores logged to Langfuse: `medrag_answer_match`, `medrag_source_coverage`

---

## Integrating With Your RAG Pipeline

Replace `SAMPLE_DATA` in each script with real output from your pipeline:

```python
# Example: pass real pipeline output to RAGAS evaluator
from evaluation.ragas_eval import evaluate_and_log

pipeline_output = [
    {
        "question": user_query,
        "answer": llm_response,
        "contexts": retrieved_chunks,
        "ground_truth": validated_answer
    }
]

evaluate_and_log(query=user_query, data=pipeline_output)
```

---

## Viewing Results in Langfuse

1. Open Langfuse UI at `http://localhost:3000`
2. Navigate to **Traces** — each query run appears as a trace
3. Navigate to **Scores** — view metric trends over time
4. Set alerts on `phi_leakage_score < 1.0` for immediate HIPAA breach notification

---

## PHI Patterns Detected

The PHI leakage checker scans for:
- SSN (Social Security Number)
- MRN (Medical Record Number — Epic format)
- DOB (Date of Birth)
- Phone numbers
- Email addresses
- Patient names
- Physical addresses

Extend `PHI_PATTERNS` in `phi_leakage_check.py` with EHR-specific patterns as needed.
