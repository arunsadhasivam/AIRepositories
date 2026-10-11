python3.11 -m venv venv

uv venv --python 3.11


# 1. Create the venv using Python 3.11
python3.11 -m venv PYTHON_CUDA_GPU_HOME

# 2. Use the specific pip3.11 inside that venv to install your package

  C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts>activate
  
  ## go to venv supported with  python 3.11
  
  (PYTHON_CUDA_GPU_HOME)>pip3.11 install -r requirements.txt


NOTE:
=====

 - if system path has python older version if not specifically say pip3.11 it default install
   all packages to default older python version.
 - so if multiple version explicitly say pip3.11 or plan to install in python set in path just say

       pip install -r requirements.txt
 - also aware the python 3.11 only available in the venv PYTHON_CUDA_GPU_HOME
