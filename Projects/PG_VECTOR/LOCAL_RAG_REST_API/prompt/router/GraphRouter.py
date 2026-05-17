import os
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.prompts import  PromptTemplate
from langchain_community.embeddings import OllamaEmbeddings
from rag.judge.JudgePipeline import run_judge_pipeline
from rag.vectorstore.DistanceMetric import DistanceMetric
from rag.retriever.config.RetrieverConfig import RetrieverConfig
from rag.retriever import BaseRetriever,VectorStoreRetriever,HybridRetriever,SolrSparseRetriever
from rag.vectorstore.PgVectorStore import PgVectorStore
from rag.guadrail.GuadRail import input_guardrail
from rag.guadrail.GuadRail import output_guardrail
from rag.guadrail.GuadRail import is_input_safe
from rag.guadrail.GuadRail import is_output_safe
from prompt.promptFactory import get_prompt
from rag.kvcache.kvContext import getKVStableContext
from typing import TypedDict,Literal
from langchain_community.chat_models import ChatOllama
import re
from langgraph.graph import StateGraph, START, END

from agents.MathClassificationAgent import MathClassificationAgent
import json
import logging
logging.basicConfig(level=logging.INFO)

TEXT_EMBEDDING_MODEL = os.getenv('TEXT_EMBEDDING_MODEL', 'nomic-embed-text')
LLM_MODEL = os.getenv('LLM_MODEL', 'mistral:7b-instruct-q2_K')
GUADRAIL_WARNING_MESSAGE=os.getenv('GUADRAIL_WARNING_MESSAGE')
GUADRAIL_TOPIC_CONTENT=os.getenv('GUADRAIL_TOPIC_CONTENT')
TEXT_EMBEDDING_MODEL = os.getenv('TEXT_EMBEDDING_MODEL', 'nomic-embed-text')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'default-local-rag')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'rag')
DB_SUPERUSER = os.getenv('DB_SUPERUSER', '5432')
DB_SUPERUSER_PWD = os.getenv('DB_SUPERUSER_PWD', '5432')
SOLR_PORT = os.getenv('SOLR_PORT',default=8983)
SOLR_CORE = os.getenv('SOLR_CORE',default='rag_core')

TOP_K = os.getenv('TOP_K',default=5)
#langfuse = Langfuse()

ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
llm = ChatOllama(model=LLM_MODEL,base_url=ollama_base_url)
# Get the prompt templates
QUERY_PROMPT, prompt = get_prompt()
MULTIQUERY_MAX_QUERY_GEN_LIMIT=os.getenv('MULTIQUERY_MAX_QUERY_GEN_LIMIT',2)

# Main function to handle the query process
def query(query, search_type, user_role, pwd):
    logging.info("-----------------------PROMPT.QUERY BEGIN--------------------------------------")
    """
    handle query and process input prompt using retriever (based on configured hybrid or cosine or other).
    Args:
        query : prompt query
        search_type: hybrid or cosine (kept for backward compatibility, routing now handled internally)
        user_role: pg_vector user name
        pwd: pg_vector password

    Returns:
        retriever response
    Raise :
        Exception
    """
    try:
        if query:
            # ── INPUT GUARDRAIL (commented out — preserve as-is) ──
            # input_result = input_guardrail(query, GUADRAIL_TOPIC_CONTENT)
            # if not is_input_safe(input_result, query):
            #  return 'INPUT PROMPT VERIFIER:'+GUADRAIL_WARNING_MESSAGE

            # Initialize math classification agent — preserved as-is
            MathClassificationAgent.init()
            math_executor = MathClassificationAgent.create_math_agent(llm)

            logging.info(f'::::: Query EXECUTION :{query} , search_type:{search_type},user_role={user_role},pwd={pwd}')

            # Initialize embedding model for pgvector
            embedding_model = OllamaEmbeddings(model=TEXT_EMBEDDING_MODEL)

            # Step 1: Build pgvector store and wrap as VectorStoreRetriever
            pgVectorStore = getPgVectorStore(user_role, pwd)
            vectorRetriever = VectorStoreRetriever(
                vector_store=pgVectorStore,
                embedding_model=embedding_model,
                search_type="similarity"
            )

            # Step 2: Run query through LangGraph router — routing handled internally
            # search_type is no longer used to branch here; LangGraph classifies the query
            response = configureAndProcessRetriever(query, vectorRetriever)

            logging.info("-----------------------PROMPT.QUERY END--------------------------------------")
            return response
    except Exception as e:
        logging.error(f"'::::: Error processing query: {str(e)}")
        raise

