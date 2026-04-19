# Encoder-Decoder Integration in Transformers

---

## 1. Overview

A Transformer has two main components:
- **Encoder** — reads and understands the input
- **Decoder** — generates the output using encoder's understanding

```
Input Text → [Tokenizer] → [Encoder] → context vectors
                                              ↓ (K, V)
Output Text ← [Tokenizer] ← [Decoder] ← cross-attention
```

---

## 2. Model Selection (First Decision)

Choose model based on task. Wrong model = no encoder or decoder hooks available.

| Model | Architecture | Task |
|---|---|---|
| T5, FLAN-T5, BART | Encoder + Decoder | Translation, Summarization, Q&A |
| BERT, RoBERTa | Encoder only | Classification, Embeddings |
| GPT, LLaMA, Mistral | Decoder only | Text Generation |

> **JSF Analogy**: Like choosing a JSF component that exposes `PhaseListener` hooks.  
> If component doesn't expose them — you can't override. Same with decoder-only models.

---

## 3. Integration Points (6 Total)

---

### 3.1 Tokenizer Level (Pre-Encoding)

**What happens:**
- Raw text → token IDs (integers)
- Adds special tokens: `<pad>`, `<eos>`, `<bos>`
- Produces attention mask (1 = real token, 0 = padding)

**Code:**
```python
tokenizer = T5Tokenizer.from_pretrained("t5-small")

# Text → token IDs + attention mask
inputs = tokenizer(
    "translate English to French: Hello",
    return_tensors="pt",
    padding=True,
    truncation=True,
    max_length=512
)

# inputs.input_ids    → tensor of token integers
# inputs.attention_mask → tensor of 1s and 0s
```

---

### 3.2 Encoder Forward Pass

**What happens:**
- Token IDs → dense vectors (embeddings)
- Positional encoding added
- N stacked self-attention layers (all tokens attend to all tokens)
- Output: rich context vectors shape `(batch, src_seq_len, d_model)`

**Code:**
```python
# Run encoder explicitly
encoder_output = model.encoder(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask
)

# Shape: (batch=1, src_seq_len=12, d_model=512)
encoder_hidden_states = encoder_output.last_hidden_state
print(encoder_hidden_states.shape)  # torch.Size([1, 12, 512])
```

---

### 3.3 Encoder → Decoder Bridge (Cross-Attention) ⭐

**This is the only structural wiring between encoder and decoder.**

**What happens:**
- Encoder's `last_hidden_state` → passed as **K (Keys)** and **V (Values)** into every decoder layer
- Decoder's own output → becomes **Q (Query)**
- Decoder "asks" encoder: *"what should I focus on in the source?"*

**Dimension flow:**
```
Encoder output:  (batch, src_len, d_model)  → K, V
Decoder query:   (batch, tgt_len, d_model)  → Q
Cross-attention: Q x K^T → scores → weighted sum of V
Output:          (batch, tgt_len, d_model)
```

**Code:**
```python
# Pass encoder output explicitly to decoder
decoder_output = model.decoder(
    input_ids=decoder_input_ids,
    encoder_hidden_states=encoder_hidden_states,   # ← K, V source
    encoder_attention_mask=inputs.attention_mask   # ← masks padding
)
```

> **JSF Analogy**: Like `afterPhase()` in `PhaseListener` — encoder output flows  
> into decoder the same way phase output flows into the next lifecycle phase.

---

### 3.4 Teacher Forcing (Training-Time Integration)

**What happens:**
- During training, decoder input = target shifted right
- Instead of feeding predicted token → feed ground truth token
- Prevents error accumulation during training

**Example:**
```
Target sentence:  "Bonjour comment allez vous"
Decoder input:    <start> Bonjour comment allez
Decoder label:    Bonjour comment allez vous <end>
```

**Code:**
```python
# During training — labels provided = teacher forcing applied internally
loss = model(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask,
    labels=target_ids       # ← triggers teacher forcing automatically
).loss

loss.backward()
```

---

### 3.5 Autoregressive Loop (Inference-Time Integration)

**What happens:**
- Encoder runs **once**
- Decoder runs **N times** — one per output token
- Each step: previous token(s) → decoder → next token
- Stops at `<eos>` token or `max_length`

