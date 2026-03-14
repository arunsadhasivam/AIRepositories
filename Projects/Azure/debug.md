

```
python -c "import openai; print('OK')"


for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"


```


install to specific referring location:
=================================================

```
pip install openai==2.28.0 --target="c:/python/lib/python3.12/site-packages" --upgrade --force-reinstall


```

To find path where it is installed:
====================================

```
python -c "import openai; print(openai.__file__)"

```

To make deployment to build create .deployment:
=====================================================


- in the  project root .deployment file.

https://github.com/projectkudu/kudu/wiki/Configurable-settings#enabledisable-build-actions-preview

```
ini[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```


Build:
=====

- to avoid changing the SCM_DO_BUILD_DURING_DEPLOYMENT better approach is --build-remote true

```
az functionapp deployment source config-zip --resource-group <<resourcegroup>> --name <<functionname>>  --src app.zip  --build-remote true

#log
Setting SCM_DO_BUILD_DURING_DEPLOYMENT to true
Removing ENABLE_ORYX_BUILD app setting
```

 
