installation:
===============

install redis on docker install langfuse project :https://github.com/langfuse/langfuse

start from docker :
====================

```
C:\Users\aruns>docker exec -it langfuse-redis-1 redis-cli
127.0.0.1:6379>
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