def getPgVectorStore(user_role,pwd):
        pg_vector_dsn = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={user_role} password={pwd}"
        pg_vector_admin_dsn = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_SUPERUSER} password={DB_SUPERUSER_PWD}"

        logging.info(f":::::: PG_VECTOR CONNECTION:::::{pg_vector_dsn}")
        #db = get_vector_db(user_role,pwd)
        pgVectorStore = PgVectorStore(
                connection_string=pg_vector_dsn,
                connection_string_admin=pg_vector_admin_dsn,
                collection_name=COLLECTION_NAME,
                dimension=768,   # match your embedding model dimension,
                user_role=user_role,
                enable_rls=True
            )
        return pgVectorStore

# ── Constants ─────────────────────────────────────────────────────────────────

# ICD-10 code pattern e.g. "J06.9", "A00", "Z23"
ICD_PATTERN = re.compile(r'\b[A-Z]\d{2}(\.\d{1,4})?\b')

# Common drug/medical keyword suffixes — extend as needed
DRUG_SUFFIXES = ("mg", "mcg", "dosage", "tablet", "capsule", "injection",
                 "syrup", "antibiotic", "vaccine", "insulin")

# LLM prompt to classify query as diagnostic or vague
CLASSIFIER_PROMPT = PromptTemplate.from_template(
    """You are a medical query classifier for a pediatric clinical RAG system.
Classify the query below into exactly one of these two categories:
- diagnostic: query describes symptoms, signs, or conditions to identify a disease
- vague: query is ambiguous, general, or unclear in clinical intent

Query: {query}

Respond with only one word: diagnostic or vague"""
)

# HyDE prompt — generates a hypothetical clinical document for vague queries
HYDE_PROMPT = PromptTemplate.from_template(
    """You are a clinical knowledge assistant.
Write a short hypothetical clinical document that would answer the following vague query.
Be factual and use pediatric clinical language.

Query: {query}

Hypothetical document:"""
)


# ── Graph State ───────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    query: str              # original user query
    query_type: str         # solr | diagnostic | vague | llm_classify
    hyde_document: str      # hypothetical document generated by HyDE (vague path only)
    response: str           # final answer returned to caller
    vector_retriever: object  # pgvector retriever passed in at graph entry


# ── Stage 1: Rule-Based Pre-Filter ───────────────────────────────────────────

def rule_based_classifier(state: GraphState) -> GraphState:
    """
    Stage 1: Fast rule-based classification — no LLM cost.
    Routes to 'solr' for single words, ICD codes, or drug keywords.
    Everything else passes to Stage 2 LLM classifier.
    """
    query = state["query"].strip()
    words = query.split()

    # Rule 1: single word → always Solr (e.g. "fever", "amoxicillin")
    if len(words) == 1:
        logging.info(":::::: RULE CLASSIFIER → solr (single word) ::::::")
        return {**state, "query_type": "solr"}

    # Rule 2: ICD-10 code detected → Solr (e.g. "ICD-10 J06.9 treatment")
    if ICD_PATTERN.search(query.upper()):
        logging.info(":::::: RULE CLASSIFIER → solr (ICD code detected) ::::::")
        return {**state, "query_type": "solr"}

    # Rule 3: known drug/dosage keyword detected → Solr
    if any(suffix in query.lower() for suffix in DRUG_SUFFIXES):
        logging.info(":::::: RULE CLASSIFIER → solr (drug keyword detected) ::::::")
        return {**state, "query_type": "solr"}

    # Rule 4: nothing matched → pass to LLM classifier
    logging.info(":::::: RULE CLASSIFIER → passing to LLM classifier ::::::")
    return {**state, "query_type": "llm_classify"}


# ── Stage 2: LLM Classifier ──────────────────────────────────────────────────

def llm_classifier(state: GraphState) -> GraphState:
    """
    Stage 2: LLM classifies as 'diagnostic' or 'vague'.
    Only called when rule-based stage could not decide.
    """
    query = state["query"]

    # Format and invoke the classifier prompt
    prompt_text = CLASSIFIER_PROMPT.format(query=query)
    result = llm.invoke(prompt_text)

    # Normalize label — strip whitespace and lowercase
    label = result.content.strip().lower()

    # Fallback to 'vague' if LLM returns unexpected output
    if label not in ("diagnostic", "vague"):
        logging.warning(f":::::: LLM CLASSIFIER unexpected label '{label}' → defaulting to vague ::::::")
        label = "vague"

    logging.info(f":::::: LLM CLASSIFIER → {label} ::::::")
    return {**state, "query_type": label}


# ── Conditional Edge: Route After Rule Classifier ─────────────────────────────

def route_after_rules(state: GraphState) -> Literal["llm_classifier", "solr_retrieval"]:
    """
    Conditional edge after rule-based classifier.
    solr → go straight to Solr retrieval.
    llm_classify → go to LLM classifier.
    """
    if state["query_type"] == "solr":
        return "solr_retrieval"
    return "llm_classifier"


# ── Conditional Edge: Route After LLM Classifier ─────────────────────────────

