# Inference Engine, Compute & Model — Where Everything Lives

---

## 1. Core Relationship

**Inference Engine lives INSIDE the Compute (GPU VM).**  
They are not separate — all three layers are inside the same machine.

```
GPU VM (Compute — Azure Data Center)
└── Inference Engine (vLLM / TGI)        ← software process running on VM
        └── Model Weights                 ← loaded into GPU VRAM
            (Mistral / Nomic / LLaMA)
```

---

## 2. Layer Breakdown

| Layer | What it is | Where it lives |
|---|---|---|
| Compute (GPU VM) | Physical/virtual GPU machine | Azure data center |
| Inference Engine | Software process (vLLM/TGI) | Running inside GPU VM |
| Model Weights | Mistral/Nomic parameters | GPU VRAM of same VM |

---

## 3. WebSphere Exact Analogy

| WebSphere | Azure LLM |
|---|---|
| Physical server | GPU VM (compute) |
| JVM process running on server | Inference Engine (vLLM) running on VM |
| WAR/EAR loaded in JVM heap | Model weights loaded in GPU VRAM |
| JVM manages threads, memory | Inference Engine manages batching, KV cache |
| Servlet doPost() executes | Model forward pass (deep learning) executes |
| HTTP response back to client | Token stream back to endpoint |

---

## 4. Full Stack — Single GPU VM

```
┌─────────────────────────────────────────────┐
│           GPU VM (Azure Compute)             │
│                                              │
│  ┌───────────────────────────────────────┐  │
│  │      Inference Engine (vLLM / TGI)    │  │
│  │                                       │  │
│  │  - Receives tokenized prompt          │  │
│  │  - Manages GPU memory (KV cache)      │  │
│  │  - Batches multiple requests          │  │
│  │  - Applies decoding strategy          │  │
│  │  - Streams tokens back                │  │
│  │                                       │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │     Model Weights (GPU VRAM)    │  │  │
│  │  │                                 │  │  │
│  │  │  Mistral 7B                     │  │  │
│  │  │  - 32 decoder layers            │  │  │
│  │  │  - ~14GB in GPU memory          │  │  │
│  │  │  - Runs forward pass            │  │  │
│  │  │  - Predicts next token          │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│                                              │
│  GPU Hardware: A100 80GB / V100 32GB         │
│  CPU RAM: 64-256GB                           │
│  Disk: Model weights stored here on start    │
└─────────────────────────────────────────────┘
```

---

## 5. Multiple Models — Multiple VMs

```
Azure Compute Cluster (same region)
│
├── GPU VM 1
│   └── Inference Engine (vLLM)
│           └── Mistral 7B (GPU VRAM)
│
├── GPU VM 2
│   └── Inference Engine (vLLM)
│           └── Nomic Embedding (GPU VRAM)
│
└── GPU VM 3
    └── Inference Engine (vLLM)
            └── LLaMA 3 (GPU VRAM)
```

Each model = its own VM = its own inference engine instance.

---

## 6. How Model Gets Loaded Into VM

```
Step 1: Azure ML deployment created
        ↓
Step 2: Azure pulls model weights from Azure Blob Storage
        (model files downloaded to VM disk)
        ↓
Step 3: Inference Engine (vLLM) starts as process on VM
        ↓
Step 4: vLLM loads model weights from disk → GPU VRAM
        (like JVM loading WAR classes into heap)
        ↓
Step 5: VM ready — inference engine listening for requests
        ↓
Step 6: Endpoint (load balancer) registers this VM
        → now reachable via Azure endpoint URL
```

---

## 7. Request Flow — Inside Single VM

```
Request arrives at GPU VM
        ↓
Inference Engine (vLLM) receives prompt
        ↓
Tokenizer: text → token IDs
        ↓
Inference Engine calls Model forward pass
        ↓
Model (Mistral in GPU VRAM):
  token IDs → 32 decoder layers → logits
        ↓
Inference Engine applies:
  temperature → top-p → top-k → sample next token
        ↓
Token streamed back to endpoint
        ↓
Repeat until <eos> or max_tokens
```

---

## 8. Inference Engine Options

