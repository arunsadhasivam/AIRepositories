To run pgvector from docker:
============================




Step 1: docker pull:
=====================

download postgres pgvector 

```
docker pull pgvector/pgvector:pg18-trixie
C:\Users\aruns>docker pull pgvector/pgvector:pg18-trixie
pg18-trixie: Pulling from pgvector/pgvector
a56206a20aed: Download complete
b5266fe75904: Download complete
3d5245a013e9: Download complete
d7ecded7702a: Download complete
9cf93fb7d1b2: Download complete
147c56225731: Download complete
d76dd811beb1: Download complete
040074889e55: Download complete
06f6106b48bf: Download complete
b750bf977656: Download complete
e0013dcb38ac: Download complete
ceb4dbc2f7a8: Download complete
5ef0bb41c3b2: Download complete
7e3d5655f5fd: Download complete
a16a85592f43: Download complete
Digest: sha256:6e0b281a99959919bec7c94718162e75cbbf48e6fd3a5c7529067fa701264082
Status: Downloaded newer image for pgvector/pgvector:pg18-trixie
docker.io/pgvector/pgvector:pg18-trixie

C:\Users\aruns>
```

<img width="2945" height="732" alt="image" src="https://github.com/user-attachments/assets/82aecd83-8101-4b24-a9bb-fa50ebf11290" />





Step 2: connect to pgvector through docker run:
================================================


run pgvector

Parameter **--name** and  port -p 5431:5432 should be unique you can  check based on availability.

```
C:\Users\aruns>docker run --name VECTOR_NEW_RAG_DB -e POSTGRES_PASSWORD=admin -p 5431:5431 -d pgvector/pgvector:pg18-trixie
5b5b9de894534eee68311eb1e394b9336d9279cbb31064c2638631ff47255e66


C:\Users\aruns>docker ps
CONTAINER ID   IMAGE                           COMMAND                  CREATED              STATUS              PORTS                                                 NAMES
5b5b9de89453   pgvector/pgvector:pg18-trixie   "docker-entrypoint.s…"   About a minute ago   Up About a minute   0.0.0.0:5431->5431/tcp, 5432/tcp                      VECTOR_NEW_RAG_DB
a43835d3817a   pgvector/pgvector:pg16          "docker-entrypoint.s…"   9 minutes ago        Up 9 minutes        0.0.0.0:5432->5432/tcp                                pgvector-db
64b50600cac2   kindest/node:v1.31.14           "/usr/local/bin/entr…"   10 days ago          Up 8 hours          0.0.0.0:30001->30001/tcp, 127.0.0.1:64969->6443/tcp   cluster3-control-plane
28ccf41be212   kindest/node:v1.31.14           "/usr/local/bin/entr…"   10 days ago          Up 8 hours                                                                cluster3-worker
6caaa1d27292   kindest/node:v1.31.14           "/usr/local/bin/entr…"   10 days ago          Up 8 hours                                                                cluster3-worker2
```


connect to db

```
C:\Users\aruns>docker exec -it  VECTOR_NEW_RAG_DB psql -U admin -d admin
psql: error: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: FATAL:  role "admin" does not exist
```

 
