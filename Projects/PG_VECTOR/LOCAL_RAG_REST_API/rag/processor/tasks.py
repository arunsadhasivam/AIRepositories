"""
tasks.py — Celery task wrapping your existing embed() pipeline
Broker : Redis (OSS, free)
Pattern: embed() logic copy-pasted unchanged — Celery adds async + retry + DLQ on top
DLQ    : Celery native on_failure() hook → handle_dead_letter task → JSON Lines log file
"""

import os
import uuid
import json
import logging
import traceback
from datetime import datetime

from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from kombu import Queue, Exchange

# ── Your existing imports — completely unchanged ───────────────────────────────
import numpy as np
import psycopg2
from sqlalchemy.exc import OperationalError, ProgrammingError
from langchain_community.embeddings import OllamaEmbeddings
from embeddings import DocumentEmbedding
from prompt.query import getPgVectorStore
from rag.retriever.Document import Document as RagDocument


# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
REDIS_URL            = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TEXT_EMBEDDING_MODEL = os.getenv("TEXT_EMBEDDING_MODEL", "nomic-embed-text")
DLQ_QUEUE_NAME       = "dead_letter"                    # Dedicated Celery queue for failures
DLQ_LOG_PATH         = os.getenv("DLQ_LOG_PATH", "dlq_failures.json")  # JSON Lines log


# ═══════════════════════════════════════════════════════════════════════════════
# Celery App
# ═══════════════════════════════════════════════════════════════════════════════

