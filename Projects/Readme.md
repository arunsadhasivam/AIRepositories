

main project:
===============


    C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts>activate
  
    (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG>streamlit run RAGUI.py
  
    You can now view your Streamlit app in your browser.
  
    Local URL: http://localhost:8501
    Network URL: http://10.0.0.218:8501


Start ollama:
==============

- use **ollama serve** to start ollama

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/0c32d7df-71e7-49da-a265-e3412965a64c" />


To get the installed package list for a project:
================================================

    pip freeze > requirements.txt.

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

Flow :
======


 - ollama server to persist embedding.

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
                                                                                                                                                 