| Inference Engine | Used by | Key feature |
|---|---|---|
| vLLM | Azure, self-hosted | PagedAttention — efficient GPU memory |
| TGI (Text Generation Inference) | HuggingFace, Azure | Flash Attention, continuous batching |
| Triton Inference Server | NVIDIA, Azure | Multi-framework support |
| Ollama | Local only | Simple local deployment |
| Anthropic proprietary | Anthropic cloud only | Closed, optimized for Claude |
| Google proprietary | Google cloud only | Optimized for TPU + Gemini |

---

## 9. WebSphere InitialContext vs LLM Endpoint — Exact Analogy

**Yes. Exactly the same pattern.**

In WebSphere — `InitialContext` is your entry point to lookup and access any resource deployed in the cell cluster (DataSource, EJB, JMS Queue).

In LLM — Endpoint URL is your entry point to access any model deployed in the compute cluster (Mistral, Nomic, LLaMA).

---

### Side by Side:

| WebSphere | LLM Provider |
|---|---|
| `new InitialContext()` | `POST https://my-project.eastus.inference.ml.azure.com` |
| JNDI name = `java:comp/env/jdbc/myDS` | Model name = `mistral-7b` in request body |
| InitialContext looks up cell cluster | Endpoint routes to compute cluster |
| Cell cluster has DataSource on node | Compute cluster has Mistral on GPU VM |
| DataSource returns DB connection | Inference Engine returns token stream |
| You use connection → execute SQL | You use stream → read generated text |
| Connection pool managed by JVM | GPU inference pool managed by vLLM |
| Result returned to your servlet | Token stream returned to your app |

---

### Code Comparison:

**WebSphere InitialContext lookup:**
```java
// InitialContext = entry point to cell cluster resources
InitialContext ctx = new InitialContext();

// Lookup resource by JNDI name — routes to correct node in cluster
DataSource ds = (DataSource) ctx.lookup("java:comp/env/jdbc/myDS");

// Use resource — executes on cluster node
Connection conn = ds.getConnection();
ResultSet rs = conn.prepareStatement("SELECT * FROM users").executeQuery();
```

**LLM Endpoint call (same pattern):**
```python
import requests

# Endpoint URL = entry point to compute cluster
# model name = JNDI name (routes to correct GPU VM)
response = requests.post(
    url="https://my-project.eastus.inference.ml.azure.com/v1/chat/completions",
    headers={"Authorization": "Bearer <key>"},
    json={
        "model": "mistral-7b",        # ← like JNDI name, routes to correct VM
        "messages": [{"role": "user", "content": "I am going to the"}],
        "stream": True                # ← get token stream back
    },
    stream=True
)

# Use resource — token stream executes on GPU VM
for line in response.iter_lines():
    if line:
        print(line.decode("utf-8"))   # tokens stream back like ResultSet rows
```

---

### Full Flow Comparison:

```
WebSphere:
Your Servlet
    ↓ new InitialContext()
Cell Cluster (Deployment Manager)
    ↓ JNDI lookup → routes to correct node
Node (JVM)
    ↓ DataSource → Connection Pool
DB executes SQL → ResultSet rows returned
    ↓
Your Servlet receives rows

LLM Provider:
Your App
    ↓ POST endpoint URL
Compute Cluster (Load Balancer)
    ↓ model name → routes to correct GPU VM
GPU VM (Inference Engine vLLM)
    ↓ Model (Mistral) → forward pass → token prediction
Tokens streamed back one by one
    ↓
Your App receives token stream
```

---

### Key Insight:
- `InitialContext` hides **which node** in cell cluster serves the resource
- `Endpoint URL` hides **which GPU VM** in compute cluster runs the model
- Both are **location transparency** — you use a name/URL, infrastructure routes to correct machine
- Both return a **stream of results** — ResultSet rows vs token stream

---

## 10. One Line Summary

```
Compute (GPU VM)  =  Server
Inference Engine  =  JVM / Tomcat
Model Weights     =  WAR deployed in Tomcat
```

**Server → JVM → WAR  ==  GPU VM → vLLM → Mistral**
