import os
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.retrievers import MultiQueryRetriever
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_community.embeddings import OllamaEmbeddings

from rag.vectorstore.DistanceMetric import DistanceMetric
from rag.retriever.config.RetrieverConfig import RetrieverConfig
from rag.retriever import BaseRetriever,VectorStoreRetriever,HybridRetriever,SolrSparseRetriever
from rag.vectorstore.PgVectorStore import PgVectorStore
from agents.MathClassificationAgent import MathClassificationAgent
import json
import logging
logging.basicConfig(level=logging.DEBUG)
import os
LLM_MODEL = os.getenv('LLM_MODEL', 'mistral')
TEXT_EMBEDDING_MODEL = os.getenv('TEXT_EMBEDDING_MODEL', 'nomic-embed-text')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'default-local-rag')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'rag')
DB_SUPERUSER = os.getenv('DB_SUPERUSER', '5432')
DB_SUPERUSER_PWD = os.getenv('DB_SUPERUSER_PWD', '5432')

# Function to get the prompt templates for generating alternative questions and answering based on context
def get_prompt():
    QUERY_PROMPT = PromptTemplate(
        input_variables=["question"],
        template="""You are an AI language model assistant. Your task is to generate five
        different versions of the given user question to retrieve relevant documents from
        a vector database. By generating multiple perspectives on the user question, your
        goal is to help the user overcome some of the limitations of the distance-based
        similarity search. Provide these alternative questions separated by newlines.
        Original question: {question}""",
    )

    template = """Answer the question based ONLY on the following context:
    {context}
    Question: {question}
    """

    prompt = ChatPromptTemplate.from_template(template)

    return QUERY_PROMPT, prompt

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



# Main function to handle the query process
def query(query,search_type,user_role,pwd):
    try:
        if query:
            # Initialize the language model with the specified model name
            llm = ChatOllama(model=LLM_MODEL)
          
            # Get the prompt templates
            QUERY_PROMPT, prompt = get_prompt()
            #agent
            MathClassificationAgent.init()
            math_executor = MathClassificationAgent.create_math_agent(llm)
            # Set up the retriever to generate multiple queries using the language model and the query prompt
            logging.info(f'::::: Query EXECUTION :{query} , search_type:{search_type},user_role={user_role},pwd={pwd}')

            embedding_model = OllamaEmbeddings(model=TEXT_EMBEDDING_MODEL)
            #Step 1: vector store
            pgVectorStore = getPgVectorStore(user_role,pwd)
            vectorRetriever = VectorStoreRetriever(
                vector_store=pgVectorStore,              # your existing Chroma/pgvector db
                embedding_model=embedding_model,  # embedding model instance
                search_type="similarity"
            )
            if search_type==DistanceMetric.HYBRID.value:
                 # Step 2: Create sparse (BM25/keyword) retriever
                sparseRetriever = SolrSparseRetriever(
                    host="localhost",
                    port=8983,
                    core="rag_core",
                    collection_id=None   # or pass specific collection if needed
                )
                # Step 3: Create config with weights
                config = RetrieverConfig()
                config.vector_weight = 0.7   # 70% semantic search
                config.sparse_weight = 0.3   # 30% keyword search
                # Step 4: Create HybridRetriever with both retrievers
                hybridRetriever = HybridRetriever(vectorRetriever, sparseRetriever, config)

                 # Step 5: Use hybridRetriever as the LangChain retriever
                retriever = MultiQueryRetriever.from_llm(
                    hybridRetriever.as_langchain_retriever(),  # wrap to LangChain compatible
                    llm,
                    prompt=QUERY_PROMPT
                )
            else:
                logging.info(':::::: COSINE SIMILARITY SEARCH :::::')
                # Get the vector database instance
                #db = get_vector_db(user_role,pwd)
                retriever = MultiQueryRetriever.from_llm(
                    vectorRetriever.as_langchain_retriever(),
                    llm,
                    prompt=QUERY_PROMPT
                )

            classifier_prompt = PromptTemplate(
                input_variables=["query"],
                template="""Analyze this query and determine if it requires mathematical calculation.
                Query: {query}
                Respond with a JSON object with a single field "requires_math" set to true if the query needs mathematical calculation, 
                or false if it's a general knowledge or information retrieval question.
                JSON response:"""
            )
            classifier_chain = (
                    classifier_prompt 
                    | llm 
                    | StrOutputParser()
            )
        
            # Define the processing chain to retrieve context, generate the answer, and parse the output
            classification_response = classifier_chain.invoke(query)
            # Parse JSON response properly
            try:
                classification_result = json.loads(classification_response.strip())
                requires_math = classification_result.get("requires_math", False)
            except json.JSONDecodeError:
                # Fallback: check for boolean keywords
                requires_math = 'true' in classification_response.lower()
                logging.warning(f"::::: Failed to parse JSON, using fallback: {classification_response}")

            if requires_math:
                logging.debug(':::::  LOCAL PYTHON MATH FUNCTION:::::::::::')
                response = MathClassificationAgent.math(query)
            else:
                logging.debug('::::: OLLAMA RAG GENERATION:::::::::::::::')    
                rag_chain = (
                    {"context": retriever, "question": RunnablePassthrough()}
                    | prompt
                    | llm
                    | StrOutputParser()
                )
                response = rag_chain.invoke(query)
            return response
    except Exception as e:
        logging.error(f"'::::: Error processing query: {str(e)}")
        raise

   

  # Function to dynamically route between math agent and RAG chain
def dynamic_router(query):
    try:
        # Let the model decide if the query requires math
        classification_result = classifier_chain.invoke({"query": query})
        
        # Parse the JSON response
        try:
            classification = json.loads(classification_result)
            requires_math = classification.get("requires_math", False)
        except json.JSONDecodeError:
            # Fallback if the model doesn't return proper JSON
            requires_math = "true" in classification_result.lower() and "requires_math" in classification_result.lower()
        
        # Route based on classification
        if requires_math:
            logging.log('::::: MATH EXECUTOR::::::::::::::')
            return math_executor.run(query)
        else:
            logging.log("::::: OLLAMA LLM EXECUTOR:::::::::::::::::::")
            return rag_chain.invoke(query)
            
    except Exception as e:
        # Fallback to regular chain if anything fails
        logging.log(f"::::: Router error: {str(e)}")
        return rag_chain.invoke(query)

    return dynamic_router    