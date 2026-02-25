
import logging
import os
from rag.retriever.SparseSolrRetriever import SolrSparseRetriever
import uuid  # for generating unique document IDs

class SolrIndexer:
    """
    Handles Solr Indexing.
    """
    def index_to_solr(self, chunks):
            """
            Index document chunks into Solr for BM25 keyword search.
            Called after pgvector indexing to keep both in sync.

            Args:
                chunks (list): List of LangChain Document chunks
            """
            logging.info('::::: SOLR INDEXING BEGIN :::::')
            try:
                # Initialize Solr retriever
                solr = SolrSparseRetriever(
                    host=os.getenv("SOLR_HOST", "localhost"),   # Solr host from env
                    port=int(os.getenv("SOLR_PORT", 8983)),     # Solr port from env
                    core=os.getenv("SOLR_CORE", "rag_core")     # Solr core from env
                )

                # Convert LangChain Document chunks to your Document objects for Solr
                from rag.retriever.Document import Document as RetrieverDocument

                solr_docs = []
                for chunk in chunks:
                    solr_docs.append(
                        RetrieverDocument(
                            id=str(uuid.uuid4()),               # generate unique ID per chunk
                            content=chunk.page_content,          # maps to Solr document field
                            metadata=chunk.metadata,             # maps to Solr cmetadata field
                            score=0.0                            # no score on indexing
                        )
                    )

                # Index all chunks into Solr
                solr.index_documents(solr_docs)
                logging.info(f'::::: INSERT TO SOLR SUCCESSFULLY: {len(solr_docs)} chunks :::::')

            except Exception as e:
                # Log error but do NOT fail entire embed — pgvector already succeeded
                logging.error(f'::::: SOLR INDEXING FAILED (non-critical): {str(e)}')