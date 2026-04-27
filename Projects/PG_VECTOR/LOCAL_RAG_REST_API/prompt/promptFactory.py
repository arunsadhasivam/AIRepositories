from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
import logging
logging.basicConfig(level=logging.INFO)
import os
MULTIQUERY_MAX_QUERY_GEN_LIMIT=os.getenv('MULTIQUERY_MAX_QUERY_GEN_LIMIT',2)



def get_prompt():
    QUERY_PROMPT = PromptTemplate(
        input_variables=["question"],
        template=f"""You are an AI language model assistant. Your task is to generate {MULTIQUERY_MAX_QUERY_GEN_LIMIT}
        different versions of the given user question to retrieve relevant documents from
        a vector database. By generating multiple perspectives on the user question, your
        goal is to help the user overcome some of the limitations of the distance-based
        similarity search. Provide these alternative questions separated by newlines.
        Original question: {{question}} """,
    )
  
    template = """Answer the question based ONLY on the following context:
    {context}
    Question: {question}
    .Output only the 2 questions, one per line.
    """
   
    prompt = ChatPromptTemplate.from_template(template)
    
    return QUERY_PROMPT, prompt


