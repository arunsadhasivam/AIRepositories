#kills all previous started ollama
#8f18e45e75d3 filter_id="" library=CUDA compute=8.9 name=CUDA0 description="NVIDIA RTX 2000 Ada Generation Laptop GPU" libdirs=ollama,cuda_v13 driver=13.2 
#pci_id=0000:01:00.0 type=discrete total="8.0 GiB" available="7.6 GiB"
# make sure the log when start using 8.0 GIB of CUDA VRAM.
taskkill /F /IM ollama.exe 2>nul
timeout /t 2

set OLLAMA_MAX_LOADED_MODELS=2
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_KEEP_ALIVE=10m
set OLLAMA_CONTEXT_LENGTH=2048
start "" cmd /k "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe serve"
