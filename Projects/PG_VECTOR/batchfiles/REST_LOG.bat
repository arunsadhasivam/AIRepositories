//start cmd /k "C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts\activate && cd C:\WorkSpace\RAG\LOCAL_RAG_REST_API && python -u app.py > C:\WorkSpace\RAG\LOGS\app.txt 2>&1"

@echo off
call C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts\activate
cd /d C:\WorkSpace\RAG\LOCAL_RAG_REST_API
python -u app.py 2>&1 | powershell -command "$input | Tee-Object -FilePath C:\WorkSpace\RAG\LOGS\app.log"