import hashlib
import logging
logging.basicConfig(level=logging.INFO)

#Error processing query: Ollama call failed with status code 500. Details: {"error":"model requires more system memory (2.6 GiB) than is available (2.2 GiB)"}
#OLLAMA_KEEP_ALIVE=0
# this OLLAMA_KEEP_ALIVE=0 will make sure once model used remove from gpu(VRAM)
#C:\Users\aruns>ollama ps
#NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL


# C:\Users\aruns>ollama ps
# NAME                       ID              SIZE      PROCESSOR    CONTEXT    UNTIL
# nomic-embed-text:latest    0a109f422b47    595 MB    100% GPU     2048       2 minutes from now
# mistral:latest             6577803aa9a0    5.1 GB    100% GPU     4096       About a minute from now

# check gpu usage

# +-----------------------------------------------------------------------------------------+
# | NVIDIA-SMI 595.71                 Driver Version: 595.71         CUDA Version: 13.2     |
# +-----------------------------------------+------------------------+----------------------+
# | GPU  Name                  Driver-Model | Bus-Id          Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
# |                                         |                        |               MIG M. |
# |=========================================+========================+======================|
# |   0  NVIDIA RTX 2000 Ada Gene...  WDDM  |   00000000:01:00.0 Off |                  N/A |
# | N/A   39C    P8              1W /   37W |    5496MiB /   8188MiB |      0%      Default |
# |                                         |                        |                  N/A |
# +-----------------------------------------+------------------------+----------------------+

# +-----------------------------------------------------------------------------------------+
# | Processes:                                                                              |
# |  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
# |        ID   ID                                                               Usage      |
# |=========================================================================================|
# |    0   N/A  N/A            8904      C   ...al\Programs\Ollama\ollama.exe      N/A      |
# |    0   N/A  N/A           11592      C   ...al\Programs\Ollama\ollama.exe      N/A      |
# |    0   N/A  N/A           27112      C   ...al\Programs\Ollama\ollama.exe      N/A      |
# +-----------------------------------------------------------------------------------------+

# as you can see above show 2 in VRAM causing issue.
#Same chunks → same sort order → same prompt prefix → Ollama reuses KV cache → faster inference

import os
import requests
def getKVStableContext(retrieved_docs):
    response = "\n---\n".join(
                    sorted([doc.page_content for doc in retrieved_docs],
                        key=lambda x: hashlib.md5(x.encode()).hexdigest())
                )
    
    logging.info('kvContext:::::getKVStableContext :::::')
    
    return response



