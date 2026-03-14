

```
python -c "import openai; print('OK')"


for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"


#install to specific referring instance
pip install openai==2.28.0 --target="c:/python/lib/python3.12/site-packages" --upgrade --force-reinstall

ls /opt/python/3/lib/python3.12/site-packages | grep openai

```
