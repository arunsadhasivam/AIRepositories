# BigQuery + Vertex AI Agent (ADK) + Spring Boot — Learning & Reference Guide

**Goal:** Build an AI agent using the **Agent Development Kit (ADK)** that autonomously queries BigQuery via the first-party `BigQueryToolset`, deploy it as a containerized API on Cloud Run, and consume it from a local Spring Boot application.

**Focus areas:** Cloud-native full-stack applications, AI-powered autonomous agents, GCP + Vertex AI.

**Stack (100% GCP-native):** ADK + Gemini (Vertex AI) + BigQueryToolset + Artifact Registry + Cloud Run + Spring Boot client.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Layer 1 — BigQuery Fundamentals](#2-layer-1--bigquery-fundamentals)
3. [Key GCP Concepts](#3-key-gcp-concepts)
4. [Phase 0 — GCP Project Setup](#4-phase-0--gcp-project-setup)
5. [Phase 1 — BigQuery Data Setup (COMPLETED)](#5-phase-1--bigquery-data-setup-completed)
6. [Phase 2 — ADK Agent (Local)](#6-phase-2--adk-agent-local)
7. [Phase 3 — Deploy to Cloud Run](#7-phase-3--deploy-to-cloud-run)
8. [Phase 4 — Spring Boot Client](#8-phase-4--spring-boot-client)
9. [Phase 5 — Extras & Demo Flow](#9-phase-5--extras--demo-flow)
10. [Key Concepts Q&A](#10-key-concepts-qa)
11. [Framework Note — ADK vs LangChain](#11-framework-note--adk-vs-langchain)
12. [UI vs CLI Reference](#12-ui-vs-cli-reference)
13. [Project Cleanup / Deletion](#13-project-cleanup--deletion)
14. [Troubleshooting Log](#14-troubleshooting-log-real-errors-hit-and-fixed)

---

## 1. Architecture Overview

```
┌──────────────────┐         ┌─────────────────────────┐
│   Local Machine   │         │   Artifact Registry      │
│                   │         │   (Docker image store)   │
│   Spring Boot     │         └───────────┬─────────────┘
│   RestTemplate    │                     │ deploy (adk deploy cloud_run)
└────────┬──────────┘                     ▼
         │  HTTP POST        ┌─────────────────────────┐
         └──────────────────►│   Cloud Run — ADK Agent  │
                             │   ADK API Server         │
                             │   BigQueryToolset        │
                             └─────┬──────────────┬────┘
                          LLM call │              │ SQL query
                                   ▼              ▼
                          ┌─────────────┐  ┌─────────────┐
                          │  Vertex AI   │  │  BigQuery    │
                          │  (Gemini)    │  │  employees   │
                          └─────────────┘  └─────────────┘
```

**Flow:** Spring Boot sends natural-language question → Cloud Run ADK agent → Gemini reasons and decides to call a BigQuery tool → `BigQueryToolset` executes SQL → results back to Gemini → natural-language answer → Spring Boot.

**Pattern:** Reason → Act (tool call) → Observe (result) → Reason again. The LLM decides *when* and *how* to query — SQL is not hardcoded. ADK uses Gemini's **native tool calling** (structured function calls), which is more reliable than text-based parsing.

**Bonus:** ADK sessions give the agent **conversation memory** — it remembers context across questions in the same session.

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

### Local machine setup — gcloud CLI (needed once you run agent code locally)

The **gcloud CLI** (Google Cloud SDK) is the command-line tool for GCP. It provides three commands used in this project: `gcloud` (all services), `bq` (BigQuery), and is also required to create local credentials (ADC) — without it, local Python code fails with `DefaultCredentialsError`.

**1. Install on Windows (click by click):**
1. Download **GoogleCloudSDKInstaller.exe** from https://cloud.google.com/sdk/docs/install
2. Double-click the .exe → accept defaults on every screen (single user, default folder)
3. On the FINAL screen keep these checked ✅:
   - *Start Google Cloud SDK Shell*
   - *Run `gcloud init`*
4. Click Finish → a terminal opens automatically and `gcloud init` starts
5. **Important:** any OTHER terminals already open will NOT see `gcloud` — open new ones

**2. `gcloud init` prompts (Login #1 — authenticates the CLI tool):**
- *"You must log in to continue. Would you like to log in (Y/n)?"* → **Y** → browser opens → sign in with the account that owns your GCP project → Allow
- *"Pick cloud project to use:"* → type the number next to your project ID
- Default region prompt → pick `us-central1` or press Enter to skip

**3. Create ADC credentials (Login #2 — for YOUR PYTHON CODE; commonly missed):**
```bash
# Creates the credential file that google.auth.default() reads.
# gcloud init alone does NOT do this. Skipping it causes:
# DefaultCredentialsError: Your default credentials were not found
gcloud auth application-default login

# Set quota project so Vertex AI calls bill correctly (use YOUR project ID)
gcloud auth application-default set-quota-project <your-project-id>
```

The ADC file lands at `C:\Users\<you>\AppData\Roaming\gcloud\application_default_credentials.json`.

**4. Verify everything:**
```bash
# CLI installed and version
gcloud --version

# Which account + project the CLI is using
gcloud config list

# THE test that matters: can Python code find credentials?
python -c "import google.auth; c, p = google.auth.default(); print('OK:', p)"
```
If the last command prints your project ID, local code will authenticate. Restart `adk web` after fixing credentials — they're loaded at import time, so a restart is required.

**5. Windows install issues:**

| Problem | Fix |
|---|---|
| `'gcloud' is not recognized` | Open a NEW terminal; or use the **"Google Cloud SDK Shell"** Start-menu shortcut; or add `C:\Users\<you>\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin` to PATH |
| PowerShell: *"running scripts is disabled"* | Use Command Prompt (cmd) instead, or `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Installer hangs / blocked | Antivirus interference — temporarily disable, or use the zip install: extract `google-cloud-cli-windows-x86_64.zip` to `C:\gcloud`, run `install.bat` |

**6. gcloud command quick reference (the ones used in this project):**
```bash
gcloud auth login                              # login the CLI tool
gcloud auth application-default login          # create ADC for code
gcloud config set project <id>                 # switch active project
gcloud config list                             # show active account/project
gcloud services enable <api>                   # enable an API
gcloud projects create / delete <id>           # project lifecycle
gcloud run deploy / services delete            # Cloud Run
gcloud artifacts repositories create           # Artifact Registry
gcloud builds submit --tag <image>             # Cloud Build
bq mk / bq load / bq query                     # BigQuery CLI (installed with the SDK)
adk web / adk api_server / adk deploy          # ADK CLI (installed via pip, separate from SDK)
```

**ADC concept (one sentence):** the same `google.auth.default()` line works in three environments with zero code change — locally it finds the ADC file, on Cloud Run it gets the service account token from the metadata server, in CI it can use workload identity federation. That's the "no credentials in code" story.

---

## 5. Phase 1 — BigQuery Data Setup (COMPLETED)

### Step 1 — Open BigQuery console
☰ → BigQuery → lands on BigQuery Studio (left: Explorer panel, right: SQL editor).

### Step 2 — Create dataset
Explorer → ⋮ next to project → **Create dataset**
- Dataset ID: `employees`
- Location: Multi-region → **US** (Vertex AI region should also be a US region)

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

**Agent's table path:** `arun-bq-agent-demo.employees.employee_data` — this exact string goes into the agent instruction so Gemini knows the table and columns.

---

## 6. Phase 2 — ADK Agent (Local)

The **Agent Development Kit (ADK)** is GCP's first-party, code-first framework for building AI agents. It is optimized for Gemini and Vertex AI, ships a built-in `BigQueryToolset` (no custom query tool needed), and deploys to Cloud Run with one command.

### Install
```bash
mkdir bq-agent && cd bq-agent
python -m venv venv
venv\Scripts\activate          # Windows
pip install "google-adk[gcp]"
```

> ⚠️ **`google-adk` alone is NOT enough for the BigQuery toolset.** The BigQuery tools are lazy-loaded optional dependencies. Without the `[gcp]` extra, the agent fails at runtime with `ImportError: cannot import name 'dataplex_v1' from 'google.cloud'`. The `[gcp]` extras group (verified against package metadata) pulls in `google-cloud-bigquery`, `google-cloud-bigquery-storage`, and `google-cloud-dataplex`. Note: `[extensions]` does NOT include these. Quotes around the package name are required on Windows.

### Required project structure (ADK convention)
```
bq-agent/
├── my_bq_agent/
│   ├── __init__.py          # contains: from . import agent
│   ├── agent.py             # must define a variable named root_agent
│   └── .env                 # Vertex AI + project config
└── requirements.txt
```

### `requirements.txt`
```
google-adk[gcp]
```

### Naming rules — three independent names

| Name | Your choice? | Rules |
|---|---|---|
| `Agent(name="...")` | Yes | Valid Python identifier: letters, digits, underscores only — `employee_data_agent` ✅, `my-agent` ❌, `my agent` ❌. Reserved word `user` not allowed. Internal ADK identifier — appears only in logs/traces, never as a cloud resource |
| Folder / app name | Yes | Same identifier style (it's a Python package). **The folder name = the app name in API URLs** (`/apps/<folder>/...`) and in the Spring Boot config |
| Cloud Run `--service_name` | Yes | Opposite convention: lowercase + **hyphens**, no underscores — `bq-agent` ✅, `bq_agent` ❌ |

Nothing ties the three together except your code and deploy command. The underscore-vs-hyphen flip (Python uses `_`, cloud resource names use `-`) is the common gotcha.

### `my_bq_agent/__init__.py`
```python
from . import agent
```

**Why this line (Python vs Java imports):** Java's `import` is only name resolution for the compiler — it runs nothing. Python's `import` is **execution**: importing a file runs it top to bottom. The chain when you run `adk web`:

```
adk web scans the parent folder
  → finds my_bq_agent/ with __init__.py        (it's a package)
    → imports the package → __init__.py runs
      → "from . import agent" → agent.py RUNS top to bottom
        → root_agent = Agent(...) executes → agent exists
          → ADK finds the variable root_agent → registered ✅
```

Without that line, `agent.py` never executes, `root_agent` is never created, and ADK reports *"No root_agent found."* The closest Java equivalent isn't an import — it's `Class.forName("...Driver")` for JDBC: the point is not to use a name but to **trigger initialization** (static block registers the driver ↔ top-level code creates `root_agent`).

### `my_bq_agent/.env`
```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=arun-bq-agent-demo
GOOGLE_CLOUD_LOCATION=us-central1
```

**What `GOOGLE_CLOUD_LOCATION` is:** the region where Gemini inference runs — a choice, not a lookup. `us-central1` is the widest-availability Vertex AI region and matches every other region in this project (Artifact Registry, Cloud Run). It is independent of the BigQuery dataset location (`US` multi-region): BigQuery location = where the *data* lives; this setting = where *model inference* runs. Keeping both in the US avoids cross-region latency. Valid options: Console → Vertex AI → region dropdown.

### `my_bq_agent/agent.py`
```python
# agent.py
import google.auth
from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryToolset, BigQueryCredentialsConfig
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

# Load Application Default Credentials —
# works locally (gcloud auth application-default login) AND on Cloud Run automatically
credentials, project_id = google.auth.default()

# Configure the toolset to use ADC
credentials_config = BigQueryCredentialsConfig(credentials=credentials)

# Restrict to READ-ONLY — blocks the LLM from ever running INSERT/UPDATE/DELETE.
# This is a built-in cost/safety guardrail enforced by the toolset itself.
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)

# First-party BigQuery tools: list datasets, get table schema, execute SQL.
# No custom query code needed — the toolset provides everything.
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config,
    bigquery_tool_config=tool_config
)

# The root agent — ADK looks for this exact variable name: root_agent
root_agent = Agent(
    name="bq_data_agent",
    model="gemini-2.5-flash",                 # Gemini via Vertex AI. NOTE: gemini-2.0-flash was RETIRED June 1, 2026 (returns 404)
    description="Agent that answers questions about employee data in BigQuery.",
    instruction=(
        "You are a data analyst. Answer questions by querying BigQuery. "
        "Use the table `arun-bq-agent-demo.employees.employee_data` "
        "with columns: employee_id, name, department, salary, hire_date."
    ),
    tools=[bigquery_toolset]
)
```


NOTE:
=====
 - enable Agent API then it works.


 <img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/956b9f22-969b-471a-a9df-664dc5bd52d4" />



### Test locally — built-in dev UI (chat)

**Prerequisites (one time):** gcloud SDK installed, `gcloud auth application-default login` done (see Phase 0 / Troubleshooting), `.env` present in the agent folder.

```bash
# From the bq-agent/ folder — the PARENT of my_bq_agent/, NOT inside it
adk web
```
Open **http://localhost:8000**:
1. Top-left **dropdown** → select the agent (the folder name)
2. Type questions in the chat box:
   - "What is the average salary in Engineering?"
   - "Who is the highest paid employee?"
   - "How many employees per department?"
3. Click the response (or the **Events** tab) → **trace view** showing every internal step: model decision → which BigQuery tool was called → the exact SQL generated → raw result → final answer
4. Test **session memory**: ask "and what about Sales?" after the Engineering question — the agent resolves "what about" from session history

The trace view is the most valuable part — study it until each step makes sense. Running from the wrong folder (inside the agent package instead of its parent) is the most common startup mistake.

### Test locally — plain REST API
```bash
adk api_server
```
Serves the same agent as a REST API on http://localhost:8000 (this is exactly what runs on Cloud Run later).

```bash
# 1. Create a session first (sessions give the agent conversation memory)
curl -X POST http://localhost:8000/apps/my_bq_agent/users/u1/sessions/s1 \
  -H "Content-Type: application/json" -d "{}"

# 2. Ask a question
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d "{
    \"app_name\": \"my_bq_agent\",
    \"user_id\": \"u1\",
    \"session_id\": \"s1\",
    \"new_message\": {
      \"role\": \"user\",
      \"parts\": [{ \"text\": \"What is the average salary in Engineering?\" }]
    }
  }"
```

The response is a JSON array of events — the final answer is the text part of the last event.

✅ **Checkpoint: if `adk web` answers questions from your BigQuery table, Layers 1 + 2 are proven.**

---

## 7. Phase 3 — Deploy to Cloud Run

> ⚠️ **Use Artifact Registry, NOT Container Registry (GCR).** GCR was deprecated and shut down (March 2025). Artifact Registry is its successor.

### One-command deploy (ADK native)
```bash
# Builds the container, pushes to Artifact Registry, deploys to Cloud Run — all in one
adk deploy cloud_run \
  --project=arun-bq-agent-demo \
  --region=us-central1 \
  --service_name=bq-agent \
  my_bq_agent
```

NOTE:
======
# ADK Cloud Run Deployment — `--service_name` Guide

## What is `--service_name`?

The `--service_name` flag sets the name of the **Cloud Run service** created during deployment.

```bash
adk deploy cloud_run \
  --project=arun-bq-agent-demo \
  --region=us-central1 \
  --service_name=bq-agent \
  my_bq_agent
```

It appears in:
- **Cloud Run Console URL:** `https://console.cloud.google.com/run/detail/us-central1/bq-agent`
- **Service HTTPS Endpoint:** `https://bq-agent-<hash>-uc.a.run.app`
- **CLI listing:** `gcloud run services list`

> If `--service_name` is omitted, ADK defaults to the agent folder name (e.g., `my_bq_agent`).

---


## Naming Rules

| Rule | Detail |
|------|--------|
| Characters allowed | Lowercase letters, numbers, hyphens (`-`) only |
| Must start with | A letter |
| Max length | 49 characters |
| No spaces or underscores | ❌ Not allowed |

---

## Valid Examples

```bash
--service_name=bq-agent
--service_name=my-agent
--service_name=arun-demo
--service_name=bq-agent-v2
--service_name=bigquery-assistant-prod
```

## Invalid Examples

```bash
--service_name=My_Agent       # ❌ uppercase + underscore
--service_name=1-bq-agent     # ❌ starts with a number
--service_name=bq agent       # ❌ space not allowed
```

prerequisties permission:
============================

- check the service account by https://console.cloud.google.com/iam-admin/iam?project=bigqueryagent-1234
- copy the service account name 


## list service account 

```
gcloud projects describe bigqueryagent-1234 --format="value(projectNumber)"
```


## Grant role by command - build role:

```
gcloud projects add-iam-policy-binding bigqueryagent-1234 --member="serviceAccount:1234-compute@developer.gserviceaccount.com" --role="roles/cloudbuild.builds.builder"
```

## Grant storage role

```
gcloud projects add-iam-policy-binding bigqueryagent-1234 --member="serviceAccount:1234-compute@developer.gserviceaccount.com" --role="roles/storage.objectAdmin"

```

## Also in service account add build and deploy admin right


- https://console.cloud.google.com/iam-admin/iam?project=bigqueryagent-1234 and select the service account give the permission for your
  login email

## service account settings

<img width="1415" height="725" alt="image" src="https://github.com/user-attachments/assets/db524a2c-89e9-40e4-83aa-688371cdc236" />


E.g:
====



```
   adk deploy cloud_run   --project=bigqueryagent-1234  --region=us-central1  --service_name=bigquery-vertex  .
```

## important

- . at the end current project location if not work try in command prompt check adk and gcloud both command works
  
## for bash:

```
adk deploy cloud_run \
  --project=bigqueryagent-1234 \
  --region=us-central1 \
  --service_name=bigquery-vertex .       

```

## for windows:

- ^ for windows instead of \ multiline
-  
 
```
adk deploy cloud_run ^
  --project=bigqueryagent-1234 ^
  --region=us-central1 ^
  --service_name=bigquery-vertex   C:\ARUNWorkspace\BigQuery  



```

<img width="3342" height="1780" alt="image" src="https://github.com/user-attachments/assets/fa65c42c-b811-48cc-b11f-6a7b7d46f3f1" />

It prints a service URL like `https://bq-agent-xxxxx-uc.a.run.app`.

### What it does underneath (know this conceptually)
```bash
# 1. Create Artifact Registry Docker repository
gcloud artifacts repositories create agent-repo \
  --repository-format=docker --location=us-central1

# 2. Cloud Build builds a Dockerfile remotely and pushes the image
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/arun-bq-agent-demo/agent-repo/bq-agent:v1

# 3. Deploy the image to Cloud Run
gcloud run deploy bq-agent \
  --image us-central1-docker.pkg.dev/arun-bq-agent-demo/agent-repo/bq-agent:v1 \
  --region us-central1
```

### Test the cloud endpoint
```bash
# Same two-call pattern as local, just the Cloud Run URL
curl -X POST https://bq-agent-xxxxx-uc.a.run.app/apps/my_bq_agent/users/u1/sessions/s1 \
  -H "Content-Type: application/json" -d "{}"

curl -X POST https://bq-agent-xxxxx-uc.a.run.app/run \
  -H "Content-Type: application/json" \
  -d "{
    \"app_name\": \"my_bq_agent\",
    \"user_id\": \"u1\",
    \"session_id\": \"s1\",
    \"new_message\": {
      \"role\": \"user\",
      \"parts\": [{ \"text\": \"How many employees per department?\" }]
    }
  }"
```

**Auth note:** Cloud Run's default service account has project-level access, so BigQuery + Vertex AI auth works automatically — **Workload Identity / ADC in action**. No credentials in code or image. The same `google.auth.default()` line works locally and in the cloud.

---

## 8. Phase 4 — Spring Boot Client

Spring Initializr → dependency: **Spring Web** only.

The ADK API server uses a **session-based** API: create a session once, then post messages to `/run`. Sessions = conversation memory.

### `application.properties`
```properties
# Replace with your actual Cloud Run URL after deploy
agent.endpoint.url=https://bq-agent-xxxxx-uc.a.run.app
# The ADK app name = the agent folder name
agent.app.name=my_bq_agent
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
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class AgentClient {

    // Cloud Run base URL, injected from application.properties
    @Value("${agent.endpoint.url}")
    private String baseUrl;

    // ADK app name (= the agent folder name)
    @Value("${agent.app.name}")
    private String appName;

    private final RestTemplate restTemplate;

    // Jackson mapper to parse the ADK event array response
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AgentClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * Asks the ADK agent a natural-language question.
     * Flow: 1) create a session, 2) POST the message to /run, 3) parse the last event's text.
     */
    public String askQuestion(String question) {

        // Fixed user id for this client; unique session id per question
        // (reuse the same sessionId across calls to keep conversation memory)
        String userId = "spring-client";
        String sessionId = UUID.randomUUID().toString();

        // Common JSON headers
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        // ---- Step 1: create the session ----
        // POST {baseUrl}/apps/{app}/users/{user}/sessions/{session}  with empty JSON body
        String sessionUrl = String.format("%s/apps/%s/users/%s/sessions/%s",
                baseUrl, appName, userId, sessionId);
        restTemplate.postForEntity(sessionUrl,
                new HttpEntity<>("{}", headers), String.class);

        // ---- Step 2: send the question to /run ----
        // Body shape required by ADK:
        // { app_name, user_id, session_id, new_message: { role, parts: [{text}] } }
        Map<String, Object> body = Map.of(
                "app_name", appName,
                "user_id", userId,
                "session_id", sessionId,
                "new_message", Map.of(
                        "role", "user",
                        "parts", List.of(Map.of("text", question))
                )
        );

        ResponseEntity<String> response = restTemplate.exchange(
                baseUrl + "/run",
                HttpMethod.POST,
                new HttpEntity<>(body, headers),
                String.class
        );

        // ---- Step 3: parse the response ----
        // ADK returns a JSON ARRAY of events (tool calls, tool results, model text).
        // The final natural-language answer is the text part of the LAST event.
        try {
            JsonNode events = objectMapper.readTree(response.getBody());
            JsonNode lastEvent = events.get(events.size() - 1);          // last event
            return lastEvent.path("content")                              // event.content
                            .path("parts").get(0)                         // first part
                            .path("text").asText("No answer returned");   // its text
        } catch (Exception e) {
            // Surface parsing problems clearly instead of swallowing them
            throw new RuntimeException("Failed to parse agent response", e);
        }
    }
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
        // Delegates to AgentClient which calls the ADK API on Cloud Run
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

**Full chain:** Spring Boot → Cloud Run (ADK) → Gemini → BigQuery → back. 🎯

---

## 9. Phase 5 — Extras & Demo Flow

1. **Local DB fallback** — for environments without live cloud access, keep a local simulation: define a custom function tool (a plain Python function decorated/registered as an ADK tool) that queries H2/Postgres instead of using `BigQueryToolset`. The agent definition stays identical. Key insight: *"the tool is swappable, the agent doesn't care about the data source."*

2. **Demo flow (under 10 minutes):**
   1. BigQuery console — run one manual query, point out the bytes-scanned estimator
   2. `adk web` — ask a question, walk through the visual trace (model decision → tool call → SQL → result → answer)
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
| Why ADK? | First-party agent framework: built-in BigQueryToolset, enforced read-only mode, one-command Cloud Run deploy, Cloud Trace observability, session-based memory |
| Why the agent pattern? | Separates reasoning from tools — LLM decides *when* and *how* to query, not hardcoded SQL. Uses native tool calling (structured), not text parsing |
| How does auth work? | Cloud Run uses Workload Identity / ADC — `google.auth.default()` works the same locally and in the cloud, no credentials in code |
| How would you secure the endpoint? | Cloud Run IAM-only invocation; Spring Boot fetches identity token via service account, sends `Authorization: Bearer` header |
| What if the LLM writes `SELECT *` on a 10TB table? | `WriteMode.BLOCKED` in `BigQueryToolConfig` blocks writes; add `maximum_bytes_billed`, dry-run validation, read-only IAM (`dataViewer` + `jobUser`) for scan-cost control |
| How is access controlled in GCP? | Three independent gates: API enablement (does service exist for project?) → IAM (who can call?) → VPC controls (from which networks?) |
| Why does GCP require enabling APIs? | Security (smaller attack surface), cost protection, per-project quota management — explicit opt-in is itself a cloud-native principle |
| What do sessions add? | Conversation memory — the agent remembers earlier questions/answers in the same session |
| Local dev substitute | H2 / Dockerized Postgres behind a swappable custom function tool |

---

## 11. Framework Note — ADK vs LangChain

This project originally used LangChain, then migrated to ADK. Reasons for the migration (useful to articulate):

| Aspect | LangChain | ADK |
|---|---|---|
| Origin | Third-party | First-party GCP framework |
| BigQuery tool | Hand-written custom tool | Built-in `BigQueryToolset` (list datasets, schemas, execute SQL) |
| Write protection | Manual (prompt + IAM only) | `WriteMode.BLOCKED` enforced in the toolset |
| Deploy | Manual Dockerfile + gcloud | `adk deploy cloud_run` one command |
| Dev UI | None (custom FastAPI) | `adk web` with visual trace of every tool call |
| Observability | DIY | Cloud Trace integration out of the box |
| Sessions/memory | DIY | Built-in session service |
| API stability | Breaking change at v1.0 (`AgentExecutor` removed; legacy moved to `langchain-classic`) | Stable, aligned with Vertex AI roadmap |

Practical note hit during development: `from langchain.agents import AgentExecutor` fails on LangChain ≥ 1.0 — the v1 migration replaced `create_react_agent` + `AgentExecutor` with `create_agent`, and moved legacy components to `langchain-classic`. Migrating to ADK removed the dependency entirely.

---

## 12. UI vs CLI Reference

| Step | CLI | UI |
|---|---|---|
| Create project | `gcloud projects create` | Project dropdown → New Project |
| Enable APIs | `gcloud services enable` | APIs & Services → Library → Enable |
| Create dataset | `bq mk` | BigQuery → ⋮ next to project → Create dataset |
| Load CSV | `bq load` | Dataset → Create table → Upload + Auto detect |
| Run queries | `bq query` | BigQuery SQL editor |
| Test agent | `adk api_server` + curl | `adk web` chat UI with trace panel |
| Deploy | `adk deploy cloud_run` | Cloud Run → "Deploy from repository" (GitHub auto-build) |
| Write agent code | local editor | Cloud Shell Editor (browser VS Code, auth automatic) |

**Note:** know the CLI conceptually even when clicking the UI — to script the process for CI/CD, the gcloud/adk commands go into GitHub Actions / Cloud Build YAML.

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

## 14. Troubleshooting Log (real errors hit and fixed)

| Error | Root cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'AgentExecutor' from 'langchain.agents'` | LangChain v1.0 removed the legacy agent APIs (`create_react_agent` → `create_agent`; legacy moved to `langchain-classic`) | Migrated to ADK entirely (see Section 11) |
| `ImportError: Fail to load module. cannot import name 'dataplex_v1' from 'google.cloud'` | ADK lazy-loads BigQuery tools; their dependencies are NOT in the base `google-adk` install | `pip install "google-adk[gcp]"` — the `gcp` extras group includes `google-cloud-bigquery`, `google-cloud-bigquery-storage`, `google-cloud-dataplex`. Note `[extensions]` does NOT include them |
| `DefaultCredentialsError: Your default credentials were not found` (`_CLOUD_SDK_MISSING_CREDENTIALS`) | `google.auth.default()` found no ADC file — `gcloud auth application-default login` was never run (it's a separate login from `gcloud init`) | Install gcloud SDK → `gcloud init` → `gcloud auth application-default login` → `set-quota-project` → restart `adk web` (credentials are loaded at import time, so a restart is required) |
| `'gcloud' is not recognized` (Windows) | SDK not on PATH, or terminal opened before install | Open a NEW terminal; or use the "Google Cloud SDK Shell" Start-menu shortcut; or add `...\Google\Cloud SDK\google-cloud-sdk\bin` to PATH |
| PowerShell: `running scripts is disabled on this system` | Execution policy blocks `gcloud.ps1` | Use Command Prompt (cmd) instead, or `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `No root_agent found` | `__init__.py` missing or doesn't contain `from . import agent`, so agent.py never executes | Add the import line; see the import-chain explanation in Phase 2 |
| `adk web` can't find the agent | Running from INSIDE the agent folder | Run from the PARENT folder of the agent package |
| 404 on `publishers/google/models/gemini-2.0-flash` | **Model lifecycle:** gemini-2.0-flash was discontinued June 1, 2026 — shut-down models return 404 | Change to `model="gemini-2.5-flash"` (retirement no earlier than Oct 16, 2026). Production lesson: models have deprecation/shutdown dates — keep the model name in config/env (e.g. `MODEL_NAME` in `.env`), monitor deprecation notices, test the replacement before cutoff |

**Debugging pattern worth internalizing:** every one of these errors was diagnosed by reading the traceback bottom-up — the last line names the real error, and the file/line chain above it shows exactly where in the import sequence it failed (e.g., `__init__.py` line 1 → `agent.py` line 9 → `google.auth.default()`).

---

## Status Tracker

- [x] Phase 0 — GCP project + APIs + gcloud SDK + ADC
- [x] Phase 1 — BigQuery dataset, table, test queries ✅ DONE
- [ ] Phase 2 — ADK agent working locally (`adk web`) — IN PROGRESS (deps + ADC fixed, chat test pending)
- [ ] Phase 3 — `adk deploy cloud_run`
- [ ] Phase 4 — Spring Boot client end-to-end
- [ ] Phase 5 — Local DB fallback + demo rehearsal
