create user and grant permission:
==================================


```

-- Grant schema public permissions
GRANT ALL ON SCHEMA public TO admin;

-- Grant all table permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO admin;

-- Grant permissions on future tables as well
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO admin;
```
