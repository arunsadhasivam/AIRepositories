# MCP vs A2A - Complete Guide

---

## What is MCP?
Model Context Protocol — connects a **single agent to multiple tools** (vector DB, Redis, Tika, APIs).
Agent pulls all required tools locally and calls them sequentially.

## What is A2A?
Agent-to-Agent protocol — connects **multiple specialized agents** to collaborate,
delegate, and work in parallel on the same task.

---

## Core Difference

| | MCP | A2A |
|---|---|---|
| **What it connects** | Agent to Tools | Agent to Agent |
| **Who does the work** | One agent | Multiple specialized agents |
| **Parallelism** | No | Yes |
| **Best for** | Tool access | Multi-agent coordination |

---

## When to Use What

| Scenario | MCP enough? | A2A needed? |
|---|---|---|
| One agent uses multiple tools | Yes | No |
| Multiple agents collaborate on same task | No | Yes |
| Agent delegates subtask to specialist agent | No | Yes |
| Parallel agents working simultaneously | No | Yes |
| One agent orchestrates many sub-agents | No | Yes |
| Simple RAG with vector + Redis + Tika | Yes | No |
| Complex RAG with specialist agents per domain | No | Yes |

---

## Real World Example - Clinical RAG Pipeline

### MCP alone — sufficient for simple pipeline
```
One Agent
    → pgvector tool     (pulls clinical docs)
    → Redis tool        (caches results)
    → Tika tool         (parses PDFs)
    → Ollama tool       (generates answer)
→ Single agent handles all tools sequentially
```

### A2A needed — specialist agents per domain
```
Orchestrator Agent
    → Agent 1 (Radiology specialist)  → pulls radiology reports
    → Agent 2 (Lab specialist)        → pulls lab results
    → Agent 3 (Prescription specialist) → pulls drug records
    ↓
All 3 run in parallel
    ↓
Orchestrator merges all results → Final Answer
```

---

## Why MCP alone is not enough for multi-agent

- MCP pulls tools to **one agent only**
- That one agent calls all tools **sequentially** — no parallelism
- Cannot delegate subtasks to **specialized agents**
- Cannot coordinate **multiple agents** working simultaneously
- One agent doing everything = **bottleneck at scale**

---

## How MCP and A2A work together

They **complement each other** — not replace:

```
Orchestrator Agent (A2A coordinates)
    ├── Radiology Agent
    │       └── MCP tools: pgvector, Tika
    ├── Lab Agent
    │       └── MCP tools: pgvector, Redis
    └── Prescription Agent
            └── MCP tools: pgvector, drug API
```

- **A2A** = how agents talk to each other
- **MCP** = how each agent accesses its tools

---

## Summary

| | MCP | A2A | MCP + A2A |
|---|---|---|---|
| **Purpose** | Agent gets tools | Agents talk to agents | Full multi-agent system |
| **Parallelism** | No | Yes | Yes |
| **Specialization** | No | Yes | Yes |
| **Complexity** | Low | High | High |
| **Best for** | Simple RAG pipelines | Complex domain-specific RAG | Production enterprise RAG |
| **Your pipeline fit** | Current state | Future scale | Target architecture |
