

Server:
=======

        
        (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG_REST_API>
        (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG_REST_API>
        (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG_REST_API>
        (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG_REST_API>python rest.py
        



Client:
========

      (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG>streamlit run RAGUI.py


Implementation:
===============

implemented only search support with mcp and normal query 

    RAGUI.py -> search -> shows MCP and normal search -> choose mcp ---> implemented only search via mcp.

normal endpoint - /query?query=35353*352
mcp endpoint -> /mcp/query?query=35353*352

          (PYTHON_CUDA_GPU_HOME) C:\WorkSpace\LOCAL_RAG_REST_API>python rest.py
           * Serving Flask app 'rest'
           * Debug mode: off
           * Running on http://127.0.0.1:8080
          INFO:werkzeug:Press CTRL+C to quit
          MCP Query APP:data::: {'query': '35353*352'}
          INFO:chromadb.telemetry.product.posthog:Anonymized telemetry enabled. See                  
          https://docs.trychroma.com/telemetry for more information.
          DEBUG:chromadb.config:Starting component System
          DEBUG:chromadb.api.segment:Collection LOCAL-RAG already exists, returning existing collection.
          DEBUG:root:Math tool initialization :INIT()
          DEBUG:root:create math Agent called:::
          DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): us-api.i.posthog.com:443
          DEBUG:urllib3.connectionpool:https://us-api.i.posthog.com:443 "POST /batch/ HTTP/11" 200 15
         
          DEBUG:urllib3.connectionpool:Starting new HTTP connection (1): localhost:11434
          DEBUG:urllib3.connectionpool:http://localhost:11434 "POST /api/chat HTTP/11" 200 None
          DEBUG:root::::::::::::::::LOCAL PYTHON MATH FUNCTION::::::::::: {
              "requires_math": true
             }
          DEBUG:root:::::::::::::::calculator CALLED:::::::::::::::
          MCP APP:response:::Result: 12444256
          INFO:werkzeug:127.0.0.1 - - [09/Jun/2025 00:38:39] "POST /mcp/query?query=35353*352 HTTP/1.1" 200 -
          
          
              