```
Step 1: <start>           → decoder → "Bonjour"
Step 2: <start> Bonjour   → decoder → "comment"
Step 3: <start> Bonjour comment → decoder → "allez"
...
```

**Code:**
```python
# Full autoregressive generation
output_ids = model.generate(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask,
    max_length=50,
    num_beams=4,          # beam search (explore multiple paths)
    early_stopping=True   # stop at <eos>
)
```

---

### 3.6 Decoding Strategy (Sampling Control)

**What happens:**
- Controls HOW the decoder picks the next token from probability distribution
- Does NOT change model weights — only changes selection logic

| Strategy | Parameter | Behavior |
|---|---|---|
| Greedy | `num_beams=1` | Always pick highest probability token |
| Beam Search | `num_beams=4` | Explore top-N paths simultaneously |
| Sampling | `do_sample=True` | Random pick weighted by probability |
| Top-K | `top_k=50` | Sample from top 50 tokens only |
| Top-P (nucleus) | `top_p=0.9` | Sample from tokens covering 90% probability mass |
| Temperature | `temperature=0.7` | < 1 = sharper, > 1 = more random |

**Code:**
```python
output_ids = model.generate(
    input_ids=inputs.input_ids,
    max_length=50,
    do_sample=True,        # enable sampling
    top_k=50,              # top-K sampling
    top_p=0.9,             # nucleus sampling
    temperature=0.7,       # sharpness control
    repetition_penalty=1.2 # penalize repeated tokens
)
```

---

## 4. Full Integration Code (End-to-End)

```python
from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch

# ── STEP 1: Load encoder-decoder model ──────────────────────
model_name = "t5-small"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

# ── STEP 2: Tokenize input (Integration Point 1) ─────────────
input_text = "translate English to French: Hello, how are you?"
inputs = tokenizer(input_text, return_tensors="pt", padding=True)

# ── STEP 3: Encoder forward pass (Integration Point 2) ───────
encoder_output = model.encoder(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask
)
encoder_hidden_states = encoder_output.last_hidden_state
# Shape: (1, src_seq_len, 512)

# ── STEP 4: Autoregressive decode (Integration Points 3,4,5) ─
output_ids = model.generate(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask,
    max_length=50,
    num_beams=4,
    early_stopping=True
)
# Internally: encoder_hidden_states passed as K,V to each decoder layer

# ── STEP 5: Decode token IDs → text (Integration Point 6) ───
output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
print("Output:", output_text)
# → "Bonjour, comment allez-vous?"
```

---

## 5. Integration Points Summary

| # | Integration Point | When | What flows |
|---|---|---|---|
| 1 | Tokenizer encode | Before encoder | Text → token IDs + attention mask |
| 2 | Encoder forward | Once per input | Token IDs → context vectors (K, V) |
| 3 | Cross-attention bridge | Every decoder layer | enc_hidden_states as K, V |
| 4 | Teacher forcing | Training only | Ground truth token as decoder input |
| 5 | Autoregressive loop | Inference only | Previous output token as next decoder input |
| 6 | Decoding strategy | Inference only | Probability → selected token |

---

## 6. LangChain Integration

In LangChain, integration point is only the **model task string** — everything else is internal.

```python
from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline

# "text2text-generation" = encoder-decoder (T5, FLAN-T5, BART)
# "text-generation"      = decoder-only (GPT, LLaMA)
pipe = pipeline("text2text-generation", model="google/flan-t5-base")

llm = HuggingFacePipeline(pipeline=pipe)
result = llm.invoke("Translate to French: Hello")
```

> In LangChain / Ollama — you cannot access raw encoder or decoder separately.  
> For full control, use HuggingFace `transformers` directly.

---

## 7. JSF Lifecycle Analogy

| JSF | Transformer |
|---|---|
| Choose component with `PhaseListener` support | Choose encoder-decoder model (T5, BART) |
| `beforePhase()` — hook before phase | Tokenizer encode — hook before encoder |
| Phase executes | Encoder forward pass |
| `afterPhase()` — hook after phase | Cross-attention bridge — encoder output flows to decoder |
| Render Response phase | Autoregressive decode loop |
| Component with no `PhaseListener` | Decoder-only model (GPT) — no encoder hook |
