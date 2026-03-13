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



az functionapp config set \
  --python-version 3.11 \
  --name <YOUR_FUNCTION_APP_NAME> \
  --resource-group <YOUR_RESOURCE_GROUP>
