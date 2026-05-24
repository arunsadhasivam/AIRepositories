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
import time   
import json 
from datetime import datetime

logging.basicConfig(level=logging.INFO)



class RAGUI:
    """Streamlit interface for RAG system"""
    def __init__(self,controller:SearchController):
        self.controller = controller

    def isAdmin(self,username):
        user_file = "users.json"
        if not os.path.exists(user_file):
            return False
        try:
            with open(user_file) as f:
                user_data = json.load(f)
            users = user_data.get("users", {})
            logging.debug(f'json={users}')
            return users.get(username).get("role") == 'app_admin'
        except Exception:
            return False
    
    # -------------------------
    # Auth helper
    # -------------------------
    def authenticate(self,username, password):
        logging.debug(f':::::user={username}, pwd={password}')
        user_file = "users.json"
        if not os.path.exists(user_file):
            return False
        try:
            with open(user_file) as f:
                user_data = json.load(f)
            users = user_data.get("users", {})
            logging.debug(f'::::: json={users}')
            return users.get(username).get("password") == password
        except Exception:
            return False
    
    # -------------------------
    # Login page
    # -------------------------
    def login(self):
        st.title("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if self.authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.password = password
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")
        
    def run(self):
        """Run the Streamlit interface - authenticated users only"""
        st.title("📚 RAG System")
        
        # Sidebar configuration
        with st.sidebar:
            st.html("<h1>USER DASHBOARD</h1>")
            # Embedding model selection

            #embedding_model = st.selectbox(
            #    "Embedding Model",
            #    options=[e.value for e in EmbeddingType],
            #    format_func=lambda x: x.split('/')[-1]
            #)
            roleName = 'app_admin' if self.isAdmin(st.session_state.username) else 'app_user'
            st.html('<hr>')
            st.html('<b>USER<b>: <span style="color:green">'+st.session_state.username +'</span' )
            st.html('<b>Role: <span style="color:green">'+roleName +'</span' )
            st.html('<hr>')
            st.html('<a href="http://localhost:8080/health_check"> HealthCheck </a>')
            st.html('<hr>')
            
        # Main interface
        tab1, tab2 = st.tabs(["📄 Document Upload", "🔍 Search"])
        
        # Document Upload Tab
        with tab1:
            st.header("Upload Documents")
            # File upload
            uploaded_files = st.file_uploader(
                "Upload PDF files",
                type=['pdf', 'docx', 'doc', 'md', 'html', 'htm'],
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
                        msg = st.empty() 
                        try:    
                            user_role = 'app_admin' if self.isAdmin(st.session_state.username) else 'app_user'
                            logging.info(f'::::: RAG UPDATE KNOWLEDGE BASE WITH USER ROLE={user_role}')
                            response =   self.controller.route_embed(file_path,user_role,st.session_state.password)
                            logging.info(f'::::: RAG UPDATE KNOWLEDGE RESPONSE={response}')
                            
                            if response is not None: 
                              msg.html(f"<span style='color:green'>File saved at: {response}</span>")
                            else :
                              msg.html(f"<span style='color:red'>* No privilege to update Knowledge Base </span>")

                        except Exception as e:
                             msg.html(f"<span style='color:red'>* No privilege to update Knowledge Base </span>")
                    if url:
                        st.success(f"Processed {url}")
        
        # Search Tab
        with tab2:
            st.header("Search and Query")
            
            # Search configuration
            search_type = st.selectbox(
                "Search Strategy",
                options=[s.value for s in SearchType]
            )
            logging.info(f"::::: RAGUI CONTROLLER:{search_type}")
            # Query input
            query = st.text_input("Enter your query")
            #st.button("Search") 
            try :
                if query and st.button("Search"):
                  st.text(f"Error in processing Query From Vector DB:help ")      
                  user_role = 'app_admin' if self.isAdmin(st.session_state.username) else 'app_user'
                  response =   self.controller.searchQuery(query,search_type,user_role,st.session_state.password)
                  logging.info(f"::::: RAGUI CONTROLLER  :QUERY SUCESS:{response}")
                  st.write(response)
            except Exception as e:
                logging.info(f"::::: RAGUI CONTROLLER  :QUERY SUCESS: {str(e)}")
                st.text(f"Error in processing Query From Vector DB:help ")      


        
if __name__ == "__main__":
    # set default state.
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None

    # load redis and inject service to controller.
    cache = RedisRagCache(url="redis://localhost:6379")
    service = SearchService(cache)
    controller = SearchController(service)
    interface = RAGUI(controller)
    if not st.session_state.authenticated:
        interface.login()
    else:
        interface.run()
  
