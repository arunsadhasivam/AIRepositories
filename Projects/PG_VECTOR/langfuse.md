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


```
  # redis:
  #   image: docker.io/redis:7
  #   restart: always
  #   # CHANGEME: row below to secure redis password
  #   command: >
  #     --requirepass ${REDIS_AUTH:-myredissecret}
  #     --maxmemory-policy noeviction
  #   ports:
  #     - 127.0.0.1:6379:6379
  #   volumes:
  #     - langfuse_redis_data:/data
  #   healthcheck:
  #     test: ["CMD", "redis-cli", "ping"]
  #     interval: 3s
  #     timeout: 10s
  #     retries: 10
 # postgres:
  #   image: docker.io/postgres:${POSTGRES_VERSION:-17}
  #   restart: always
  #   healthcheck:
  #     test: ["CMD-SHELL", "pg_isready -U postgres"]
  #     interval: 3s
  #     timeout: 3s
  #     retries: 10
  #   environment:
  #     POSTGRES_USER: ${POSTGRES_USER:-postgres}
  #     POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres} # CHANGEME
  #     POSTGRES_DB: ${POSTGRES_DB:-postgres}
  #     TZ: UTC
  #     PGTZ: UTC
  #   ports:
  #     - 127.0.0.1:5432:5432
  #   volumes:
  #     - langfuse_postgres_data:/var/lib/postgresql/data


remove dependency:

langfuse-worker:
    image: docker.langfuse.com/langfuse/langfuse-worker:${LANGFUSE_IMAGE_TAG:-4}
    restart: always
    depends_on: &langfuse-depends-on
      postgres:
     #   condition: service_healthy
      minio:
        condition: service_healthy
      #redis:
      #  condition: service_healthy
      clickhouse:

```

Result:
=======

<img width="3775" height="525" alt="image" src="https://github.com/user-attachments/assets/a6bf2692-b1f1-4d09-ad7e-cc6b667f33f5" />


Change the db:
================

```
using postgresql+psycopg2 not in docker one installed manually for vector db Rag

C:\WorkSpace\RAG\langfuse\.env.dev-redis-cluster.example
DIRECT_URL="postgresql+psycopg2://admin:admin@localhost:5432/langfuse
DATABASE_URL="postgresql+psycopg2://admin:admin@localhost:5432/langfuse"

REDIS_PORT=6380
change the redisport , since docker has cluster.

REDIS_CLUSTER_ENABLED="true"
REDIS_CLUSTER_NODES="127.0.0.1:6370,127.0.0.1:6371,127.0.0.1:6372,127.0.0.1:6373,127.0.0.1:6374,127.0.0.1:6375"


in docker-compose.yml
======================

redis:
    image: docker.io/redis:7
    restart: always
    # CHANGEME: row below to secure redis password
    command: >
      --requirepass ${REDIS_AUTH:-myredissecret}
      --maxmemory-policy noeviction
    ports:
      - 127.0.0.1:6380:6380

docker one will be like , original one pointing to new docker instance installation
since installing as manuall gives option to open sql editor.

DIRECT_URL="postgresql://postgres:postgres@localhost:5432/postgres"
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"

CREATE DATABASE langfuse;
```

<img width="3792" height="630" alt="image" src="https://github.com/user-attachments/assets/c3343f77-adfd-478d-a456-dbdc97a2f81f" />

<img width="3605" height="2005" alt="image" src="https://github.com/user-attachments/assets/a0a4256a-76aa-4323-9687-bbf6974c66e3" />
