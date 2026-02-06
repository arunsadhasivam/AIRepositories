Streamlit how it works:
==========================

  - if say redis in PYTHON_CUDA_GPU_HOME venv it loads from there.
  - let say if streamlit not in PYTHON_CUDA_GPU_HOME , but installed globally in python
  - then it loads streamlit from python global and redis from PYTHON_CUDA_GPU_HOME so when you run it
    says module not found'redis'
  - make sure PYTHON_CUDA_GPU_HOME you have both streamlit and redis installed .
