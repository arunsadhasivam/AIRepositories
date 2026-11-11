@echo off
call C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts\activate
cd /d C:\WorkSpace\RAG\LOCAL_RAG
set PYTHONUNBUFFERED=1
streamlit run RAGUI.py 2>&1 | powershell -command "$input | Tee-Object -FilePath C:\WorkSpace\RAG\LOGS\ui.log"