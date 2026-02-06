
Scripts to enable RLS:
=======================


               
          -- =========================
          -- 1️⃣ Create roles
          -- =========================
          -- Superuser creates roles
          CREATE ROLE app_admin LOGIN PASSWORD 'admin';
          CREATE ROLE app_user  LOGIN PASSWORD 'user123';
          
          -- Optional: prevent superusers from default access
          REVOKE ALL ON DATABASE rag FROM PUBLIC;
           
          -- =========================
          -- 3️⃣ Enable RLS
          -- =========================
          ALTER TABLE langchain_pg_embedding ENABLE ROW LEVEL SECURITY;
          ALTER TABLE langchain_pg_embedding FORCE ROW LEVEL SECURITY;
          
          -- =========================
          -- 4️⃣ Create policies
          -- =========================
          
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
          
          -- =========================
          -- 6️⃣ Grant usage
          -- =========================
          -- Admin gets all rights (optional but recommended)
          GRANT SELECT, INSERT, UPDATE, DELETE ON langchain_pg_embedding TO app_admin;
          
          -- Users get only read access
          GRANT SELECT ON langchain_pg_embedding TO app_user;
