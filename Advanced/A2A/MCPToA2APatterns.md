# MCP vs A2A - Connection Patterns

---

## Core Mental Model

**MCP = Proxy / Gateway pattern**
**A2A = Direct HTTP REST pattern**

---

## MCP Path - Proxy Pattern

```
Your Agent → MCP Local Server → Remote Tool (Google, Slack, Okta)
```

- MCP local server acts as **managed proxy**
- Underneath it still hits the **remote server**
- MCP registry knows **what tools exist and how to connect**
- Your agent does not need to know remote tool details
- MCP manages the connection, auth, and routing

---

## A2A Direct Path - REST Pattern

```
Your Agent → Direct HTTP → Remote Agent
```

- No proxy — direct call to remote agent endpoint
- Works like a **REST API call** between agents
- Your agent needs to know the **remote agent endpoint**
- You manage the connection yourself

---

## Comparison Table

| | MCP Path | A2A Direct Path |
|---|---|---|
| **Pattern** | Proxy / Gateway | Direct HTTP REST |
| **Discovery** | MCP registry knows what tools exist | You know agent endpoint directly |
| **Who manages connection** | MCP server manages | You manage |
| **Auth management** | MCP handles | You handle |
| **Example** | Agent → MCP → Okta API | Orchestrator → HTTP → Guardrail Agent |
| **Remote server hit** | Yes — MCP proxies to it | Yes — direct call |
| **MCP required** | Yes | No |

---

## When to Use Which

| Scenario | Use |
|---|---|
| Connecting to Google, Slack, Okta | MCP path — managed proxy |
| Agent calling another specialist agent | A2A direct HTTP |
| Tool discovery needed | MCP path — registry handles it |
| Known agent endpoint | A2A direct HTTP |
| Auth managed centrally | MCP path |
| Low latency agent-to-agent call | A2A direct HTTP |

---

## Combined in Your Clinical RAG Pipeline

```
Orchestrator Agent
    │
    ├── MCP path
    │       └── MCP Local Server
    │               ├── Okta (IAM)
    │               ├── Slack (notifications)
    │               └── Google (drive/docs)
    │
    └── A2A Direct HTTP
            ├── Retrieval Agent
            ├── Guardrail Agent
            ├── LLM-as-Judge Agent
            └── PII Masking Agent
```

---

## Key Insight

> MCP is just a **managed proxy** — underneath it still hits the remote server.
> A2A is a **direct HTTP call** — like calling a REST API but between agents.
> Both can coexist in the same pipeline.
> MCP and A2A are **independent protocols that complement each other**.

---

## Summary

| | MCP | A2A | MCP + A2A |
|---|---|---|---|
| **Role** | Tool gateway/proxy | Agent coordinator | Full production architecture |
| **Connects** | Agent to Tools | Agent to Agent | Both |
| **Discovery** | Via MCP registry | Direct endpoint | Both |
| **Remote call** | Via MCP proxy | Direct HTTP | Both |
| **Your pipeline** | Okta, Slack, Google | Retrieval, Judge, Guardrail agents | Target architecture |
