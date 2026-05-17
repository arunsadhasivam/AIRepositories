@echo off

:: Set Python path so Celery finds your modules
set PYTHONPATH=C:\WorkSpace\RAG\LOCAL_RAG_REST_API


:: Start embed worker in new terminal window
start "Celery Embed Worker" cmd /k "C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts\activate && cd  C:\WorkSpace\RAG\LOCAL_RAG_REST_API && celery -A rag.processor.tasks worker --queues=embed --concurrency=2 --loglevel=info"

:: Start dead letter worker in new terminal window
start "Celery DLQ Worker" cmd /k "C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts\activate && cd C:\WorkSpace\RAG\LOCAL_RAG_REST_API && celery -A rag.processor.tasks worker --queues=dead_letter --concurrency=1 --loglevel=info"

start "Celery DLQ Worker" cmd /k "C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts\activate && cd C:\WorkSpace\RAG\LOCAL_RAG_REST_API && python -m celery -A rag.processor.tasks flower --port=5555"
 

echo Celery workers started.
