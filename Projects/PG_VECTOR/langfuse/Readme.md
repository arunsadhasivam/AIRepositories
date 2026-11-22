Steps:
======


- if you have redis,postgres already installed.
- just change the C:\WorkSpace\RAG\langfuse\docker-compose.yml only port:

```
   ports:
      - 127.0.0.1:6379:6379 (line no 265)

 ports:
      - 127.0.0.1:5433:5432 (line 289)

```