app = Celery("rag_pipeline", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(

    # ── Two queues only — embed (main) and dead_letter (DLQ) ──────────────────
    task_queues=(
        Queue("embed",       Exchange("default", type="direct"), routing_key="embed"),
        Queue("dead_letter", Exchange("default", type="direct"), routing_key="dead_letter"),
    ),
    task_default_queue="embed",

    # ── Reliability settings ───────────────────────────────────────────────────
    task_acks_late             = True,   # ACK after task finishes — no lost jobs on crash
    task_reject_on_worker_lost = True,   # Re-queue if worker process dies mid-task
    worker_prefetch_multiplier = 1,      # One task per worker — fair dispatch

    # ── Serialization ──────────────────────────────────────────────────────────
    task_serializer   = "json",          # JSON — inspectable via redis-cli
    result_serializer = "json",
    accept_content    = ["json"],

    # ── Result TTL ─────────────────────────────────────────────────────────────
    result_expires    = 3600,            # Keep task results in Redis for 1 hour

    # ── Timeouts ───────────────────────────────────────────────────────────────
    task_soft_time_limit = 300,          # 5 min soft — raises SoftTimeLimitExceeded
    task_time_limit      = 360,          # 6 min hard — SIGKILL ceiling

    timezone   = "UTC",
    enable_utc = True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# embed_task
# Your embed() logic is copy-pasted here with MINIMAL changes:
#   Change 1: Takes file_path (str) instead of file object — Flask file not
#             serializable through Redis. Caller saves file before dispatching.
#   Change 2: on_failure() hook added — Celery calls this automatically after
#             all retries exhausted. Routes to dead_letter queue.
#   Change 3: SoftTimeLimitExceeded + retry() added around your existing logic.
# Everything else inside is your original code untouched.
# ═══════════════════════════════════════════════════════════════════════════════

@app.task(
    bind=True,                           # 'self' gives access to retry(), on_failure()
    name="tasks.embed_task",
    queue="embed",
    max_retries=3,                       # Retry 3 times — then on_failure() fires
    acks_late=True,
    soft_time_limit=300,                 # 5 min soft limit per attempt
    time_limit=360,                      # 6 min hard limit per attempt
)
def embed_task(self, file_path: str, user_role: str, pwd: str,
               enable_pii_masking: bool = True):
    """
    Async Celery task wrapping your existing embed() pipeline.
    Caller dispatches with embed_task.delay(file_path, user_role, pwd)
    and gets task_id back immediately — no blocking.
    
    Args:
        file_path         : Absolute path to temp file saved by caller before dispatch
        user_role         : DB role for RLS (row-level security)
        pwd               : DB password for this role
        enable_pii_masking: Whether to run PII masking on chunks
    """

    # example retry error message
    # if variable wrong fie_path
    #rag.processor.tasks - WARNING - embed_task:RETRY | attempt=1/3 | error=name 'fie_path' is not defined
    # retry allows robust chunking to avoid ingestion failure knowledge source never get missed because of network issue.
    try:

        # ══════════════════════════════════════════════════════════════════════
        # YOUR EXISTING embed() LOGIC STARTS HERE — UNCHANGED
        # Only difference: file_path used directly instead of file object
        # ══════════════════════════════════════════════════════════════════════

        # Log start of embedding process
        logging.info(f'::::: QUEUE TASK TO BEGIN EMBEDDING TO VECTOR DB:BEGIN:::{user_role}')

        # Validate that file exists at path (replaces your file object check)
        if not file_path or not os.path.exists(file_path):
            # Log error for missing file
            logging.error('No file provided or empty filename')
            # Return False — non-retriable, file is gone
            return False

        # Load document and split into chunks using Docling
        embedder = DocumentEmbedding.DocumentEmbedder()                    # Your existing service class
        chunks = embedder.load_and_split_data(file_path)

        # Validate that chunks were created
        if not chunks or len(chunks) == 0:
            # Log error for empty chunks
            logging.error('No chunks created from document')
            # Return False — non-retriable, corrupt/empty file
            return False

        # Apply PII masking if enabled
        if enable_pii_masking:
            # Mask PII in all chunks
            logging.info("::::: MASKING IN PROCESS ::::::: BEGIN")
            chunks = embedder.create_mask(chunks)
            logging.info("::::: MASKING IN PROCESS ::::::: END")

        # Get vector database connection using user credentials
        db = getPgVectorStore(user_role, pwd)

        logging.info(f'::::: INSERT TO VECTOR DB:BEGIN {user_role}:::')

        # Step 1 - Convert LangChain chunks to RagDocument
        rag_docs = [
            RagDocument(
                id=str(uuid.uuid4()),
                content=chunk.page_content,
                metadata=chunk.metadata
            )
            for chunk in chunks
        ]

        # Step 2 - Generate embeddings using same model as search
        embedding_model = OllamaEmbeddings(model=TEXT_EMBEDDING_MODEL, show_progress=True)
        vectors = embedding_model.embed_documents([doc.content for doc in rag_docs])
        numpy_vectors = [np.array(v, dtype=np.float32) for v in vectors]  # convert list → numpy array
        # Step 3 - Insert into PgVectorStore
        logging.info(f'::::: INSERT TO VECTOR DB:BEGIN {user_role} :::::')
        try:
            db.add_documents(rag_docs, embeddings=numpy_vectors)
        except ProgrammingError as e:
            logging.info(f'::::: INSERT TO SOLR DB FAILED :::::')
            return False

        logging.info(f'::::: INSERT TO SOLR DB:END {user_role} :::::')

        # Validate database connection was established
        if not db:
            # Log error for failed database connection
            logging.error('Failed to get vector database connection')
            # Return False — will be caught by except below and retried
            return False

        # Insert chunks into vector database
        try:
            # Log start of database insertion
            logging.info(f'::::: INSERT TO SOLR DB:BEGIN {user_role} :::::')
            # Index same chunks into Solr for BM25 keyword search
            embedder.solrIndexer.index_to_solr(chunks)
            # Log successful insertion
            logging.info('::::: INSERT TO SOLR DB SUCESSFULLY:END :::::')

        except ProgrammingError as e:
            # Log database programming error
            logging.error(f'Database programming error: {str(e)}')
            print(str(e))
            # Check if error is permission-related
            if "row-level security" in str(e).lower() or "permission denied" in str(e).lower():
                # Log permission error
                logging.error('Permission denied for database operation')
                # Non-retriable — permission won't fix on retry
                return False
            else:
                # Re-raise — retriable, caught by outer except below
                return False

        except psycopg2.errors.InsufficientPrivilege as e:
            # Log insufficient privilege error
            print(f'InsufficientPrivilege :: {str(e)}')
            logging.error(f'Insufficient database privileges: {str(e)}')
            # Non-retriable — return False directly
            return False

        except OperationalError as e:
            # Log operational error — retriable (DB connection blip)
            print(f'OperationalError :: {str(e)}')
            logging.error(f'Database operational error: {str(e)}')
            # Re-raise — caught by outer except below, triggers retry
            return False

        # Log successful embedding with chunk count
        logging.info(f'Successfully embedded {len(chunks)} chunks for user: {user_role}')
        # Return True to indicate success
        return True

        # ══════════════════════════════════════════════════════════════════════
        # YOUR EXISTING embed() LOGIC ENDS HERE
        # ══════════════════════════════════════════════════════════════════════

    except SoftTimeLimitExceeded:
        # ── Celery addition: soft timeout hit — retry ──────────────────────────
        logger.error(
            "embed_task:SOFT_TIMEOUT | user=%s | attempt=%d/%d",
            user_role, self.request.retries + 1, self.max_retries
        )
        # Retry with exponential backoff: 10s → 20s → 40s
        raise self.retry(
            exc=SoftTimeLimitExceeded("Soft time limit exceeded"),
            countdown=2 ** self.request.retries * 10
        )

    except Exception as exc:
        # ── Celery addition: retry with exponential backoff ────────────────────
        retry_count = self.request.retries
        logger.warning(
            "embed_task:RETRY | attempt=%d/%d | error=%s",
            retry_count + 1, self.max_retries, str(exc)
        )

        if retry_count >= self.max_retries:
            # All retries exhausted — re-raise so Celery fires on_failure() below
            logger.error(
                "embed_task:MAX_RETRIES_EXHAUSTED | user=%s | error=%s",
                user_role, str(exc)
            )
            raise                                        # Triggers on_failure() automatically

        # Retry — exponential backoff: 10s → 20s → 40s
        raise self.retry(exc=exc, countdown=2 ** retry_count * 10)

    finally:
        # ── Your existing finally block — completely unchanged ─────────────────
        if file_path and os.path.exists(file_path):
            try:
                # Delete temporary file
                os.remove(file_path)
                # Log successful cleanup
                logging.info(f'Temporary file removed: {file_path}')
            except Exception as e:
                # Log error during cleanup
                logging.error(f'Error removing temporary file {file_path}: {str(e)}')

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Celery built-in hook — fires automatically after all retries exhausted.
        No manual call needed — Celery triggers this when max_retries is hit.

        Args:
            exc     : Exception that caused the final failure
            task_id : Celery task UUID
            args    : Positional args [file_path, user_role, pwd, ...]
            kwargs  : Keyword args
            einfo   : ExceptionInfo with full traceback
        """
        # ── Extract args safely — never log password ───────────────────────────
        file_path_arg = args[0] if len(args) > 0 else "unknown"  # file_path is args[0]
        user_role_arg = args[1] if len(args) > 1 else "unknown"  # user_role is args[1]
        # args[2] is pwd — never extracted, never logged

        logger.error(
            "embed_task:ON_FAILURE | task_id=%s | user=%s | file=%s | error=%s",
            task_id, user_role_arg, file_path_arg, str(exc)
        )

        # ── Build sanitized DLQ payload — no passwords ─────────────────────────
        dlq_payload = {
            "task_id"    : task_id,                      # Celery task UUID for tracing
            "task_name"  : self.name,                    # 'tasks.embed_task'
            "file_path"  : file_path_arg,                # Original file path
            "user_role"  : user_role_arg,                # User role — no pwd stored
            "error"      : str(exc),                     # Exception message
            "traceback"  : str(einfo.traceback),         # Full traceback for debugging
            "failed_at"  : datetime.utcnow().isoformat(), # UTC timestamp of final failure
            "retry_count": self.max_retries,             # Total retries attempted
            "status"     : "FAILED",                     # Terminal status
        }

        # ── Dispatch to dead_letter queue via Celery ───────────────────────────
        # handle_dead_letter task picks this up from the dead_letter queue
        handle_dead_letter.apply_async(
            kwargs={"payload": dlq_payload},
            queue=DLQ_QUEUE_NAME
        )

        logger.error(
            "embed_task:ROUTED_TO_DLQ | task_id=%s | user=%s",
            task_id, user_role_arg
        )


# ═══════════════════════════════════════════════════════════════════════════════
# handle_dead_letter
# DLQ consumer task — separate worker on dead_letter queue
# Persists failure metadata to JSON Lines file for ops inspection/replay
# ═══════════════════════════════════════════════════════════════════════════════

@app.task(
    bind=True,
    name="tasks.handle_dead_letter",
    queue="dead_letter",
    max_retries=0,                       # Terminal — never retries
    acks_late=True,
)
def handle_dead_letter(self, payload: dict):
    """
    DLQ consumer — persists permanently failed task metadata to JSON Lines file.
    Ops team reads dlq_failures.json to inspect and replay failures.

    Inspect : cat dlq_failures.json | python -m json.tool
    Replay  : embed_task.apply_async(args=[file_path, user_role, pwd], queue='embed')

    Args:
        payload : Sanitized failure dict from embed_task.on_failure()
    """
    logger.error(
        "handle_dead_letter:RECEIVED | task_id=%s | user=%s | error=%s",
        payload.get("task_id"),
        payload.get("user_role"),
        payload.get("error")
    )

    try:
        # ── Append to JSON Lines file — one JSON object per line ──────────────
        # JSON Lines: each line is a valid JSON object — easy to grep/parse
        # cat dlq_failures.json | python -m json.tool  ← pretty print all failures
        with open(DLQ_LOG_PATH, "a") as f:             # 'a' = append, never overwrites
            f.write(json.dumps(payload) + "\n")         # One record per line

        logger.info(
            "handle_dead_letter:PERSISTED | task_id=%s | log=%s",
            payload.get("task_id"), DLQ_LOG_PATH
        )

    except Exception as e:
        # ── Never raise from DLQ handler — last line of defense ───────────────
        logger.critical(
            "handle_dead_letter:PERSIST_FAILED | task_id=%s | error=%s",
            payload.get("task_id"), str(e)
        )



# ═══════════════════════════════════════════════════════════════════════════════
# Worker startup
# ═══════════════════════════════════════════════════════════════════════════════

"""
# Terminal 1 — main embed workers
celery -A processor.tasks worker --queues=embed --concurrency=2 --loglevel=info

# Terminal 2 — dead letter worker (low priority, 1 concurrent)
celery -A processor.tasks worker --queues=dead_letter --concurrency=1 --loglevel=info

# Terminal 3 — Flower UI (free OSS dashboard)
pip install flower
celery -A tasks flower --port=5555
# http://localhost:5555 — see all tasks, retries, failures live

# Inspect DLQ failures
cat dlq_failures.json | python -m json.tool
"""
