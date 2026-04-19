

# Ollama Internals — Reference Guide
> Based on Mistral-7B-Instruct-v0.3 running on NVIDIA RTX 2000 Ada (8GB VRAM)

---

## What is Ollama?

Ollama is a local LLM inference server. It:
- Exposes a REST API (`http://127.0.0.1:11434`) to run LLMs locally
- Manages model loading, GPU offloading, tokenization, and token generation
- Uses **llama.cpp** under the hood via GGUF model format
- Works with LangChain, OpenAI-compatible clients, and direct HTTP calls

---

## Startup Lifecycle

```
1. Server starts → binds to 127.0.0.1:11434
2. Discovers GPU (CUDA/Vulkan/CPU)
3. On first request → loads model from disk (GGUF file)
4. Offloads layers to GPU based on available VRAM
5. Allocates KV Cache
6. Runner starts → ready for inference
```

### From your log:
```
OLLAMA_HOST:        http://127.0.0.1:11434
OLLAMA_KEEP_ALIVE:  5m0s       ← model stays loaded 5 min after last request
OLLAMA_MAX_LOADED_MODELS: 1    ← only 1 model in VRAM at a time
OLLAMA_NUM_PARALLEL: 1         ← 1 concurrent request
OLLAMA_MAX_QUEUE:   512        ← max queued requests
Runner started in:  6.63 sec
```

---

## GPU Discovery

```
GPU:     NVIDIA RTX 2000 Ada Generation Laptop GPU
VRAM:    8.0 GiB total / 7.6 GiB available
CUDA compute capability: 8.9  (Ada Lovelace — very capable)
Library: CUDA v13
```

Ollama picks CUDA over CPU/Vulkan automatically when available. All 33 model layers fully offloaded to GPU → **maximum inference speed**.

---

## Model Format: GGUF + Quantization

### Your model:
```
File:       Mistral-7B-Instruct-v0.3
Format:     GGUF V3
File size:  4.07 GiB
Params:     7.25 Billion
Quant type: Q4_K_M (4-bit medium)
BPW:        4.83 bits per weight
```

### Quantization explained:

| Type | Bits | VRAM Usage | Quality |
|------|------|------------|---------|
| f16 | 16 | ~14 GB | Full |
| Q8_0 | 8 | ~7.2 GB | Near-full |
| **Q4_K_M** | **~4** | **~4.1 GB** | **Good (your setup)** |
| Q3_K_M | ~3 | ~3.1 GB | Moderate |
| Q2_K | ~2 | ~2.2 GB | Lower |

### Tensor breakdown in your model:
| Tensor Type | Count | Used For |
|---|---|---|
| f32 | 65 | Norms, output layers (precision-critical) |
| q4_K | 193 | Bulk transformer weights (compressed) |
| q6_K | 33 | Slightly more precise mid-tier weights |

---

## Model Architecture (Mistral-7B)

```
Architecture:     LLaMA (Mistral variant)
Layers:           32 transformer blocks
Embedding dim:    4096
Attention heads:  32 (query) / 8 (key-value) ← GQA
FFN hidden dim:   14336
Vocab size:       32768
Max context:      32768 tokens (train), 4096 (your runtime)
Tokenizer:        SentencePiece (SPM)
BOS token:        1 '<s>'
EOS token:        2 '</s>'
```

### Grouped Query Attention (GQA):
- 32 Q heads share 8 KV heads (4:1 ratio)
- Reduces KV cache size by 4x
- Mistral's efficiency optimization vs vanilla MHA

---

## Memory Layout (Your Runtime)

```
CUDA0 model weights:   4097.52 MiB   ← all 33 layers on GPU
CUDA0 KV cache:         512.00 MiB   ← K: 256 MiB + V: 256 MiB
CUDA0 compute buffer:   112.01 MiB   ← attention compute scratch
CPU model buffer:        72.00 MiB   ← minimal CPU fallback
Total:                 ~4.8 GiB
```

---

## Inference Pipeline (Token Generation)

```
Request (prompt text)
    ↓
Tokenizer (text → token IDs)
    ↓
Prefill phase: all prompt tokens processed in one batch (n_batch=512)
    ↓
32 Transformer layers (on GPU):
    - RMSNorm → attention (Q/K/V) → GQA → FFN → RMSNorm
    ↓
KV Cache: stores K/V tensors to avoid recomputation
    ↓
Logits over 32768 vocab tokens
    ↓
Sampling (temperature / top_p / top_k / repeat_penalty)
    ↓
Next token selected → decoded → streamed back
    ↓
Repeat until </s> or max tokens
```

---

## Hyperparameters You Can Tweak

