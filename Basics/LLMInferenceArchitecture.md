# LLM Provider Request Flow: Prompt → Endpoint → Inference Engine → Compute → Response

---

## 1. Key Components — What Each Is

| Component | What it is | Analogy |
|---|---|---|
| Endpoint | URL router / load balancer | Nginx reverse proxy |
| Inference Engine | Software that runs the model | Tomcat servlet container |
| Compute | GPU VM hardware | Physical server with JVM |
| Model (Mistral/Claude) | Weights loaded in GPU memory | WAR deployed in Tomcat |
| Response / Stream | Token by token text output | HTTP chunked response |

---

## 2. Where Response is Generated — Inference Engine or Model?

**Short answer:**
- **Model (Mistral)** generates the tokens (deep learning prediction)
- **Inference Engine** manages the process, batching, streaming back to you

```
Model      = generates raw token predictions (deep learning)
Inference  = orchestrates, streams, manages memory
Engine
```

Like:
- **WAR (your code)** = generates the business logic response
- **Tomcat** = manages HTTP, threading, sends response back to client

---

## 3. Full Request Flow — Azure (Mistral + Nomic)

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR APP                                  │
│  LangChain / Python / Java                                       │
│  POST prompt → Azure Endpoint URL                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Public Internet (if app is local)
                           │ Private Network (if app is on Azure)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AZURE ENDPOINT (Load Balancer)                 │
│  - Receives HTTP POST request                                    │
│  - Reads "model" field in request body                          │
│  - Routes to correct GPU VM                                      │
│  - Handles auth (API key validation)                             │
└──────────┬───────────────────────────────┬───────────────────────┘
           │ local private network          │ local private network
           ▼                               ▼
┌──────────────────────┐       ┌──────────────────────────────────┐
│  GPU VM 1            │       │  GPU VM 2                         │
│  ┌────────────────┐  │       │  ┌──────────────────────────────┐ │
│  │ Inference      │  │       │  │ Inference Engine              │ │
│  │ Engine         │  │       │  │ (different instance)          │ │
│  │ (vLLM/TGI)    │  │       │  │ (vLLM/TGI)                   │ │
│  └───────┬────────┘  │       │  └────────────┬─────────────────┘ │
│          │           │       │               │                    │
│  ┌───────▼────────┐  │       │  ┌────────────▼─────────────────┐ │
│  │ Mistral Model  │  │       │  │ Nomic Embedding Model         │ │
│  │ (GPU VRAM)     │  │       │  │ (GPU VRAM)                    │ │
│  │ 32 decoder     │  │       │  │ Encoder layers                │ │
│  │ layers         │  │       │  │ text → vector                 │ │
│  └───────┬────────┘  │       │  └────────────┬─────────────────┘ │
│          │           │       │               │                    │
└──────────┼───────────┘       └───────────────┼────────────────────┘
           │                                   │
           │ token stream                      │ vector array
           ▼                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AZURE ENDPOINT (Load Balancer)                 │
│  - Collects token stream from Mistral VM                        │
│  - Collects vector from Nomic VM                                │
│  - Streams response back to your app                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR APP                                  │
│  Receives streamed tokens / vector                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. What Inference Engine Does (Inside GPU VM)

Inference Engine = software layer between endpoint and model.  
Examples: **vLLM**, **TGI (Text Generation Inference)**, **Triton**

```
Inference Engine responsibilities:
├── Receives prompt from endpoint
├── Tokenizes prompt (text → token IDs)
├── Manages GPU memory (KV cache)
├── Batches multiple requests together
├── Calls model forward pass (actual deep learning)
├── Applies decoding strategy (top-p, top-k, temperature)
├── Streams tokens back one by one as generated
└── Manages max_tokens, stop sequences
```

---

## 5. What Model (Mistral) Does Inside Inference Engine

```
Inference Engine calls Mistral:

Token IDs arrive
        ↓
Mistral embedding layer (token IDs → vectors)
        ↓
Layer 1 of 32: Masked Self-Attention + FFN
        ↓
Layer 2 of 32: Masked Self-Attention + FFN
        ↓
... (32 layers total)
        ↓
Layer 32: final hidden state
        ↓
Linear layer → logits (score for every word in vocab)
        ↓
Temperature applied → top-p/top-k filter → sample next token
        ↓
Token sent back to Inference Engine → streamed to endpoint → your app
        ↓
Repeat until <eos> or max_tokens reached
```

---

## 6. Streaming — How Tokens Come Back

