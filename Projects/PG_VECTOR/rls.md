
Scripts to enable RLS:
=======================


    ALTER TABLE langchain_pg_embedding ENABLE ROW LEVEL SECURITY;
    ALTER TABLE langchain_pg_embedding FORCE ROW LEVEL SECURITY;
    CREATE POLICY read_all
    ON langchain_pg_embedding
    FOR SELECT
    USING (true);
    
    -- only admin can create embedding.
    CREATE POLICY admin_insert_only
    ON langchain_pg_embedding
    FOR INSERT
    TO admin
    WITH CHECK (true);
