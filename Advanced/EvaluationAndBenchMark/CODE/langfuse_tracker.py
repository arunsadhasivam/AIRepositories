# langfuse_tracker.py
# Centralised Langfuse tracker used by all evaluation and benchmarking scripts.
# Every eval result is logged as a Langfuse score so you can monitor metric
# drift over time in the Langfuse UI.

from langfuse import Langfuse  # Langfuse Python SDK

# ---------------------------------------------------------------------------
# Initialise the Langfuse client.
# Set LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST in your .env
# or export them as environment variables before running any eval script.
# ---------------------------------------------------------------------------
langfuse = Langfuse(
    public_key="your-public-key",    # replace with your Langfuse public key
    secret_key="your-secret-key",    # replace with your Langfuse secret key
    host="http://localhost:3000"      # use https://cloud.langfuse.com for cloud
)


def log_score(trace_id: str, metric_name: str, score: float, comment: str = "") -> None:
    """
    Log a single numeric score against an existing Langfuse trace.

    Args:
        trace_id   : Langfuse trace ID returned when the trace was created.
        metric_name: Name of the metric e.g. 'ragas_faithfulness', 'bertscore'.
        score      : Float value between 0.0 and 1.0.
        comment    : Optional human-readable note stored alongside the score.
    """
    # Create a score object on the trace — visible in the Langfuse dashboard
    langfuse.score(
        trace_id=trace_id,       # links score to the correct trace/query run
        name=metric_name,        # metric label shown in Langfuse UI
        value=score,             # numeric score
        comment=comment          # optional context note
    )
    print(f"[Langfuse] Logged '{metric_name}' = {score:.4f} for trace {trace_id}")


def create_trace(query: str, metadata: dict = None):
    """
    Create a new Langfuse trace for a single RAG query run.
    Returns the trace object whose .id is passed to log_score().

    Args:
        query   : The user query being evaluated.
        metadata: Optional dict with extra context (e.g. retriever type).
    """
    # Start a trace — this represents one end-to-end RAG query evaluation
    trace = langfuse.trace(
        name="rag-evaluation",      # trace group name shown in Langfuse UI
        input=query,                # raw user query
        metadata=metadata or {}     # attach retriever type, model name, etc.
    )
    return trace  # caller uses trace.id to attach scores