**Non-streaming (wait for full response):**
```
Your App → POST prompt
                ↓ wait...
                ↓ wait...
                ↓ wait...
Your App ← full text response (all at once)
```

**Streaming (token by token — like ChatGPT typing effect):**
```
Your App → POST prompt (stream=True)
Your App ← "I"        (token 1 arrives)
Your App ← " am"      (token 2 arrives)
Your App ← " going"   (token 3 arrives)
Your App ← " to"      (token 4 arrives)
Your App ← " the"     (token 5 arrives)
Your App ← " store"   (token 6 arrives)
Your App ← [DONE]
```

**Streaming code — Azure Mistral:**
```python
import requests
import json

response = requests.post(
    url="https://my-project.eastus.inference.ml.azure.com/v1/chat/completions",
    headers={
        "Authorization": "Bearer <azure-api-key>",
        "Content-Type": "application/json"
    },
    json={
        "model": "mistral-7b",
        "messages": [{"role": "user", "content": "I am going to the"}],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": True          # ← enable streaming
    },
    stream=True                 # ← requests lib stream mode
)

# Process each token as it arrives
for line in response.iter_lines():
    if line:
        # Each line is a server-sent event
        data = line.decode("utf-8").replace("data: ", "")
        if data != "[DONE]":
            chunk = json.loads(data)
            token = chunk["choices"][0]["delta"].get("content", "")
            print(token, end="", flush=True)  # print token immediately
```

---

## 7. All 3 Providers — Full Flow Comparison

### Anthropic (Claude):

```
Your App
    ↓ POST https://api.anthropic.com/v1/messages
Anthropic API Gateway (endpoint)
    ↓ private internal network
Anthropic GPU Cluster
    ├── Inference Engine (Anthropic proprietary)
    └── Claude Model (weights in GPU memory)
            ↓ token stream
Anthropic API Gateway
    ↓
Your App (streamed response)
```

**Streaming code — Anthropic:**
```python
import anthropic

client = anthropic.Anthropic(api_key="<key>")

# Streaming response
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=500,
    messages=[{"role": "user", "content": "I am going to the"}]
) as stream:
    for token in stream.text_stream:
        print(token, end="", flush=True)  # each token printed as arrives
```

---

### Google Gemini:

```
Your App
    ↓ POST https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent
Google API Gateway (endpoint)
    ↓ private GCP internal network
Google TPU Pod Cluster
    ├── Inference Engine (Google proprietary)
    └── Gemini Model (weights in TPU memory)
            ↓ token stream
Google API Gateway
    ↓
Your App (streamed response)
```

**Streaming code — Gemini:**
```python
import google.generativeai as genai

genai.configure(api_key="<key>")
model = genai.GenerativeModel("gemini-2.0-flash")

# Streaming response
for chunk in model.generate_content("I am going to the", stream=True):
    print(chunk.text, end="", flush=True)  # each chunk printed as arrives
```

---

## 8. Response — Where is it Generated?

| Step | Where | What happens |
|---|---|---|
| Token prediction | **Model (Mistral/Claude/Gemini)** | Deep learning forward pass, next token selected |
| Token streaming | **Inference Engine (vLLM/TGI)** | Sends token back to endpoint as generated |
| Response routing | **Endpoint (Load Balancer)** | Forwards stream back to your app |
| Response received | **Your App** | Assembles tokens into full text |

**Model generates. Inference Engine streams. Endpoint routes. Your app receives.**

---

## 9. Full Component Responsibility Summary

| Component | Lives in | Responsibility |
|---|---|---|
| Endpoint | Azure/Anthropic/Google load balancer | Auth, routing, API interface |
| Inference Engine | GPU VM (vLLM / TGI / proprietary) | Tokenize, batch, decode strategy, stream |
| Model weights | GPU VRAM | Actual deep learning prediction |
| Compute (GPU VM) | Azure/GCP data center | Hardware that runs inference engine + model |
| Your App | Local or cloud VM | Send prompt, receive stream, process response |

---

## 10. WebSphere Analogy — Full Flow

| WebSphere | LLM Provider |
|---|---|
| Client HTTP request | Your app POST to endpoint |
| Nginx/IHS (reverse proxy) | Endpoint (load balancer) |
| Tomcat/WebSphere (servlet container) | Inference Engine (vLLM/TGI) |
| Your WAR/Servlet doPost() | Model forward pass (deep learning) |
| HTTP chunked response | Token stream response |
| Local call: IHS → Tomcat → WAR | Local call: Endpoint → Inference Engine → Model |
