CREATE USER admin WITH PASSWORD 'admin';
-- Grant login permission
ALTER ROLE admin WITH LOGIN;
-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE rag TO admin;

SELECT usename FROM pg_user;
