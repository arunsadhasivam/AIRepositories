import os
import sys
import logging
import requests
import redis
LLM_MODEL = os.getenv('LLM_MODEL', 'mistral:7b-instruct-q2_K')
GUADRAIL_WARNING_MESSAGE=os.getenv('GUADRAIL_WARNING_MESSAGE')
GUADRAIL_TOPIC_CONTENT=os.getenv('GUADRAIL_TOPIC_CONTENT')
TEXT_EMBEDDING_MODEL = os.getenv('TEXT_EMBEDDING_MODEL', 'nomic-embed-text')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'default-local-rag')

#POSTGRES

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'rag')
DB_SUPERUSER = os.getenv('DB_SUPERUSER', '5432')
DB_SUPERUSER_PWD = os.getenv('DB_SUPERUSER_PWD', '5432')

#SOLR
SOLR_PORT = os.getenv('SOLR_PORT',default=8983)
SOLR_CORE = os.getenv('SOLR_CORE',default='rag_core')
# ── check Ollama is running ──
def check_ollama():
    try:
        # ping Ollama base URL
        ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        response = requests.get(f"{ollama_base_url}", timeout=3)
        if response.status_code == 200:
            logging.info("::::: HEALTH CHECK — Ollama        : UP ✅")
            return True
    except Exception:
        pass
    logging.error("::::: HEALTH CHECK — Ollama        : DOWN ❌")
    return False


# ── check Solr is running ──
def check_solr():
    try:
        # ping Solr admin endpoint
        response = requests.get(f"http://localhost:{SOLR_PORT}/solr/{SOLR_CORE}/admin/ping", timeout=3 )
        if response.status_code == 200:
            logging.info("::::: HEALTH CHECK — Solr          : UP ✅")
            return True
    except Exception:
        pass
    logging.error("::::: HEALTH CHECK — Solr          : DOWN ❌")
    return False


# ── check Redis/Memurai is running ──
def check_redis():
    try:
        # ping Redis using redis-py client
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', 6379)
        client = redis.Redis(host=redis_host, port=int(redis_port), socket_timeout=3)
        # ping returns True if connected
        client.ping()
        logging.info("::::: HEALTH CHECK — Redis/Memurai : UP ✅")
        return True
    except Exception:
        pass
    logging.error("::::: HEALTH CHECK — Redis/Memurai : DOWN ❌")
    return False


# ── check PostgreSQL/pgvector is running ──
def check_postgres():
    try:
        import psycopg2
        # connect using env vars
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', 5432),
            dbname=os.getenv('DB_NAME', 'rag'),
            user=os.getenv('DB_SUPERUSER'),
            password=os.getenv('DB_SUPERUSER_PWD'),
            connect_timeout=3
        )
        conn.close()
        logging.info("::::: HEALTH CHECK — PostgreSQL    : UP ✅")
        return True
    except Exception:
        pass
    logging.error("::::: HEALTH CHECK — PostgreSQL    : DOWN ❌")
    return False


# ── run all checks and exit if any fail ──


def getAvailabilityStatus():
    logging.info("::::: STARTUP HEALTH CHECKS RUNNING :::::")

    # collect results of all checks
    results = {
        "Ollama"    : check_ollama(),
        "Solr"      : check_solr(),
        "Redis"     : check_redis(),
        "PostgreSQL": check_postgres()
    }

    # find any failed checks
    failed = [name for name, status in results.items() if not status ]

    if failed:
        # print all failures and exit before app starts
        logging.error(f"::::: STARTUP FAILED — services down: {failed}")
        logging.error("::::: Fix the above services and restart the app.")
        sys.exit(1)  # exit with error code — app never starts
        

    logging.info("::::: ALL HEALTH CHECKS PASSED — Starting app :::::")
    return results