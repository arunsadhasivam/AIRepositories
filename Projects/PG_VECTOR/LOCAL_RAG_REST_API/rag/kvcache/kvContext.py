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


# as you can see above show 2 in VRAM causing issue.
def getKVStableContext(retrieved_docs):
    response = "\n---\n".join(
                    sorted([doc.page_content for doc in retrieved_docs],
                        key=lambda x: hashlib.md5(x.encode()).hexdigest())
                )
    
    logging.info('kvContext:::::getKVStableContext :::::')
    
    return response