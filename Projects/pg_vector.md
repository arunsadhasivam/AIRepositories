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


you can see embedding stored in db:
===================================

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/6e080fc5-74a1-4e30-b653-330caa50cd90" />

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/970427f1-52f4-479b-850a-f23009c94f84" />
