import os
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
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


from agents.MathClassificationAgent import MathClassificationAgent
import json
import logging
logging.basicConfig(level=logging.INFO)

# import phoenix as px
# from phoenix.client import Client
# client = Client()
from langfuse.callback import CallbackHandler
from langfuse import Langfuse
import os
# initialize langfuse handler once
langfuse_handler = CallbackHandler(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL")
)

print("::::: LANGFUSE SK::::::", os.getenv("LANGFUSE_SECRET_KEY"))
print("::::: LANGFUSE PK:::::", os.getenv("LANGFUSE_PUBLIC_KEY"))
print("::::: LANGFUSE HOST:::::", os.getenv("LANGFUSE_BASE_URL"))

LLM_MODEL = os.getenv('LLM_MODEL', 'mistral')
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
langfuse = Langfuse()

ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
llm = ChatOllama(model=LLM_MODEL,base_url=ollama_base_url)
# Get the prompt templates
QUERY_PROMPT, prompt = get_prompt()

def verify_langfuse():
    check = langfuse.auth_check()
    logging.info(f"::::: Langfuse auth check: {check}")
    return check
#verify_langfuse()

def get_langfuse_prompt(name: str) -> PromptTemplate:
    # pull prompt from Langfuse UI
    prompt = langfuse.get_prompt(name)
    # compile with variable
    template = prompt.compile(query="{{query}}")
    # convert to LangChain PromptTemplate
    return PromptTemplate(
        input_variables=["query"],
        template=prompt.prompt  # raw template string
    )


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
          
            hybridRetriever = None
            # ── INPUT GUADTRAIL ──
            input_result = input_guardrail(query, GUADRAIL_TOPIC_CONTENT)
            if not is_input_safe(input_result, query):
             return 'INPUT PROMPT VERIFIER:'+GUADRAIL_WARNING_MESSAGE  # blocked early, never hits ret
          
          
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
                    port=SOLR_PORT,
                    core=SOLR_CORE,
                    collection_id=None   # or pass specific collection if needed
                )
                # Step 3: Create config with weights
                config = RetrieverConfig()
                config.vector_weight = 0.7   # 70% semantic search
                config.sparse_weight = 0.3   # 30% keyword search
                config.top_k = TOP_K
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


            #prompt = langfuse.get_prompt("math_prompt")
            #math_prompt_template = langfuse.get_prompt("math_prompt",  label="latest")
            #logging.info(f'::::: MATH TEMPLATE :::::::math_prompt_template:{math_prompt_template}')
            # GET RETRIEVER     
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
            langfuse.trace(name="math-prompt", input={"query": query})
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
                #chunk order stabilization - Deterministic Chunk Ordering for KV Cache Prefix Stability
                # similar to sort A-z alphabets in array based on alphabet value (a-0 ,z -26)
                # Same chunk content → same hash → same sort position → every time, guaranteed.
                retrieved_docs = retriever.invoke(query)
                # sort chunks deterministically — same docs always same order → stable prefix → KV cache hit
                stable_context = getKVStableContext(retrieved_docs)
                rag_chain = (
                    {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
                    | prompt
                    | llm
                    | StrOutputParser()
                )
            response = rag_chain.invoke({"context": stable_context, "question": query})

            # ── OUTPUT GUADTRAIL guadtrail handler ──
            retrieved_context = retriever.invoke(query)
            retrieved_context_text = " ".join([doc.page_content for doc in retrieved_context])
            output_result = output_guardrail(query, retrieved_context_text, response)
            if not is_output_safe(output_result, response):
                return 'OUTPUT :'+GUADRAIL_WARNING_MESSAGE
            # ── END ADD ──
            response =  getJudgeResponse(retriever,hybridRetriever,query,response,llm)

        return response
    except Exception as e:
        logging.error(f"'::::: Error processing query: {str(e)}")
        raise

def getJudgeResponse(retriever,hybridRetriever,query,response,llm):
    # Step 2 — Retrieve docs separately for judge context
    try:
        docs = retriever.invoke(query)
        # Step 3 — Run judge pipeline
        judge_result = run_judge_pipeline(
            query=query,
            answer=response,
            context_chunks=[doc.page_content for doc in docs],
            primary_retriever=hybridRetriever,
            llm=llm
        )

        # Step 4 — Act on judge result
        if judge_result["status"] == "blocked":
            logging.warning(f"::::: JUDGE BLOCKED RESPONSE: {judge_result['reason']}")
            response = "I could not generate a reliable answer for this query."
        elif judge_result["status"] == "low_confidence":
            logging.warning(f"::::: JUDGE LOW CONFIDENCE: {judge_result['scores']}")
            response = judge_result["answer"]   # return answer but logged as low confidence
        else:
            logging.debug(f"::::: JUDGE PASSED: {judge_result['scores']}")
            response = judge_result["answer"]   # use judge-approved answer
        return response
    except Exception as e:
        logging.error(f"::::: Error processing query: {str(e)}", exc_info=True)  # ← add exc_info=True
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