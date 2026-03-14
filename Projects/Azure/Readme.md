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

- to run azure functions locally

  ```
  npm install -g azure-functions-core-tools@4
  ```
