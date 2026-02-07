
Scripts to enable RLS:
=======================

```
- GRANT = Can this role has permission to this the table

- RLS =  this role can they change this row


app_admin → granted full table-level privileges, RLS policy allows all rows → full CRUD

app_user → granted SELECT only, RLS policy allows all rows → read-only access



```

Scenario where RLS comes in:
============================

  - **Scenario** : where RLS plays major role - Suppose you give app_user **GRANT INSERT by mistake**
  - Without RLS =  app_user can now insert anywhere → security breach!
  - With RLS → your policy still applies:


Scripts:
=========

          -- =========================
          -- 1️⃣ Create roles
          -- =========================
          -- Superuser creates roles
          CREATE ROLE app_admin LOGIN PASSWORD 'admin';
          CREATE ROLE app_user  LOGIN PASSWORD 'user123';
          GRANT CONNECT ON DATABASE rag TO app_admin;

          -- grant permission to app_admin only to select,update,delete
          GRANT SELECT, INSERT, UPDATE, DELETE ON langchain_pg_embedding TO app_admin;
          GRANT SELECT ON langchain_pg_embedding TO app_user;

          
          GRANT SELECT, INSERT, UPDATE, DELETE ON public.langchain_pg_collection TO app_admin;
          GRANT SELECT ON public.langchain_pg_collection TO app_user;

           
          GRANT SELECT ON langchain_pg_collection TO app_user;
          -- Revoke default public access
          REVOKE ALL ON langchain_pg_collection FROM PUBLIC;

          
          -- Optional: prevent superusers from default access
          REVOKE ALL ON DATABASE rag FROM PUBLIC;
           
          -- =========================
          -- 3️⃣ Enable RLS
          -- =========================
          ALTER TABLE langchain_pg_embedding ENABLE ROW LEVEL SECURITY;
          ALTER TABLE langchain_pg_embedding FORCE ROW LEVEL SECURITY;
          
          -- ========================================
          -- 4️⃣ Create policies - ROW LEVEL SECURITY
          -- ================================================
          
          -- Admin: full CRUD (SELECT, INSERT, UPDATE, DELETE)
          CREATE POLICY admin_full_access
          ON langchain_pg_embedding
          FOR ALL
          TO app_admin
          USING (true)
          WITH CHECK (true);
          
          -- Normal users: read-only (SELECT)
          CREATE POLICY user_read_only
          ON langchain_pg_embedding
          FOR SELECT
          TO app_user
          USING (true);
          
          -- =========================
          -- 5️⃣ Revoke default access from public
          -- =========================
          REVOKE ALL ON langchain_pg_embedding FROM PUBLIC;
          
          -- ==============================================
          -- 6️⃣ Grant usage - TABLE LEVEL SECURITY
          -- =================================================
          -- Admin gets all rights (optional but recommended)
          GRANT SELECT, INSERT, UPDATE, DELETE ON langchain_pg_embedding TO app_admin; 
          
          -- Users get only read access
          GRANT SELECT ON langchain_pg_embedding TO app_user;



Login in as Admin:
====================

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/036896fd-0bff-45f8-bf27-117fd2c4efef" />

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/bfcb6214-ab5c-404d-ab60-5b2f221f914c" />


Failure:
=========

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/3cad7a9a-205b-4c4a-9763-5d300d3bd704" />

<img width="3747" height="1232" alt="image" src="https://github.com/user-attachments/assets/6a55de36-cfc5-4032-aa61-36cebaae0cec" />



