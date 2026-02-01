import os
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.retrievers import MultiQueryRetriever
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from embeddings.get_vector_db import get_vector_db
from agents.MathClassificationAgent import MathClassificationAgent
import json
import logging
logging.basicConfig(level=logging.DEBUG)

LLM_MODEL = os.getenv('LLM_MODEL', 'mistral')

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

# Main function to handle the query process
def query(query):
    if query:
        # Initialize the language model with the specified model name
        llm = ChatOllama(model=LLM_MODEL)
        # Get the vector database instance
        db = get_vector_db()
        # Get the prompt templates
        QUERY_PROMPT, prompt = get_prompt()


        #agent
        MathClassificationAgent.init()
        math_executor = MathClassificationAgent.create_math_agent(llm)

        

        # Set up the retriever to generate multiple queries using the language model and the query prompt
        retriever = MultiQueryRetriever.from_llm(
            db.as_retriever(), 
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
        
        response = classifier_chain.invoke(query)

        if('true' in response):
            logging.debug (':::::::::::::::LOCAL PYTHON MATH FUNCTION:::::::::::'+response)
            response = MathClassificationAgent.math(query)
        else :
            logging.debug ('::::::::::::::OLLAMA RAG GENERATION:::::::::::::::')    
            rag_chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            response = rag_chain.invoke(query)

        
        return response

    return None

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
            console.log('::::::::::::MATH EXECUTOR::::::::::::::')
            return math_executor.run(query)
        else:
            console.log("::::::::::OLLAMA LLM EXECUTOR:::::::::::::::::::")
            return rag_chain.invoke(query)
            
    except Exception as e:
        # Fallback to regular chain if anything fails
        print(f"Router error: {str(e)}")
        return rag_chain.invoke(query)

    return dynamic_router    