Step 1:
========


download az client to connect to remote azure runtime https://aka.ms/installazurecliwindows


Step 2:
========


 - change route to function_app.py
 - change .env to local-settings.json
 - host.json 


 - if you want to make both uvicorn and func work then use union to have support for make request from
   fastapi and azure function to serve.
   

```

       async def processRequest(
              self, request: Union[Request,func.HttpRequest], url: str, extra: str = ""
          ) -> EmployeeResponse:
```
Step 2:
========


npm install -g azurite # emulate the azure storage in local.
az functionapp config set \
  --python-version 3.11 \
  --name <YOUR_FUNCTION_APP_NAME> \
  --resource-group <YOUR_RESOURCE_GROUP>


  step3:
  ======

```
  az functionapp list --output table

 ```

- to view the functionapp details.


Step 4:
========

- tail log
- install azure-cli


```
PS C:\Arun> az webapp log tail --name funemployee --resource-group rg-funemployee

get the function app name and resource group name.

az functionapp list --output table

```

Step 5:
========

- to run azure functions locally from https://github.com/Azure/azure-functions-core-tools
- make sure full version not min 
  https://github.com/Azure/azure-functions-core-tools/releases/download/4.8.0/Azure.Functions.Cli.win-x64.4.8.0.zip
  ```
  npm install -g azure-functions-core-tools@4
  ```


Debugging:
==============

```

func  start --language-worker-timeout 60 -- --debugPort 9091
```

Prequisties for build:
=========================


- make sure 2 properties are set


VERY VERY IMPORTANT:
=====================


without this remote build to cloud wont happen. if fails check the .env and application properties in cloud 

**SCM_DO_BUILD_DURING_DEPLOYMENT** - Tells Azure trigger a build after deployment

**ENABLE_ORYX_BUILD** - Tells Azure use Oryx to do that build — which runs pip install

