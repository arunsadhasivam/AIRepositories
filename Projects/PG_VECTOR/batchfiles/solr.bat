echo ON
echo "SOLR STARTED"
cd C:\SOLR\solr-9.10.1\bin
solr.cmd start  


echo "OLLAMA STARTED"
timeout /t 3
cd C:\Users\aruns\AppData\Local\Programs\
start "" cmd /k "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe serve"
