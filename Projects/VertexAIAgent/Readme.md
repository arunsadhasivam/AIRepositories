
# BigQuery + Vertex AI Agent + Spring Boot — Learning & Reference Guide

**Goal:** Build an AI agent (Vertex AI / Gemini) that autonomously queries BigQuery, deploy it as a containerized API on Cloud Run via Artifact Registry, and consume it from a local Spring Boot application.

**Focus areas:** Cloud-native full-stack applications, AI-powered autonomous agents, GCP + Vertex AI.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Layer 1 — BigQuery Fundamentals](#2-layer-1--bigquery-fundamentals)
3. [Key GCP Concepts](#3-key-gcp-concepts)
4. [Phase 0 — GCP Project Setup](#4-phase-0--gcp-project-setup)
5. [Phase 1 — BigQuery Data Setup (COMPLETED)](#5-phase-1--bigquery-data-setup-completed)
6. [Phase 2 — Vertex AI Agent (Local)](#6-phase-2--vertex-ai-agent-local)
7. [Phase 3 — Containerize & Deploy to Cloud Run](#7-phase-3--containerize--deploy-to-cloud-run)
8. [Phase 4 — Spring Boot Client](#8-phase-4--spring-boot-client)
9. [Phase 5 — Extras & Demo Flow](#9-phase-5--extras--demo-flow)
10. [Key Concepts Q&A](#10-key-concepts-qa)
11. [Project Review — Strengths & Gaps](#11-project-review--strengths--gaps)
12. [UI vs CLI Reference](#12-ui-vs-cli-reference)
13. [Project Cleanup / Deletion](#13-project-cleanup--deletion)

---

## 1. Architecture Overview

```
┌──────────────────┐         ┌─────────────────────────┐
│   Local Machine   │         │   Artifact Registry      │
│                   │         │   (Docker image store)   │
│   Spring Boot     │         └───────────┬─────────────┘
│   RestTemplate    │                     │ deploy
└────────┬──────────┘                     ▼
         │  HTTP POST        ┌─────────────────────────┐
         └──────────────────►│   Cloud Run — Agent API  │
                             │   FastAPI + LangChain    │
                             │   ReAct Agent            │
                             └─────┬──────────────┬────┘
                          LLM call │              │ SQL query
                                   ▼              ▼
                          ┌─────────────┐  ┌─────────────┐
                          │  Vertex AI   │  │  BigQuery    │
                          │  (Gemini)    │  │  employees   │
                          └─────────────┘  └─────────────┘
```

**Flow:** Spring Boot sends natural-language question → Cloud Run agent → Gemini reasons and generates SQL → BigQuery tool executes → results back to Gemini → natural-language answer → Spring Boot.

**Pattern:** ReAct (Reason → Act → Observe → Reason again). The LLM decides *when* and *how* to query — SQL is not hardcoded.

---

## 2. Layer 1 — BigQuery Fundamentals

BigQuery is GCP's **serverless, columnar data warehouse**. No servers to provision, no indexes to tune.

| Concept | Traditional DB (MySQL/Postgres) | BigQuery |
|---|---|---|
| Database | Schema / DB | **Dataset** |
| Table | Table (row-based) | **Table** (columnar) |
| Query engine | MySQL engine | **Dremel** (massively parallel) |
| Storage | Server disk | **Colossus** (distributed FS) |
| Pricing | Server uptime | **Per TB scanned** (1 TB/month free) |
| Indexes | B-tree indexes | **Partitioning + Clustering** |

### Key points

- **Storage and compute are separated** — core cloud-native principle.
- **Columnar storage:** `SELECT name, salary` reads only 2 columns even if the table has 50. Check the cost estimator (top-right of SQL editor): `SELECT *` scans more bytes than selecting specific columns — columnar storage visible in action.
- **Partitioning:** split table by date/int range so queries scan only relevant partitions.
- **Clustering:** physically co-locate rows by column value (e.g. `department`) to reduce scan further.
- **Preview tab is free** — `SELECT *` costs scan bytes; Preview does not.
- **Table reference format:** `` `project.dataset.table` `` in backticks — different from MySQL. The agent must generate this exact format.
- **Public datasets:** e.g. `bigquery-public-data.usa_names.usa_1910_2013` (~6M rows) — zero setup, useful for demonstrating scale.
- Minimum IAM to query: `roles/bigquery.dataViewer` + `roles/bigquery.jobUser`.

---

## 3. Key GCP Concepts

### What "BigQuery API" / "Vertex AI API" means

Every GCP service is fundamentally a **set of REST endpoints in the cloud** (e.g. `bigquery.googleapis.com`). There is no software to install. UI, CLI (`bq`, `gcloud`), and client libraries (Python/Java) are all **wrappers around the same REST API**.

**"Enable the API" = switch on that service's endpoints for YOUR project:**
1. Allow requests from your project to the service
2. Start metering usage for billing
3. Apply quotas and IAM permissions

If disabled: `403: BigQuery API has not been used in project... or it is disabled` — even the console UI fails.

**Analogy (Spring Boot world):**

| Your world | GCP equivalent |
|---|---|
| `@RestController` exposing `/api/query` | `bigquery.googleapis.com` endpoints |
| Feature flag that must be ON before endpoint accepts traffic | "Enable API" toggle |
| `RestTemplate` client calling that endpoint | `google-cloud-bigquery` client library |
| Spring Security rejecting calls when flag is off | 403 error when API disabled |

### IMPORTANT — Common misconception corrected

Enabling an API is **NOT** about "exposed externally vs. stays inside cloud." It controls whether the service works **at all** for your project — from anywhere, including the console UI itself.

**Three independent access gates:**

1. **API enablement** — does the service exist for my project?
2. **IAM** — who is allowed to call it?
3. **Networking / VPC controls** — from which networks can calls come?

Examples:
- BigQuery API enabled + IAM granted only to you → only you can query, even though the endpoint is reachable from any network. Auth blocks everyone else.
- Cloud Run with `--allow-unauthenticated` → truly public.
- Same Cloud Run with IAM-only invocation → deployed, but locked to callers with a valid identity token.

**Why explicit opt-in:** security (smaller attack surface), cost protection (disabled service can't bill you), per-project quota management — explicit opt-in is itself a cloud-native principle.

### How to check if an API is enabled

- **Way 1:** Top search bar → "BigQuery API" → page shows either blue **Enable** button (not enabled) or **"API Enabled"** ✓ with **Manage** button (enabled).
- **Way 2:** ☰ → APIs & Services → **Enabled APIs & services** → scan the list.
- **Shortcut:** if BigQuery Studio opens and shows the Explorer panel — the API is enabled.

APIs needed for this project (enable upfront to avoid interruptions):
- BigQuery API (usually enabled by default on new projects)
- Vertex AI API (`aiplatform.googleapis.com`) — usually NOT default
- Cloud Run Admin API — usually NOT default
- Artifact Registry API — usually NOT default
- Cloud Build API — usually NOT default

---

## 4. Phase 0 — GCP Project Setup

### UI path
1. console.cloud.google.com → project dropdown → **New Project** → e.g. `arun-bq-agent-demo`
2. Attach billing (new accounts get $300 free credit; this project costs ~nothing)
3. Enable APIs via APIs & Services → Library (see list above)

### CLI equivalent
```bash
# Login to your cloud account
gcloud auth login

# Create project
gcloud projects create arun-bq-agent-demo --name="BQ Agent Demo"

# Set as active project
gcloud config set project arun-bq-agent-demo

# Enable all required APIs in one command
gcloud services enable \
  bigquery.googleapis.com \
  aiplatform.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

# Application Default Credentials — lets local code auth as you (no API keys in code)
gcloud auth application-default login
```

---

## 5. Phase 1 — BigQuery Data Setup (COMPLETED)

### Step 1 — Open BigQuery console
☰ → BigQuery → lands on BigQuery Studio (left: Explorer panel, right: SQL editor).

### Step 2 — Create dataset
Explorer → ⋮ next to project → **Create dataset**
- Dataset ID: `employees`
- Location: Multi-region → **US** (Vertex AI region later should also be US)

### Step 3 — Sample CSV (`employee_data.csv`)
```csv
employee_id,name,department,salary,hire_date
1,Arun Kumar,Engineering,165000,2019-03-15
2,Priya Sharma,Engineering,142000,2021-06-01
3,John Smith,Sales,98000,2020-01-10
4,Maria Garcia,HR,87000,2018-11-20
5,David Chen,Engineering,178000,2017-05-30
6,Sarah Johnson,Sales,105000,2022-02-14
7,Raj Patel,Finance,120000,2019-09-01
8,Emily Brown,HR,79000,2023-04-18
9,Kevin Lee,Finance,134000,2021-08-23
10,Anita Desai,Engineering,156000,2020-12-05
```

### Step 4 — Create table from upload
⋮ next to `employees` dataset → **Create table**
- Create table from: **Upload** → pick CSV
- Table name: `employee_data`
- Schema: ✅ **Auto detect** (infers INTEGER, STRING, INTEGER, DATE)

### Step 5 — Verify
Click table → tabs:
- **Schema** — confirm types
- **Details** — row count (10), size in bytes
- **Preview** — see rows free of charge

### Step 6 — Test queries

```sql
-- Basic select: note backtick `project.dataset.table` format
SELECT name, department, salary
FROM `arun-bq-agent-demo.employees.employee_data`
ORDER BY salary DESC
LIMIT 5;
```

```sql
-- Aggregation
SELECT department,
       COUNT(*) AS headcount,
       ROUND(AVG(salary), 0) AS avg_salary
FROM `arun-bq-agent-demo.employees.employee_data`
GROUP BY department
ORDER BY avg_salary DESC;
```

```sql
-- Date function
SELECT name,
       hire_date,
       DATE_DIFF(CURRENT_DATE(), hire_date, YEAR) AS years_at_company
FROM `arun-bq-agent-demo.employees.employee_data`
WHERE DATE_DIFF(CURRENT_DATE(), hire_date, YEAR) >= 5;
```

```sql
-- Public dataset (~6M rows, zero setup) — demonstrates scale
SELECT name, SUM(number) AS total
FROM `bigquery-public-data.usa_names.usa_1910_2013`
WHERE state = 'CA'
GROUP BY name
ORDER BY total DESC
LIMIT 10;
```

### CLI equivalents
```bash
# Create dataset
bq mk --dataset --location=US arun-bq-agent-demo:employees

# Load CSV with schema auto-detection
bq load --autodetect --source_format=CSV \
  employees.employee_data employee_data.csv

# Run a query from CLI
bq query --use_legacy_sql=false \
  'SELECT department, AVG(salary) AS avg_salary
   FROM `arun-bq-agent-demo.employees.employee_data`
   GROUP BY department'
```

**Agent's table path:** `arun-bq-agent-demo.employees.employee_data` — this exact string goes into the agent tool description so Gemini knows the table and columns.

---

## 6. Phase 2 — Vertex AI Agent (Local)

### Project structure
```
bq-agent/
├── Dockerfile
├── main.py              # FastAPI app (the API endpoint)
├── agent.py             # Vertex AI agent + BigQuery tool
├── requirements.txt
└── .env                 # GCP_PROJECT_ID=arun-bq-agent-demo
```

### Setup
```bash
mkdir bq-agent && cd bq-agent
python -m venv venv
venv\Scripts\activate          # Windows
pip install fastapi uvicorn google-cloud-bigquery langchain langchain-google-vertexai python-dotenv
```

### `requirements.txt`
```
fastapi
uvicorn
google-cloud-bigquery
google-cloud-aiplatform
langchain-google-vertexai
langchain
python-dotenv
```

### `agent.py`
```python
# agent.py
import os
from dotenv import load_dotenv
load_dotenv()                                    # loads .env into os.environ for local dev

from google.cloud import bigquery
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_google_vertexai import ChatVertexAI
from langchain import hub

# Initialize BigQuery client — uses ADC (Application Default Credentials)
bq_client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])

def run_bigquery_query(sql: str) -> str:
    """
    Tool function: executes a SQL query against BigQuery.
    The LLM calls this with a SQL string it generates.
    Returns results as a string the LLM can read.
    """
    try:
        query_job = bq_client.query(sql)        # run the query
        results = query_job.result()             # wait for results
        rows = [dict(row) for row in results]    # convert to list of dicts
        if not rows:
            return "No results found."
        return str(rows[:20])                    # cap at 20 rows for the LLM
    except Exception as e:
        return f"Query error: {str(e)}"

# Define the tool the LLM can use
bigquery_tool = Tool(
    name="BigQueryTool",
    func=run_bigquery_query,
    description=(
        "Use this tool to query the BigQuery dataset. "
        "Input must be a valid SQL string. "
        "Table: `arun-bq-agent-demo.employees.employee_data`. "
        "Columns: employee_id, name, department, salary, hire_date."
    )
)

# Initialize Gemini via Vertex AI
llm = ChatVertexAI(
    model_name="gemini-1.5-flash",              # or gemini-1.5-pro
    project=os.environ["GCP_PROJECT_ID"],
    location="us-central1",
    temperature=0
)

# Pull the standard ReAct prompt from LangChain hub
prompt = hub.pull("hwchase17/react")

# Build the agent
agent = create_react_agent(llm=llm, tools=[bigquery_tool], prompt=prompt)

# AgentExecutor runs the Reason → Act → Observe loop
agent_executor = AgentExecutor(
    agent=agent,
    tools=[bigquery_tool],
    verbose=True,                                # prints the ReAct loop — study this!
    max_iterations=5,
    handle_parsing_errors=True
)

def ask_agent(question: str) -> str:
    """Entry point called by the FastAPI route."""
    result = agent_executor.invoke({"input": question})
    return result["output"]
```

### `main.py`
```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from agent import ask_agent

app = FastAPI()

class QueryRequest(BaseModel):
    question: str           # natural language question

class QueryResponse(BaseModel):
    answer: str

@app.post("/query", response_model=QueryResponse)
def query_bigquery(request: QueryRequest):
    answer = ask_agent(request.question)
    return QueryResponse(answer=answer)

@app.get("/health")
def health():
    return {"status": "ok"}
```

### Test sequence
```bash
# 1. Test agent directly before the API layer
python -c "from agent import ask_agent; print(ask_agent('What is the average salary in Engineering?'))"

# Watch the verbose output — the ReAct loop:
# Thought → Action: BigQueryTool → Observation → Final Answer
# Understanding and explaining this loop is the core learning of this project.

# 2. Run the API locally
uvicorn main:app --reload --port 8080

# 3. Test endpoint
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"Who is the highest paid employee?\"}"
```

✅ **Checkpoint: if this works, Layers 1 + 2 are proven. Everything after is packaging.**

---

## 7. Phase 3 — Containerize & Deploy to Cloud Run

> ⚠️ **Use Artifact Registry, NOT Container Registry (GCR).** GCR was deprecated and shut down (March 2025). Always say "Artifact Registry"; GCR was its predecessor.

### `Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Deploy steps
```bash
# 1. Create Artifact Registry Docker repository
gcloud artifacts repositories create agent-repo \
  --repository-format=docker \
  --location=us-central1

# 2. Cloud Build builds the Dockerfile remotely and pushes — no local Docker needed
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/arun-bq-agent-demo/agent-repo/bq-agent:v1

# 3. Deploy to Cloud Run
gcloud run deploy bq-agent \
  --image us-central1-docker.pkg.dev/arun-bq-agent-demo/agent-repo/bq-agent:v1 \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=arun-bq-agent-demo \
  --memory 1Gi

# 4. Test the cloud endpoint (URL printed after deploy)
curl -X POST https://bq-agent-xxxxx-uc.a.run.app/query \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"How many employees per department?\"}"
```

**Auth note:** Cloud Run's default service account has project-level access, so BigQuery + Vertex AI auth works automatically — **Workload Identity / ADC in action**. No credentials in code or image.

**UI alternative (most UI-friendly path):** Cloud Run → Create Service → **"Continuously deploy from a repository"** → connect GitHub repo → auto-builds Dockerfile on every push. Built-in continuous deployment.

---

## 8. Phase 4 — Spring Boot Client

Spring Initializr → dependency: **Spring Web** only.

### `application.properties`
```properties
# Replace with your actual Cloud Run URL after deploy
agent.endpoint.url=https://bq-agent-xxxxx-uc.a.run.app
```

### `RestTemplateConfig.java`
```java
// RestTemplateConfig.java
package com.example.bqagent.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class RestTemplateConfig {

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();  // Can add timeouts here for prod
    }
}
```

### `AgentClient.java`
```java
// AgentClient.java
package com.example.bqagent.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.*;

@Service
public class AgentClient {

    // Injected from application.properties
    @Value("${agent.endpoint.url}")
    private String agentEndpointUrl;

    private final RestTemplate restTemplate;

    public AgentClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * Sends a natural language question to the Cloud Run agent
     * and returns the answer string.
     */
    public String askQuestion(String question) {

        // Build the request body
        AgentRequest requestBody = new AgentRequest(question);

        // Set JSON content type
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        // Wrap body + headers into HttpEntity
        HttpEntity<AgentRequest> entity = new HttpEntity<>(requestBody, headers);

        // POST to /query endpoint on Cloud Run
        ResponseEntity<AgentResponse> response = restTemplate.exchange(
            agentEndpointUrl + "/query",
            HttpMethod.POST,
            entity,
            AgentResponse.class
        );

        // Extract the answer from the response body
        return response.getBody().answer();
    }

    // DTO matching the FastAPI request body: { "question": "..." }
    public record AgentRequest(String question) {}

    // DTO matching the FastAPI response body: { "answer": "..." }
    public record AgentResponse(String answer) {}
}
```

### `AgentController.java`
```java
// AgentController.java
package com.example.bqagent.controller;

import com.example.bqagent.client.AgentClient;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/agent")
public class AgentController {

    private final AgentClient agentClient;

    public AgentController(AgentClient agentClient) {
        this.agentClient = agentClient;
    }

    @PostMapping("/ask")
    public String ask(@RequestBody AskRequest request) {
        // Delegates to AgentClient which calls Cloud Run
        return agentClient.askQuestion(request.question());
    }

    public record AskRequest(String question) {}
}
```

### End-to-end test
```bash
mvn spring-boot:run

curl -X POST http://localhost:8080/api/agent/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"Which department has the lowest average salary?\"}"
```

**Full chain:** Spring Boot → Cloud Run → Gemini → BigQuery → back. 🎯

---

## 9. Phase 5 — Extras & Demo Flow

1. **H2/Postgres fallback** — for environments without live cloud access, keep a local simulation: copy `agent.py` → `agent_local.py`, swap `run_bigquery_query` for a local DB query function. Agent code stays identical. Key insight: *"the tool is swappable, the agent doesn't care about the data source."*

2. **Demo flow (under 10 minutes):**
   1. BigQuery console — run one manual query, point out the bytes-scanned estimator
   2. Ask agent a question via curl/Postman — show verbose ReAct logs
   3. Cloud Run service in console — revisions, autoscaling settings
   4. Hit it from Spring Boot
   5. Close with security/cost answers when asked

3. **Digital twin framing:** BigQuery holds the *state/history* of the twin (employee events, metrics); the agent is the *query interface* to the twin. One sentence turns "a SQL chatbot" into "a digital twin query layer."

---

## 10. Key Concepts Q&A

| Question | Answer |
|---|---|
| Why BigQuery? | Serverless, columnar, scales to petabytes, no index management — built for analytics on GCP |
| Why Cloud Run? | Fully managed, scales to zero, container-based — follows 12-factor principles |
| Why Vertex AI + Gemini? | Native GCP AI, ADC auth, no API key management — same IAM as your data |
| Why ReAct agent pattern? | Separates reasoning from tools — LLM decides *when* and *how* to query, not hardcoded SQL |
| How does auth work? | Cloud Run uses Workload Identity / ADC — no credentials in code |
| How would you secure the endpoint? | Cloud Run IAM-only invocation; Spring Boot fetches identity token via service account, sends `Authorization: Bearer` header |
| What if the LLM writes `SELECT *` on a 10TB table? | `maximum_bytes_billed` on query job config, dry-run validation before execution, restrict tool to read-only IAM (`dataViewer` + `jobUser`) |
| How is access controlled in GCP? | Three independent gates: API enablement (does service exist for project?) → IAM (who can call?) → VPC controls (from which networks?) |
| Why does GCP require enabling APIs? | Security (smaller attack surface), cost protection, per-project quota management — explicit opt-in is itself a cloud-native principle |
| Local dev substitute | H2 / Dockerized Postgres behind the same swappable tool interface |

---

## 11. Project Review — Strengths & Gaps

### Strengths
| Requirement | Coverage |
|---|---|
| GCP-native database | BigQuery — shows analytics + AI synergy (stronger than plain Cloud SQL) |
| AI-powered agents | Vertex AI ReAct agent with BigQuery tool |
| Cloud-native deployment | Docker → Artifact Registry → Cloud Run, full container lifecycle |
| Full-stack integration | Spring Boot consuming the endpoint |

**Differentiator:** most demos show static CRUD; this demos an agent that *generates and executes SQL autonomously*.

### Gaps closed
1. H2/local fallback prepared
2. Artifact Registry, not deprecated GCR
3. Security answer ready (IAM-only invocation + identity tokens)
4. BigQuery cost guardrails (`maximum_bytes_billed`, dry-run, read-only IAM)
5. Digital twin framing

### Priority order (limited time)
1. Agent working locally against BigQuery — proves Layers 1+2
2. H2/Postgres swap-in version
3. Deploy via Artifact Registry → Cloud Run
4. Spring Boot client last (simplest, already known cold)

---

## 12. UI vs CLI Reference

| Step | CLI | UI |
|---|---|---|
| Create project | `gcloud projects create` | Project dropdown → New Project |
| Enable APIs | `gcloud services enable` | APIs & Services → Library → Enable |
| Create dataset | `bq mk` | BigQuery → ⋮ next to project → Create dataset |
| Load CSV | `bq load` | Dataset → Create table → Upload + Auto detect |
| Run queries | `bq query` | BigQuery SQL editor |
| Build + push image | `gcloud builds submit` | ⚠️ Gap — use Cloud Shell, or Cloud Run "Deploy from repository" (GitHub auto-build) |
| Deploy Cloud Run | `gcloud run deploy` | Cloud Run → Create Service (forms) |
| Write agent code | local editor | Cloud Shell Editor (browser VS Code, auth automatic) |

**Note:** know the CLI conceptually even when clicking the UI — to script the process for CI/CD, the gcloud commands go into GitHub Actions / Cloud Build YAML.

---

## 13. Project Cleanup / Deletion

**UI:** ☰ → IAM & Admin → Settings → **Shut down** → type project ID → confirm.

**CLI:**
```bash
gcloud projects delete arun-bq-agent-demo
```

Notes:
- 30-day pending deletion — billing stops immediately, resources stop working; restorable within 30 days via Manage Resources → "Resources pending deletion"
- After 30 days: permanently wiped
- Project ID is **never reusable**, even after deletion
- For practice: no need to delete — 10-row BigQuery table costs $0.00, Cloud Run scales to zero. Delete the Cloud Run service alone if desired:
  ```bash
  gcloud run services delete bq-agent --region us-central1
  ```

---

## Status Tracker

- [x] Phase 0 — GCP project + APIs
- [x] Phase 1 — BigQuery dataset, table, test queries ✅ DONE
- [ ] Phase 2 — Agent working locally
- [ ] Phase 3 — Artifact Registry + Cloud Run deploy
- [ ] Phase 4 — Spring Boot client end-to-end
- [ ] Phase 5 — H2 fallback + demo rehearsal
