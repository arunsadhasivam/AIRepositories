python3.11 -m venv venv

uv venv --python 3.11


# 1. Create the venv using Python 3.11
python3.11 -m venv PYTHON_CUDA_GPU_HOME

# 2. Use the specific pip3.11 inside that venv to install your package

  C:\Arun\PythonEnv\PYTHON_CUDA_GPU_HOME\Scripts>activate
  
  ## go to venv supported with  python 3.11 - important
  
  (PYTHON_CUDA_GPU_HOME)>pip3.11 install -r requirements.txt


NOTE:
=====

 - if system env path has python older version(python 3.10) if not specifically say pip3.11 it default install on python 3.10
  
 - so if your venv has multiple version explicitly say pip3.11 or python version 3.10 in system path env variable.

       - pip install -r requirements.txt # will install on python 3.10
       - pip3.11 install -r requirements.txt # will install on python 3.11

 - whereas if venv PYTHON_CUDA_GPU_HOME has default 3.10(windows system environment path variable) and 3.11 .you need to explicitly
   say pip3.11 or pip3.10,   if you have both installed in venv  . if not specify explicitly ,it will install in python 3.10 path.
   
 - Aware if not use pip3.11 for your project which uses venv PYTHON_CUDA_GPU_HOME  wont have modules installed for 3.11 it will install on
   default pip3.10 python version.
