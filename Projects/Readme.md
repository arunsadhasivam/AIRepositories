
main project:
===============


    C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts>activate
  
    (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG>streamlit run RAGUI.py
  
    You can now view your Streamlit app in your browser.
  
    Local URL: http://localhost:8501
    Network URL: http://10.0.0.218:8501


```
1)  C:\WorkSpace\RAG\LOCAL_RAG_REST_API>python app.py      
2) C:\WorkSpace\RAG\LOCAL_RAG>streamlit run RAGUI.py
3) C:\SOLR\solr-9.10.1\bin>solr.cmd start
4) run first C:\Memurai\merumai.exe
5) run C:\Memurai\merumai-cli.exe > 127.0.0.1:6379>
        

```

<img width="3830" height="1150" alt="image" src="https://github.com/user-attachments/assets/f5699cd3-7fcd-49d8-b9c1-5c3841aafd17" />


Start ollama:
==============

- use **ollama serve** to start ollama


<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/0c32d7df-71e7-49da-a265-e3412965a64c" />


- make sure ollama has embedding model installed

```
C:\Users\aruns>ollama list
NAME                       ID              SIZE      MODIFIED
mistral:latest             6577803aa9a0    4.4 GB    6 months ago
llama2:latest              78e26419b446    3.8 GB    7 months ago
nomic-embed-text:latest    0a109f422b47    274 MB    10 months ago
```

C:\Users\aruns>

Start Redis:
=============
 
<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/10148735-7c2f-4c94-8aec-f6677b0762e5" />
<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/9c093a5b-e98a-41ce-885c-7c34da6ac24d" />

- see retrieved from cache.

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/fb9c58c9-dd88-4ceb-87bb-4c65940bd1c3" />



REST Project:
==============


    (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG_REST_API>python app.py
  
       * Serving Flask app 'app'
       * Debug mode: on
      WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
       * Running on all addresses (0.0.0.0)
       * Running on http://127.0.0.1:8080
       * Running on http://10.0.0.218:8080
      Press CTRL+C to quit
       * Restarting with stat
       * Debugger is active!
       * Debugger PIN: 124-060-967

Running logs:
=============

- above code works fine

rest api
=========

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/7e50e647-73cf-4d38-88d9-e9350f7d311f" />
<img width="3815" height="2122" alt="image" src="https://github.com/user-attachments/assets/d2c586d9-85c6-4df8-ac19-b4f2ea5c6222" />


ollama
======

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/3f4d9742-7972-43bd-be74-2706efe67ba8" />

local rag:
============

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/af078138-3325-4b00-8b8b-3a55e093f9be" />


Note:
======
- make sure requirements.txt is followed and versions are same.


Flow :
======


 

      ------------------------------------------------------------------------------------------|-----------------------------------------
        LOCAL_RAG (project )                                                                    | LOCAL_RAG_REST_API
                                                                                                |
        RAGUI.py (streamlit) --> SearchController (controller) -- > SearchController(service)---|---> app.py(route_query)---> query.py(prompt)
                                                                                                |                             |
      ------------------------------------------------------------------------------------------|-----------------------------|-----------                                                                                                                                                             |
                 Agent                                                                                           MathClassificationAgent.py
                                                                                                                        (Agent)
                                                                                                                              |
     -------------------------------------------------------------------------------------------------------------------------|------------------                                                                                                                                                      |                                                                                                                                                                        |
                                                                                     --|---------if requires_math=true--------|--- false-----|
                                                                                       |                                                     |
                                                                                       |                                                     |
                                                                                MathClassification(math_exectutor)                     Ollama LLM 
                                                                                       |                                                     |
                                                                                    return response                                return response
                                                                                                                                                 