def route_after_llm(state: GraphState) -> Literal["diagnostic_retrieval", "vague_hyde"]:
    """
    Conditional edge after LLM classifier.
    diagnostic → hybrid retrieval directly.
    vague → HyDE first, then MultiQuery + hybrid retrieval.
    """
    if state["query_type"] == "diagnostic":
        return "diagnostic_retrieval"
    return "vague_hyde"


# ── Node: Solr-Only Retrieval ─────────────────────────────────────────────────

def solr_retrieval(state: GraphState) -> GraphState:
    """
    Keyword/ICD/single-word queries: Solr BM25 only.
    No pgvector, no MultiQuery, no HyDE.
    """
    logging.info(":::::: SOLR ONLY RETRIEVAL ::::::")

    # Build Solr sparse retriever — keyword-only, no vector component
    solr_retriever = SolrSparseRetriever(
        host="localhost",
        port=SOLR_PORT,
        core=SOLR_CORE,
        collection_id=None
    )

    # Wrap as LangChain-compatible retriever
    lc_retriever = solr_retriever.as_langchain_retriever()

    # # Get response + guardrail output check
    # response, output_result, retrieved_docs = getRetrieverAndGuadRailResponse(
    #     lc_retriever, state["query"]
    # )

    # # Output guardrail check — preserved from original
    # if output_result is not None and not is_output_safe(output_result, response):
    #     return {**state, "response": "OUTPUT :" + GUADRAIL_WARNING_MESSAGE}

    # # LLM-as-Judge scoring — preserved from original
    # response = getJudgeResponse(
    #     lc_retriever, None, state["query"], response, llm, retrieved_docs
    # )

    logging.info(":::::: FINAL RESPONSE AFTER SOLR SEARCH ::::::")
    return {**state, "response": lc_retriever}


# ── Node: Diagnostic Retrieval ────────────────────────────────────────────────

def diagnostic_retrieval(state: GraphState) -> GraphState:
    """
    Diagnostic symptom queries: hybrid retriever directly (pgvector 0.7 + Solr 0.3).
    Symptom queries embed well — HyDE not needed.
    """
    logging.info(":::::: DIAGNOSTIC HYBRID RETRIEVAL ::::::")

    # Build Solr sparse retriever
    sparse_retriever = SolrSparseRetriever(
        host="localhost",
        port=SOLR_PORT,
        core=SOLR_CORE,
        collection_id=None
    )

    # Configure hybrid weights: 70% semantic, 30% keyword — preserved from original
    config = RetrieverConfig()
    config.vector_weight = 0.7
    config.sparse_weight = 0.3
    config.top_k = TOP_K

    # Build hybrid retriever combining pgvector + Solr
    hybridRetriever = HybridRetriever(state["vector_retriever"], sparse_retriever, config)

    # Wrap as LangChain-compatible retriever
    retriever = hybridRetriever.as_langchain_retriever()

    # # Get response + guardrail output check
    # response, output_result, retrieved_docs = getRetrieverAndGuadRailResponse(
    #     retriever, state["query"]
    # )

    # # Output guardrail check — preserved from original
    # if output_result is not None and not is_output_safe(output_result, response):
    #     return {**state, "response": "OUTPUT :" + GUADRAIL_WARNING_MESSAGE}

    # # LLM-as-Judge scoring — preserved from original
    # response = getJudgeResponse(
    #     retriever, hybridRetriever, state["query"], response, llm, retrieved_docs
    # )

    logging.info(":::::: FINAL RESPONSE AFTER DIAGNOSTIC HYBRID SEARCH ::::::")
    return {**state, "response": hybridRetriever}


# ── Node: HyDE for Vague Queries ──────────────────────────────────────────────

def vague_hyde(state: GraphState) -> GraphState:
    """
    Vague queries: generate a hypothetical clinical document via HyDE.
    Bridges the semantic gap between a vague query and indexed documents.
    The generated document is used as the enriched query in vague_retrieval.
    """
    logging.info(":::::: HyDE GENERATION FOR VAGUE QUERY ::::::")

    # Ask LLM to generate a hypothetical document answering the vague query
    prompt_text = HYDE_PROMPT.format(query=state["query"])
    hyde_result = llm.invoke(prompt_text)

    # Store the hypothetical document — passed to vague_retrieval node
    hyde_document = hyde_result.content.strip()
    logging.info(":::::: HyDE DOCUMENT GENERATED ::::::")

    return {**state, "hyde_document": hyde_document}


# ── Node: Vague Retrieval (HyDE + MultiQuery + Hybrid) ───────────────────────

