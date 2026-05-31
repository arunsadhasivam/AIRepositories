# SolrSparseRetriever.py
# BM25-based sparse retriever using Apache Solr
# Schema matches langchain_pg_embedding table structure

import logging
import json
import urllib.request    # standard HTTP client
import urllib.parse      # URL encoding
from typing import List
from rag.retriever.BaseRetriever import BaseRetriever
from rag.retriever.Document import Document
from rag.exception.RetrieverException import RetrieverException
from langchain_core.retrievers import BaseRetriever as LangChainBaseRetriever
from langchain_core.documents import Document as LangChainDocument
from langchain_core.callbacks import CallbackManagerForRetrieverRun

logger = logging.getLogger(__name__)


class SolrSparseRetriever(BaseRetriever):
    """
    Sparse BM25 retriever using Apache Solr.
    Schema mirrors langchain_pg_embedding:
        uuid         -> Solr id field
        document     -> Solr document field (BM25 search target)
        cmetadata    -> Solr cmetadata field
        custom_id    -> Solr custom_id field
        collection_id-> Solr collection_id field
    """

    def __init__(self,
                 host: str = "localhost",              # Solr host
                 port: int = 8983,                     # Solr default port
                 core: str = "rag_core",               # Solr core name
                 collection_id: str = None):           # optional filter by collection
        """
        Initialize SolrSparseRetriever.

        Args:
            host: Solr host
            port: Solr port
            core: Solr core name
            collection_id: Optional collection filter (mirrors langchain collection)
        """
        super().__init__(name="SolrSparseRetriever")

        # Build Solr base URL
        self.base_url = f"http://{host}:{port}/solr/{core}"

        # Optional collection filter — mirrors langchain_pg_embedding collection_id
        self.collection_id = collection_id

        # Verify Solr is reachable
        self._verify_connection()

        logger.info(f"SolrSparseRetriever initialized at '{self.base_url}'")

    def _verify_connection(self):
        """Ping Solr to verify connection."""
        try:
            ping_url = f"{self.base_url}/admin/ping"  # Solr health check endpoint
            with urllib.request.urlopen(ping_url, timeout=5) as response:
                result = json.loads(response.read().decode())
                if result.get("status") != "OK":
                    raise RetrieverException("Solr ping failed")
            logger.info("SolrSparseRetriever: Connection verified")
        except Exception as e:
            raise RetrieverException(f"Solr connection failed: {str(e)}")

    def index_documents(self, documents: List[Document]):
        """
        Index documents into Solr matching langchain_pg_embedding schema.
        Call this after ingesting documents into pgvector to keep Solr in sync.

        Args:
            documents: List of Document objects to index
        """
        try:
            solr_docs = []
            for doc in documents:
                solr_docs.append({
                    "id": doc.id,                                       # maps to uuid
                    "document": doc.content,                            # maps to document column
                    "cmetadata": json.dumps(doc.metadata),              # maps to cmetadata column
                    "custom_id": doc.metadata.get("custom_id", ""),     # maps to custom_id column
                    "collection_id": doc.metadata.get("collection_id", "")  # maps to collection_id
                })

            # Serialize docs to JSON bytes
            payload = json.dumps(solr_docs).encode("utf-8")

            # POST to Solr update endpoint with commit=true to make docs searchable immediately
            update_url = f"{self.base_url}/update/json/docs?commit=true"
            req = urllib.request.Request(
                update_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req) as response:
                json.loads(response.read().decode())  # parse response
                logger.info(f"Indexed {len(solr_docs)} documents into Solr")

        except Exception as e:
            logger.error(f"SolrSparseRetriever: Indexing failed: {str(e)}")
            raise RetrieverException(f"Solr indexing error: {str(e)}")

    def retrieve(self, query: str, top_k: int = 3) -> List[Document]:
        """
        Retrieve documents using BM25 keyword search via Solr.

        Args:
            query: Search query string
            top_k: Number of top documents to return

        Returns:
            List of Document objects ranked by BM25 score
        """
        self.validate_query(query)  # validate using base class

        try:
            # URL encode query to handle special characters safely
            encoded_query = urllib.parse.quote(query)

            # Build filter query for collection_id if provided
            # mirrors langchain pgvector collection filtering
            fq = ""
            if self.collection_id:
                fq = f"&fq=collection_id:{urllib.parse.quote(self.collection_id)}"

            # Build Solr BM25 search URL
            # defType=edismax  -> enables BM25 scoring
            # qf=document      -> search in document field (mirrors langchain_pg_embedding.document)
            # fl               -> return these fields in response
            # rows             -> limit results to top_k
            # wt=json          -> return JSON response
            search_url = (
                f"{self.base_url}/select"
                f"?q={encoded_query}"
                f"&defType=edismax"                                      # BM25 scoring
                f"&qf=document"                                          # search in document field
                f"&fl=id,document,cmetadata,custom_id,collection_id,score"  # return all fields + score
                f"&rows={top_k}"                                         # limit to top_k
                f"&wt=json"                                              # JSON response
                f"{fq}"                                                  # optional collection filter
            )

            # Execute HTTP GET to Solr
            with urllib.request.urlopen(search_url, timeout=10) as response:
                result = json.loads(response.read().decode())  # parse JSON

            # Extract docs from Solr response structure
            solr_docs = result.get("response", {}).get("docs", [])

            # Convert Solr docs to your Document objects
            documents = []
            for solr_doc in solr_docs:

                # Parse cmetadata JSON string back to dict
                cmetadata_raw = solr_doc.get("cmetadata", "{}")
                try:
                    # cmetadata may be string or dict depending on Solr field type
                    metadata = json.loads(cmetadata_raw) if isinstance(cmetadata_raw, str) else cmetadata_raw
                except json.JSONDecodeError:
                    metadata = {}  # fallback to empty dict

                # Enrich metadata with collection_id and custom_id
                metadata["collection_id"] = solr_doc.get("collection_id", "")  # mirrors pg column
                metadata["custom_id"] = solr_doc.get("custom_id", "")          # mirrors pg column

                doc = Document(
                    id=str(solr_doc.get("id", "")),          # uuid
                    content=solr_doc.get("document", ""),     # document text
                    metadata=metadata,                         # enriched metadata
                    score=float(solr_doc.get("score", 0.0))   # BM25 score
                )
                documents.append(doc)

            logger.info(f"SolrSparseRetriever: Retrieved {len(documents)} docs for query '{query[:50]}'")
            return documents

        except Exception as e:
            logger.error(f"SolrSparseRetriever: BM25 retrieval failed: {str(e)}")
            raise RetrieverException(f"Solr BM25 retrieval error: {str(e)}")

    def close(self):
        """No persistent connection — Solr uses stateless HTTP."""
        logger.info("SolrSparseRetriever: No connection to close")

    def as_langchain_retriever(self):
        """
        Wraps HybridRetriever into a LangChain compatible retriever.
        Required for MultiQueryRetriever.from_llm() to accept it.
        """
        # Local reference to self (HybridRetriever) for use inside inner class
        vector  = self
        # Inner class that extends LangChain's BaseRetriever
        class LangChainAdapter(LangChainBaseRetriever):
            def _get_relevant_documents(
                self, 
                query: str, 
                *, 
                run_manager: CallbackManagerForRetrieverRun  # required by LangChain
            ):
                # Call HybridRetriever's retrieve method
                docs = vector.retrieve(query)

                # Convert your Document objects to LangChain Document objects
                return [
                    LangChainDocument(
                        page_content=str(doc.content) if doc.content is not None else "",   # map content -> page_content
                        metadata=doc.metadata if isinstance(doc.metadata, dict) else {}    # ensure dict     
                       )
                    for doc in docs
                ]

        return LangChainAdapter()  # return instance of adapter