# 🎫 IT Helpdesk AI Agent using MCP + Ollama + PostgreSQL

A production-style AI agent that lets support staff query the IT Helpdesk ticket system using **natural language** — powered by **MCP (Model Context Protocol)**, **Ollama (local LLM)**, and **PostgreSQL**.

> **"Show me all critical open tickets this week"** → AI queries DB → returns results. No SQL needed.

---

## 🏗️ Architecture

```
User (natural language)
        ↓
   Ollama Agent  (llama3 running locally)
        ↓
   MCP Client    (sends tool calls)
        ↓
   MCP Server    (Python + FastMCP)
        ↓
   PostgreSQL    (helpdesk_db)
        ↓
   Audit Log     (every query logged)
```

---

## 🧰 Tech Stack

| Component     | Tool                  | Cost   |
|---------------|-----------------------|--------|
| LLM           | Ollama + llama3       | Free   |
| MCP Server    | Python + FastMCP      | Free   |
| Database      | PostgreSQL (local)    | Free   |
| Language      | Python 3.10+          | Free   |

---

## 📁 Project Structure

```
helpdesk-mcp-agent/
├── db/
│   └── schema.sql          # PostgreSQL schema + mock data
├── mcp_server.py           # MCP server (tools exposed to AI)
├── agent.py                # Ollama agent (talks to MCP server)
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## ✅ Prerequisites

Make sure the following are installed on your machine:

- Python 3.10 or above
- PostgreSQL (local)
- Ollama

---

## 🚀 Step-by-Step Setup

### Step 1: Clone or Download the Project

```bash
git clone https://github.com/YOUR_USERNAME/helpdesk-mcp-agent.git
cd helpdesk-mcp-agent
```

---

### Step 2: Install Ollama

Download and install Ollama from the official site:

```
https://ollama.com/download
```

After installing, pull the llama3 model:

```bash
ollama pull llama3
```

Verify Ollama is running:

```bash
ollama list
```

You should see `llama3` in the list.

---

### Step 3: Install PostgreSQL Locally

#### On Mac:
```bash
brew install postgresql
brew services start postgresql
```

#### On Windows:
Download installer from:
```
https://www.postgresql.org/download/windows/
```

#### On Ubuntu/Linux:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

---

### Step 4: Create the Database

Open PostgreSQL terminal:

```bash
psql -U postgres
```

Create the database:

```sql
CREATE DATABASE helpdesk_db;
\q
```

---

### Step 5: Load the Schema and Mock Data

```bash
psql -U postgres -d helpdesk_db -f db/schema.sql
```

Verify data loaded:

```bash
psql -U postgres -d helpdesk_db -c "SELECT * FROM tickets;"
```

You should see 10 mock tickets.

---

### Step 6: Create Python Virtual Environment

```bash
python -m venv venv
```

Activate it:

#### On Mac/Linux:
```bash
source venv/bin/activate
```

#### On Windows:
```bash
venv\Scripts\activate
```

---

### Step 7: Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 8: Configure Database Password

Open `mcp_server.py` and update the DB config section with your local PostgreSQL password:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "helpdesk_db",
    "user": "postgres",
    "password": "YOUR_PASSWORD_HERE"   # ← change this
}
```

---

### Step 9: Start the MCP Server

In **Terminal 1**, run:

```bash
python mcp_server.py
```

You should see:

```
MCP Server 'helpdesk_mcp' running on stdio...
```

---

### Step 10: Run the AI Agent

In **Terminal 2**, run:

```bash
python agent.py
```

---

## 💬 Example Queries You Can Ask

Once the agent is running, try these natural language queries:

```
> Show all critical open tickets
> How many tickets are unassigned?
> List all tickets raised by the Finance department
> Which agent has the most open tickets?
> Show all network-related tickets this week
> What is the status of TKT-1002?
```

---

## 🔐 Key Features

### 1. Natural Language to SQL
- No SQL knowledge needed
- AI understands intent and queries the DB

### 2. Role-Based Access
- `admin` → sees all tickets and agent details
- `agent` → sees only assigned tickets

### 3. Audit Logging
- Every query (natural language + generated SQL) is logged to `audit_logs` table
- Full traceability — who asked what and when

---

## 🧪 Verify Audit Logs

After running some queries, check the audit log:

```bash
psql -U postgres -d helpdesk_db -c "SELECT * FROM audit_logs;"
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `ollama: command not found` | Reinstall Ollama from ollama.com |
| `connection refused` on PostgreSQL | Run `brew services start postgresql` or `sudo systemctl start postgresql` |
| `ModuleNotFoundError: mcp` | Run `pip install -r requirements.txt` inside venv |
| `password authentication failed` | Update password in `mcp_server.py` DB_CONFIG |
| llama3 model not found | Run `ollama pull llama3` |

---

## 📌 LinkedIn Showcase Description

> Built an AI-powered IT Helpdesk Query Agent using **MCP (Model Context Protocol)**, **Ollama (llama3)**, and **PostgreSQL**. Support staff can query ticket data using plain English — no SQL needed. Includes role-based access control and full audit logging for compliance. Fully local, zero cost.
> Tech: Python · FastMCP · Ollama · PostgreSQL · asyncpg

---
 
