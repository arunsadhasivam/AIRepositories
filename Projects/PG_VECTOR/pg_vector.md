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

- see in the screenshot vector extension added
<img width="3822" height="2200" alt="image" src="https://github.com/user-attachments/assets/a13bbc7e-4e95-434a-9021-8da34dfcbb03" />

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/6e080fc5-74a1-4e30-b653-330caa50cd90" />

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/970427f1-52f4-479b-850a-f23009c94f84" />
