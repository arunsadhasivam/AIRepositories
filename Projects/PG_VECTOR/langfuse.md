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
- https://github.com/arunsadhasivam/AIRepositories/new/master/Projects/PG_VECTOR/langfuse/Readme.md

<img width="3792" height="2037" alt="image" src="https://github.com/user-attachments/assets/83f532fa-15b7-430a-b958-367e41a1fdee" />
