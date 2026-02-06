

install vc++ tools for nmake:
===============================

- to compile the pgvector code



<img width="3577" height="1835" alt="image" src="https://github.com/user-attachments/assets/df396671-cdc6-4e7c-919e-64f4a4c45af6" />





Step 1:
========


- use command prompt **C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Visual Studio 2026\Visual Studio Tools\VC**
- try to run the build.
- set the path with nmake - **C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.50.35717\bin\Hostx64\x64**

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/3f4c7f75-7069-4afd-8772-4c919480bc51" />


```

set "PGROOT=C:\Program Files\PostgreSQL\18"
set PATH=%PATH%;C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.50.35717\bin\Hostx64\x64
C:\Arun\PGVECTOR\pgvector-master>nmake

Microsoft (R) Program Maintenance Utility Version 14.50.35722.0
Copyright (C) Microsoft Corporation.  All rights reserved.

makefile(5) : fatal error U1104: Unknown text function 'wildcard'
Stop.


```


- use x86 vc++ command prompt , run as admin


```
**********************************************************************
** Visual Studio 2026 Developer Command Prompt v18.2.0
** Copyright (c) 2025 Microsoft Corporation
**********************************************************************
[DEBUG:ext\vcvars.bat] Found potential v145 version file: 'Microsoft.VCToolsVersion.VC.14.50.18.0.txt'
[DEBUG:ext\vcvars.bat] Testing v145 version file: 'Microsoft.VCToolsVersion.VC.14.50.18.0.txt'
[vcvarsall.bat] Environment initialized for: 'x64'

C:\Windows\System32>cd C:\Arun\PGVECTOR\pgvector-master

C:\Arun\PGVECTOR\pgvector-master>set "PGROOT=C:\Program Files\PostgreSQL\18"

C:\Arun\PGVECTOR\pgvector-master>set PATH=%PATH%;C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.50.35717\bin\Hostx64\x64

C:\Arun\PGVECTOR\pgvector-master>nmake /F Makefile.win

Microsoft (R) Program Maintenance Utility Version 14.50.35722.0
Copyright (C) Microsoft Corporation.  All rights reserved.


C:\Arun\PGVECTOR\pgvector-master>nmake /F Makefile.win install

Microsoft (R) Program Maintenance Utility Version 14.50.35722.0
Copyright (C) Microsoft Corporation.  All rights reserved.

        copy vector.dll "C:\Program Files\PostgreSQL\18\lib"
        1 file(s) copied.
        copy vector.control "C:\Program Files\PostgreSQL\18\share\extension"
        1 file(s) copied.
        copy sql\vector--*.sql "C:\Program Files\PostgreSQL\18\share\extension"
sql\vector--0.1.0--0.1.1.sql
sql\vector--0.1.1--0.1.3.sql
sql\vector--0.1.3--0.1.4.sql
sql\vector--0.1.4--0.1.5.sql
sql\vector--0.1.5--0.1.6.sql
sql\vector--0.1.6--0.1.7.sql
sql\vector--0.1.7--0.1.8.sql
sql\vector--0.1.8--0.2.0.sql
sql\vector--0.2.0--0.2.1.sql
sql\vector--0.2.1--0.2.2.sql
sql\vector--0.2.2--0.2.3.sql
sql\vector--0.2.3--0.2.4.sql
sql\vector--0.2.4--0.2.5.sql
sql\vector--0.2.5--0.2.6.sql
sql\vector--0.2.6--0.2.7.sql
sql\vector--0.2.7--0.3.0.sql
sql\vector--0.3.0--0.3.1.sql
sql\vector--0.3.1--0.3.2.sql
sql\vector--0.3.2--0.4.0.sql
sql\vector--0.4.0--0.4.1.sql
sql\vector--0.4.1--0.4.2.sql
sql\vector--0.4.2--0.4.3.sql
sql\vector--0.4.3--0.4.4.sql
sql\vector--0.4.4--0.5.0.sql
sql\vector--0.5.0--0.5.1.sql
sql\vector--0.5.1--0.6.0.sql
sql\vector--0.6.0--0.6.1.sql
sql\vector--0.6.1--0.6.2.sql
sql\vector--0.6.2--0.7.0.sql
sql\vector--0.7.0--0.7.1.sql
sql\vector--0.7.1--0.7.2.sql
sql\vector--0.7.2--0.7.3.sql
sql\vector--0.7.3--0.7.4.sql
sql\vector--0.7.4--0.8.0.sql
sql\vector--0.8.0--0.8.1.sql
sql\vector--0.8.1.sql
       36 file(s) copied.
        if not exist "C:\Program Files\PostgreSQL\18\include\server\extension\vector" mkdir "C:\Program Files\PostgreSQL\18\include\server\extension\vector"
        for %f in (src\halfvec.h src\sparsevec.h src\vector.h) do copy %f "C:\Program Files\PostgreSQL\18\include\server\extension\vector"

C:\Arun\PGVECTOR\pgvector-master>copy src\halfvec.h "C:\Program Files\PostgreSQL\18\include\server\extension\vector"
        1 file(s) copied.

C:\Arun\PGVECTOR\pgvector-master>copy src\sparsevec.h "C:\Program Files\PostgreSQL\18\include\server\extension\vector"
        1 file(s) copied.

C:\Arun\PGVECTOR\pgvector-master>copy src\vector.h "C:\Program Files\PostgreSQL\18\include\server\extension\vector"
        1 file(s) copied.

C:\Arun\PGVECTOR\pgvector-master>


```



Step 2 : create extension:
=============================


<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/687d0095-643f-4190-94a7-4397f3a6fbdb" />


Step 3 : verify vector works:
=============================


- see below it works (https://github.com/pgvector/pgvector)
<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/3adee758-4044-41ad-acdc-20f41d18e699" />


step 4:create user and grant permission:
========================================


```

-- Grant schema public permissions
GRANT ALL ON SCHEMA public TO admin;

-- Grant all table permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO admin;

-- Grant permissions on future tables as well
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO admin;
```


Step 5:you can see embedding stored in db:
==============================================

- see in the screenshot vector extension added
<img width="3822" height="2200" alt="image" src="https://github.com/user-attachments/assets/a13bbc7e-4e95-434a-9021-8da34dfcbb03" />

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/6e080fc5-74a1-4e30-b653-330caa50cd90" />

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/970427f1-52f4-479b-850a-f23009c94f84" />