### Via API / Modelfile (`OPTIONS` block):

| Parameter | Default | Your Log | What It Controls | When to Change |
|---|---|---|---|---|
| `num_ctx` | 2048 | **4096** (VRAM auto) | Max tokens in context window | Increase for long docs; costs VRAM |
| `temperature` | 0.8 | — | Randomness of token sampling | Lower (0.1–0.3) for RAG/factual tasks |
| `top_p` | 0.9 | — | Nucleus sampling cumulative prob cutoff | Lower = more focused |
| `top_k` | 40 | — | Sample from top-K token candidates | Lower = more deterministic |
| `repeat_penalty` | 1.1 | — | Penalize recently used tokens | Increase if output loops/repeats |
| `num_predict` | -1 | — | Max output tokens (-1 = unlimited) | Cap for latency control |
| `num_gpu` | auto | **33** (all) | Transformer layers offloaded to GPU | Reduce if VRAM overflows |
| `num_thread` | auto | **6** | CPU threads (non-GPU ops) | Match physical core count |
| `num_batch` | 512 | **512** | Tokens in one prefill batch | Larger = faster prompt processing |
| `flash_attention` | false | **auto→enabled** | Memory-efficient attention kernel | Leave auto; helps long contexts |
| `mmap` | true | **false** | Memory-map model file | false = faster inference |

### Via Environment Variables (server-level):

| Variable | Your Value | Purpose |
|---|---|---|
| `OLLAMA_CONTEXT_LENGTH` | 0 (auto) | Force specific context length |
| `OLLAMA_KEEP_ALIVE` | 5m0s | Model unload timeout |
| `OLLAMA_MAX_LOADED_MODELS` | 1 | Max models in VRAM |
| `OLLAMA_NUM_PARALLEL` | 1 | Concurrent inference requests |
| `OLLAMA_FLASH_ATTENTION` | false | Server-default for flash attn |
| `OLLAMA_GPU_OVERHEAD` | 0 | Reserved VRAM buffer |

---

## Context Window vs VRAM

Your GPU auto-set `num_ctx=4096` based on 8GB VRAM. The model supports up to 32768 tokens.

| num_ctx | KV Cache Size (approx) | Notes |
|---|---|---|
| 4096 | ~512 MiB | **Your current setup** |
| 8192 | ~1 GiB | Needs ~500 MiB more VRAM |
| 16384 | ~2 GiB | Tight on 8GB |
| 32768 | ~4 GiB | Won't fit with model weights |

To increase: set `OLLAMA_CONTEXT_LENGTH=8192` in environment before starting Ollama.

---

## Sampling Strategy Quick Reference

```
temperature=0.0  → greedy (always picks highest prob token) — deterministic
temperature=0.1  → near-deterministic — good for RAG, classification
temperature=0.7  → balanced — general chat
temperature=1.0  → more random — creative writing
temperature>1.2  → often incoherent

top_p=0.9 + top_k=40 → standard combo
top_p=0.5 + top_k=10 → highly focused output
```

---

## Flash Attention

```
llama_context: Flash Attention was auto, set to enabled
```

Flash Attention (FA2) rewrites the attention kernel to avoid materializing the full N×N attention matrix. Instead it computes in tiles. On your Ada GPU (compute 8.9), this is hardware-accelerated.

Benefit: Enables longer contexts with same VRAM. Especially useful when `num_ctx` > 4096.

---

## Ollama REST API Quick Reference

```bash
# Generate (non-streaming)
POST http://127.0.0.1:11434/api/generate
{
  "model": "mistral",
  "prompt": "your prompt",
  "stream": false,
  "options": {
    "temperature": 0.2,
    "top_p": 0.9,
    "num_ctx": 4096,
    "num_predict": 512
  }
}

# Chat (OpenAI-compatible)
POST http://127.0.0.1:11434/api/chat
{
  "model": "mistral",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}

# List loaded models
GET http://127.0.0.1:11434/api/tags

# Check running model
GET http://127.0.0.1:11434/api/ps
```

---

## Your Setup Summary

| Property | Value |
|---|---|
| Model | Mistral-7B-Instruct-v0.3 |
| Quantization | Q4_K_M (4-bit medium) |
| GPU | NVIDIA RTX 2000 Ada 8GB |
| Layers on GPU | 33/33 (full offload) |
| VRAM used | ~4.8 GiB |
| Context window | 4096 tokens |
| Flash Attention | Enabled (auto) |
| Batch size | 512 tokens |
| Model load time | ~6.6 seconds |
| Ollama version | 0.18.3 |
| API endpoint | http://127.0.0.1:11434 |
