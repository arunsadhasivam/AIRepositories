

 
                                                        

<div align="center">
  <h1>Architecture Diagram </h1>

</div>


Architecture Diagram:
=====================

<img width="1488" height="888" alt="image" src="https://github.com/user-attachments/assets/b6878cdb-3c15-4fbd-807d-cad3e6fdc969" />

</p>
</details>




                                                        

<div align="center">
  <h1>Integration Setup (OLLAMA,REDIS,VECTORDB) </h1>

</div>

<p>
<details><summary>Integrations</summary>

Step 1:Start ollama:
=====================

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

Step2:Start Redis:
===================
 
<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/10148735-7c2f-4c94-8aec-f6677b0762e5" />
<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/9c093a5b-e98a-41ce-885c-7c34da6ac24d" />

- see retrieved from cache.

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/fb9c58c9-dd88-4ceb-87bb-4c65940bd1c3" />




Step 3:PG VECTOR DB:
=======================


<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/99f686c9-dac3-4998-afce-498ad9068e01" />



</div>
</p>
</details>




 


<div align="center">
  <h1>Project Setup </h1>

</div>


Step 1: main project:
=====================


    C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts>activate
  
    (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG>streamlit run RAGUI.py
  
    You can now view your Streamlit app in your browser.
  
    Local URL: http://localhost:8501
    Network URL: http://10.0.0.218:8501




LOCAL_RAG:
==========

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/4f6b5ddb-6a2a-4a86-b48e-154ec92b6a32" />




Step 2:REST Project:
=====================


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
 
RLS:
=====

- configured in RLS to allow updation of knowledge store.

Admin User - update RAG knowledge store:
=========================================
<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/c19b6c81-d716-4949-b19c-b1f75bfba106" />



Normal User - update RAG knowledge store:
=========================================
<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/dd2129d6-3aa1-449b-8251-de91e328fdc9" />