def vague_retrieval(state: GraphState) -> GraphState:
    """
    Vague queries: MultiQuery + hybrid retrieval using HyDE document as enriched query.
    MultiQuery generates rephrasings of the HyDE document to widen retrieval coverage.
    """
    logging.info(":::::: VAGUE MULTIQUERY HYBRID RETRIEVAL ::::::")

    # Use HyDE-generated document as the enriched query — not the original vague query
    enriched_query = state["hyde_document"]

    # Build Solr sparse retriever
    sparse_retriever = SolrSparseRetriever(
        host="localhost",
        port=SOLR_PORT,
        core=SOLR_CORE,
        collection_id=None
    )

    # Configure hybrid weights — preserved from original
    config = RetrieverConfig()
    config.vector_weight = 0.7
    config.sparse_weight = 0.3
    config.top_k = TOP_K

    # Build hybrid retriever
    hybridRetriever = HybridRetriever(state["vector_retriever"], sparse_retriever, config)

    # Wrap with MultiQuery — generates multiple rephrasings of enriched_query
    # QUERY_PROMPT preserved from original
    retriever = MultiQueryRetriever.from_llm(
        hybridRetriever.as_langchain_retriever(),
        llm,
        prompt=QUERY_PROMPT
    )

    # # Get response using enriched HyDE query — not original query
    # response, output_result, retrieved_docs = getRetrieverAndGuadRailResponse(
    #     retriever, enriched_query
    # )

    # # Output guardrail check — preserved from original
    # if output_result is not None and not is_output_safe(output_result, response):
    #     return {**state, "response": "OUTPUT :" + GUADRAIL_WARNING_MESSAGE}

    # # LLM-as-Judge — pass original query for faithful evaluation, not HyDE doc
    # response = getJudgeResponse(
    #     retriever, hybridRetriever, state["query"], response, llm, retrieved_docs
    # )

    logging.info(":::::: FINAL RESPONSE AFTER VAGUE HYBRID SEARCH ::::::")
    return {**state, "hyde_document": retriever}


# ── Build and Compile LangGraph ───────────────────────────────────────────────

def build_rag_graph() -> StateGraph:
    """
    Builds and compiles the LangGraph router with conditional edges.

    Graph flow:
    rule_based_classifier
        ├── solr         → solr_retrieval      → END
        └── llm_classify → llm_classifier
                            ├── diagnostic → diagnostic_retrieval → END
                            └── vague      → vague_hyde → vague_retrieval → END
    """
    graph = StateGraph(GraphState)

    # Register all nodes
    graph.add_node("rule_based_classifier", rule_based_classifier)
    graph.add_node("llm_classifier", llm_classifier)
    graph.add_node("solr_retrieval", solr_retrieval)
    graph.add_node("diagnostic_retrieval", diagnostic_retrieval)
    graph.add_node("vague_hyde", vague_hyde)
    graph.add_node("vague_retrieval", vague_retrieval)

    # Entry point — always starts here
    graph.set_entry_point("rule_based_classifier")

    # Conditional edge: after rule classifier → solr or llm_classifier
    graph.add_conditional_edges(
        "rule_based_classifier",
        route_after_rules,
        {
            "solr_retrieval": "solr_retrieval",
            "llm_classifier": "llm_classifier"
        }
    )

    # Conditional edge: after LLM classifier → diagnostic or vague_hyde
    graph.add_conditional_edges(
        "llm_classifier",
        route_after_llm,
        {
            "diagnostic_retrieval": "diagnostic_retrieval",
            "vague_hyde": "vague_hyde"
        }
    )

    # HyDE node always feeds into vague_retrieval
    graph.add_edge("vague_hyde", "vague_retrieval")

    # All retrieval nodes terminate the graph
    graph.add_edge("solr_retrieval", END)
    graph.add_edge("diagnostic_retrieval", END)
    graph.add_edge("vague_retrieval", END)

    return graph.compile()


# ── Public Entry Point — replaces original configureAndProcessRetriever ───────

def GraphBasedRetriever(query: str, vectorRetriever) -> str:
    """
    Replaces original configureAndProcessRetriever.
    Builds the LangGraph, runs query through the router, returns final response.
    search_type param removed — routing now handled internally by the graph.

    Args:
        query: user query string
        vectorRetriever: pgvector VectorStoreRetriever instance

    Returns:
        final response string
    """
    # Build and compile the LangGraph router
    rag_graph = build_rag_graph()

    # Initial state — all fields required by GraphState
    initial_state: GraphState = {
        "query": query,
        "query_type": "",       # set by rule_based_classifier
        "hyde_document": "",    # set by vague_hyde if vague path taken
        "response": "",         # set by whichever retrieval node runs
        "vector_retriever": vectorRetriever
    }

    # Invoke the graph — LangGraph handles node execution and edge routing
    final_state = rag_graph.invoke(initial_state)

    logging.info(":::::: FINAL RESPONSE AFTER LANGGRAPH ROUTING ::::::")
    return final_state["response"]