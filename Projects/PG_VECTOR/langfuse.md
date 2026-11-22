installation:
===============

install redis on docker install langfuse project :https://github.com/langfuse/langfuse

start from docker :
====================

```
C:\Users\aruns>docker exec -it langfuse-redis-1 redis-cli
127.0.0.1:6379>
```

container up and running:
==========================


```

C:\LANGFUSE\langfuse>docker compose up -d
[+] Running 7/7
 ✔ Network langfuse_default              Created                                                                   0.2s
 ✔ Container langfuse-clickhouse-1       Healthy                                                                   6.7s
 ✔ Container langfuse-postgres-1         Healthy                                                                   4.7s
 ✔ Container langfuse-minio-1            Healthy                                                                   6.7s
 ✔ Container langfuse-redis-1            Healthy                                                                   4.7s
 ✔ Container langfuse-langfuse-web-1     Started                                                                   7.2s
 ✔ Container langfuse-langfuse-worker-1  Started                                                                   7.0s
```

Langfuse:
=========


Error:
=======

- if already installed postgres

C:\WorkSpace\RAG\langfuse>docker compose up -d
[+] Running 2/4
 ✔ Container langfuse-minio-1       Running                                                                                                                   0.0s
 ✔ Container langfuse-clickhouse-1  Running                                                                                                                   0.0s
 - Container langfuse-postgres-1    Starting                                                                                                                  0.1s
 - Container langfuse-redis-1       Starting                                                                                                                  0.1s
Error response from daemon: Ports are not available: exposing port TCP 127.0.0.1:6379 -> 127.0.0.1:0: listen tcp 127.0.0.1:6379: bind: An attempt was made to access a socket in a way forbidden by its access permissions.

Solution:
===========

go to langfuse project and remove service.

C:\WorkSpace\RAG\langfuse\docker-compose.yml



<img width="3792" height="630" alt="image" src="https://github.com/user-attachments/assets/c3343f77-adfd-478d-a456-dbdc97a2f81f" />

<img width="3605" height="2005" alt="image" src="https://github.com/user-attachments/assets/a0a4256a-76aa-4323-9687-bbf6974c66e3" />

<img width="3750" height="1800" alt="image" src="https://github.com/user-attachments/assets/842d6b42-7cff-4d90-869a-5e611a33422a" />

<img width="3835" height="2132" alt="image" src="https://github.com/user-attachments/assets/e385886a-9aa5-48c3-8dc0-4c02772daa12" />


LANGFUSE SETUP WORKING:
=======================

- works after changing the below
- follow this docker-compose.yml https://github.com/arunsadhasivam/AIRepositories/new/master/Projects/PG_VECTOR/langfuse/Readme.md

- make sure the langfuse docker compose up shows the log as **"Ready to accept connections tcp"**

<img width="2535" height="1942" alt="image" src="https://github.com/user-attachments/assets/dbca8594-24cb-464a-a6b4-ce46e186dfbe" />



Langfuse:
=========

 <img width="3820" height="1807" alt="image" src="https://github.com/user-attachments/assets/dea2b93e-f79b-4839-900a-bbbeb70b379c" />

 <img width="3830" height="1547" alt="image" src="https://github.com/user-attachments/assets/80b60217-1918-4bb5-9c59-b68e8d35b9e6" />

 <img width="3830" height="1557" alt="image" src="https://github.com/user-attachments/assets/2ec496fe-6a05-4147-826b-b36eabee7d68" />

 <img width="3830" height="1732" alt="image" src="https://github.com/user-attachments/assets/b6b29012-9104-4c99-943b-6ec06d9ea015" />

<img width="3785" height="2010" alt="image" src="https://github.com/user-attachments/assets/e0d049e0-d9bf-46f4-b0db-78c1d19e4069" />

