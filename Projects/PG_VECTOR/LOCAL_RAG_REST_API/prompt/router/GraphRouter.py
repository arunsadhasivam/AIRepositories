import re
import logging
from typing import TypedDict, Literal, Any,Annotated

from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOllama
from rag.retriever.config.RetrieverConfig import RetrieverConfig
from rag.retriever import HybridRetriever, SolrSparseRetriever, VectorStoreRetriever
from langgraph.graph import StateGraph, END

logging.basicConfig(level=logging.INFO)

class GraphState(TypedDict):
    query: str
    query_type: str
    hyde_document: str
    response: Annotated[Any, lambda x, y: y]   # last-write-wins, no serialization
    vector_retriever: Annotated[Any, lambda x, y: y]
    hybrid_retriever: Annotated[Any, lambda x, y: y]      



class GraphRouter:
    ICD_PATTERN = re.compile(r'\b[A-Z]\d{2}(\.\d{1,4})?\b')
    DRUG_SUFFIXES = (
        "mg", "mcg", "dosage", "tablet", "capsule", "injection",
        "syrup", "antibiotic", "vaccine", "insulin"
    )

    CLASSIFIER_PROMPT = PromptTemplate.from_template(
        """You are a medical query classifier for a pediatric clinical RAG system.
Classify the query below into exactly one of these two categories:
- diagnostic: query describes symptoms, signs, or conditions to identify a disease
- vague: query is ambiguous, general, or unclear in clinical intent

Query: {query}

Respond with only one word: diagnostic or vague"""
    )

    HYDE_PROMPT = PromptTemplate.from_template(
        """You are a clinical knowledge assistant.
Write a short hypothetical clinical document that would answer the following vague query.
Be factual and use pediatric clinical language.

Query: {query}

Hypothetical document:"""
    )

    def __init__(
        self,
        llm: ChatOllama,
        query_prompt: PromptTemplate,
        prompt: PromptTemplate,
        solr_host: str = "localhost",
        solr_port: int = 8983,
        solr_core: str = "rag_core",
        top_k: int = 5,
    ):
        self.llm = llm
        self.query_prompt = query_prompt
        self.prompt = prompt
        self.solr_host = solr_host
        self.solr_port = solr_port
        self.solr_core = solr_core
        self.top_k = int(top_k)
        self.rag_graph = self.build_rag_graph()

    def route(self, query: str, search_type:str,vector_retriever: VectorStoreRetriever) -> Any:
        initial_state: GraphState = {
            "query": query,
            "search_type": search_type,
            "query_type": "",
            "hyde_document": "",
            "response": None,
            "vector_retriever": vector_retriever,
            "hybrid_retriever": None,   # add this
        }
        final_state = self.rag_graph.invoke(initial_state)
        logging.info(f":::::: FINAL RESPONSE AFTER LANGGRAPH ROUTING ::::::{final_state}")
        #return final_state["response"]
        return final_state["response"], final_state["hybrid_retriever"]  # return tuple

    def build_rag_graph(self) -> StateGraph:
        graph = StateGraph(GraphState)
        graph.add_node("rule_based_classifier", self.rule_based_classifier)
        graph.add_node("llm_classifier", self.llm_classifier)
        graph.add_node("solr_retrieval", self.solr_retrieval)
        graph.add_node("diagnostic_retrieval", self.diagnostic_retrieval)
        graph.add_node("vague_hyde", self.vague_hyde)
        graph.add_node("vague_retrieval", self.vague_retrieval)
        graph.set_entry_point("rule_based_classifier")
        graph.add_conditional_edges(
            "rule_based_classifier",
            self.route_after_rules,
            {
                "solr_retrieval": "solr_retrieval",
                "llm_classifier": "llm_classifier",
            },
        )
        graph.add_conditional_edges(
            "llm_classifier",
            self.route_after_llm,
            {
                "diagnostic_retrieval": "diagnostic_retrieval",
                "vague_hyde": "vague_hyde",
            },
        )
        graph.add_edge("vague_hyde", "vague_retrieval")
        graph.add_edge("solr_retrieval", END)
        graph.add_edge("diagnostic_retrieval", END)
        graph.add_edge("vague_retrieval", END)
        return graph.compile()

    def rule_based_classifier(self, state: GraphState) -> GraphState:
        query = state["query"].strip()
        words = query.split()
        if len(words) == 5:
            logging.info(":::::: RULE CLASSIFIER ? solr (single word) ::::::")
            return {**state, "query_type": "solr"}
        if self.ICD_PATTERN.search(query.upper()):
            logging.info(":::::: RULE CLASSIFIER ? solr (ICD code detected) ::::::")
            return {**state, "query_type": "solr"}
        if any(suffix in query.lower() for suffix in self.DRUG_SUFFIXES):
            logging.info(":::::: RULE CLASSIFIER ? solr (drug keyword detected) ::::::")
            return {**state, "query_type": "solr"}
        logging.info(":::::: RULE CLASSIFIER ? passing to LLM classifier ::::::")
        return {**state, "query_type": "llm_classify"}

    def llm_classifier(self, state: GraphState) -> GraphState:
        query = state["query"]
        prompt_text = self.CLASSIFIER_PROMPT.format(query=query)
        result = self.llm.invoke(prompt_text)
        label = result.content.strip().lower()
        if label not in ("diagnostic", "vague"):
            logging.warning(
                f":::::: LLM CLASSIFIER unexpected label '{label}' ? defaulting to vague ::::::"
            )
            label = "vague"
        logging.info(f":::::: LLM CLASSIFIER ? {label} ::::::")
        return {**state, "query_type": label}

    def route_after_rules(self, state: GraphState) -> Literal["llm_classifier", "solr_retrieval"]:
        if state["query_type"] == "solr":
            return "solr_retrieval"
        return "llm_classifier"

    def route_after_llm(self, state: GraphState) -> Literal["diagnostic_retrieval", "vague_hyde"]:
        if state["query_type"] == "diagnostic":
            return "diagnostic_retrieval"
        return "vague_hyde"

    def solr_retrieval(self, state: GraphState) -> GraphState:
        logging.info(":::::: SOLR ONLY RETRIEVAL ::::::")
        solr_retriever = SolrSparseRetriever(
            host=self.solr_host,
            port=self.solr_port,
            core=self.solr_core,
            collection_id=None,
        )
        return {**state, "response": solr_retriever.as_langchain_retriever(),"hybrid_retriever": None}

    def diagnostic_retrieval(self, state: GraphState) -> GraphState:
        logging.info(":::::: DIAGNOSTIC HYBRID RETRIEVAL ::::::")
        sparse_retriever = SolrSparseRetriever(
            host=self.solr_host,
            port=self.solr_port,
            core=self.solr_core,
            collection_id=None,
        )
        config = RetrieverConfig()
        config.vector_weight = 0.7
        config.sparse_weight = 0.3
        config.top_k = self.top_k
        hybrid_retriever = HybridRetriever(state["vector_retriever"], sparse_retriever, config)
        return {**state, "response": hybrid_retriever.as_langchain_retriever(), "hybrid_retriever": hybrid_retriever}

    def vague_hyde(self, state: GraphState) -> GraphState:
        logging.info(":::::: HyDE GENERATION FOR VAGUE QUERY ::::::")
        prompt_text = self.HYDE_PROMPT.format(query=state["query"])
        hyde_result = self.llm.invoke(prompt_text)
        hyde_document = hyde_result.content.strip()
        logging.info(":::::: HyDE DOCUMENT GENERATED ::::::")
        return {**state, "hyde_document": hyde_document}

    def vague_retrieval(self, state: GraphState) -> GraphState:
        logging.info(":::::: VAGUE MULTIQUERY HYBRID RETRIEVAL ::::::")
        enriched_query = state["hyde_document"]
        sparse_retriever = SolrSparseRetriever(
            host=self.solr_host,
            port=self.solr_port,
            core=self.solr_core,
            collection_id=None,
        )
        config = RetrieverConfig()
        config.vector_weight = 0.7
        config.sparse_weight = 0.3
        config.top_k = self.top_k
        hybrid_retriever = HybridRetriever(state["vector_retriever"], sparse_retriever, config)
        multi_query_retriex1ver = MultiQueryRetriever.from_llm(
            hybrid_retriever.as_langchain_retriever(),
            self.llm,
            prompt=self.query_prompt,
        )
        return {**state, "response": multi_query_retriever,"hybrid_retriever": hybrid_retriever}


def GraphBasedRetriever(
    query: str,
    search_type: str,
    vector_retriever:VectorStoreRetriever,
    llm: ChatOllama,
    query_prompt: PromptTemplate,
    prompt: PromptTemplate,
    solr_port: int = 8983,
    solr_core: str = "rag_core",
    top_k: int = 5,
) -> Any:
    
    logging.info(f"::::: GraphBasedRetriever received query='{query}' with search_type='{search_type}'")
    router = GraphRouter(
        llm=llm,
        query_prompt=query_prompt,
        prompt=prompt,
        solr_port=solr_port,
        solr_core=solr_core,
        top_k=top_k,
    )
    return router.route(query, search_type,vector_retriever)
