import pdfplumber
import streamlit as st
import os
import requests
from enum import Enum
from controller.SearchController import SearchController
from service.SearchService import SearchService
from cache.RedisRagCache import RedisRagCache

from model.EmbeddingType import EmbeddingType
from model.SearchType import SearchType
from model.SearchType import SearchType
import logging
logging.basicConfig(level=logging.DEBUG)

class RAGUI:
    """Streamlit interface for RAG system"""
    def __init__(self,controller:SearchController):
        self.controller = controller
       
        
    def processQuery(self,query,search_type):
        logging.debug('RAGInterface:::' , query, search_type)
        if not self.rag_pipeline or not self.rag_pipeline.vector_store:
            st.error("Please upload documents first!")
            return
        with st.spinner("Searching..."):
            # Perform search
            results = self.rag_pipeline.search(
                query,
                SearchType(search_type)
            )
            
            # Generate response
            response = self.rag_pipeline.generate_response(
                query,
                results
            )
            
            # Display results
            st.subheader("Response")
            st.write(response)
            st.subheader("Source Documents")
            for doc, score in results:
                with st.expander(
                    f"Source: {doc.source} (Page {doc.page_number})"
                ):
                    st.write(f"Relevance Score: {score:.3f}")
                    st.write(doc.text)    
        
    def run(self):
        """Run the Streamlit interface"""
        st.title("📚 RAG System")
        
        # Sidebar configuration
        with st.sidebar:
            st.header("Configuration")
            
            # Embedding model selection
            embedding_model = st.selectbox(
                "Embedding Model",
                options=[e.value for e in EmbeddingType],
                format_func=lambda x: x.split('/')[-1]
            )
            
        # Main interface
        tab1, tab2 = st.tabs(["📄 Document Upload", "🔍 Search"])
        
        # Document Upload Tab
        with tab1:
            st.header("Upload Documents")
            
            # File upload
            uploaded_files = st.file_uploader(
                "Upload PDF files",
                type="pdf",
                accept_multiple_files=True
            )
            temp_dir = "temp_uploads"
            # URL input
            url = st.text_input("Or enter PDF URL")
            text = ""
            if st.button("Process Documents"):
                with st.spinner("Processing documents..."):
                    for file in uploaded_files:
                        os.makedirs(temp_dir, exist_ok=True)
                        file_path = os.path.join(temp_dir, file.name)

                        with open(file_path, "wb") as f:
                            f.write(file.getbuffer())
                        response =   self.controller.route_embed(self,file_path)
                        st.write(f"File saved at: {response}")
                    if url:
                       
                        st.success(f"Processed {file_path}")
        
        # Search Tab
        with tab2:
            st.header("Search and Query")
            
            # Search configuration
            search_type = st.selectbox(
                "Search Strategy",
                options=[s.value for s in SearchType]
            )
            # Query input
            query = st.text_input("Enter your query")
            #st.button("Search") 
            try :
                if query and st.button("Search"):
                  response =   self.controller.searchQuery(query,search_type)
                  st.write(response)
            except Exception as e:
                st.text("Error in processing Query From Vector DB",help=e)      


# def configure(binder):
#     binder.bind(SearchController, to=SearchController)

if __name__ == "__main__":
    cache = RedisRagCache(url="redis://localhost:6379")
    service = SearchService(cache)
    controller = SearchController(service)
    interface = RAGUI(controller)
    interface.run()
  
