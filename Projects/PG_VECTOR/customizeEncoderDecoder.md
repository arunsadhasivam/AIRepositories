# Encoder & Decoder Override Examples in Transformers

---

## 1. Why Override?

| Override Type | Goal |
|---|---|
| Encoder override | Change how input is understood (custom embeddings, layer hooks) |
| Decoder override | Change how output is generated (token selection, stopping, constraints) |

> **JSF Analogy**: Encoder override = `beforePhase()`, Decoder override = `afterPhase()`  
> You intercept the lifecycle at the point you need to control.

---

## 2. Encoder Overrides

---

### 2.1 Hook Into Encoder Hidden States (Per Layer)

**What:** Extract intermediate encoder layer outputs — not just final layer.  
**Why:** Different layers capture different abstractions (syntax vs semantics).

```python
from transformers import T5Tokenizer, T5ForConditionalGeneration
from torch import nn

tokenizer = T5Tokenizer.from_pretrained("t5-small")
model = T5ForConditionalGeneration.from_pretrained("t5-small")

# Storage for intermediate layer outputs
layer_outputs = []

# Register forward hook on encoder layer 0
def encoder_hook(module, input, output):
    # output[0] shape: (batch, seq_len, d_model)
    layer_outputs.append(output[0].detach())

# Attach hook to encoder block 0 (of N total blocks)
hook = model.encoder.block[0].register_forward_hook(encoder_hook)

# Run encoder — hook fires automatically
inputs = tokenizer("translate English to French: Hello", return_tensors="pt")
encoder_out = model.encoder(input_ids=inputs.input_ids)

print("Layer 0 output shape:", layer_outputs[0].shape)
# torch.Size([1, seq_len, 512])

# Always remove hook after use to avoid memory leak
hook.remove()
```

---

### 2.2 Override Encoder Embeddings (Custom Token Representation)

**What:** Replace default token embeddings with your own before encoder runs.  
**Why:** Domain-specific vocabulary (medical, legal) where pretrained embeddings are weak.

```python
import torch
from torch import nn

# Get default embedding dimension
d_model = model.config.d_model  # 512 for t5-small

# Custom embedding layer — same output dim as model expects
custom_embedding = nn.Embedding(
    num_embeddings=tokenizer.vocab_size,
    embedding_dim=d_model
)

# Replace model's shared embedding with custom one
model.shared = custom_embedding           # encoder + decoder input embedding
model.encoder.embed_tokens = custom_embedding  # encoder specifically

# Now encoder uses your embeddings instead of pretrained ones
inputs = tokenizer("Hello world", return_tensors="pt")
encoder_out = model.encoder(input_ids=inputs.input_ids)
print("Encoder output with custom embeddings:", encoder_out.last_hidden_state.shape)
```

---

### 2.3 Modify Encoder Output Before Passing to Decoder

**What:** Intercept encoder's final output and transform it before cross-attention.  
**Why:** Apply domain adaptation, scaling, or injection of external knowledge.

```python
import torch

inputs = tokenizer(
    "translate English to French: Good morning",
    return_tensors="pt"
)

# Step 1: Run encoder
encoder_output = model.encoder(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask
)

# Step 2: Intercept and modify hidden states
hidden_states = encoder_output.last_hidden_state  # (batch, seq_len, d_model)

# Example: scale encoder output (domain boosting)
modified_hidden_states = hidden_states * 1.2

# Example: inject external knowledge vector at position 0
knowledge_vector = torch.zeros_like(hidden_states[:, 0:1, :])  # (1, 1, d_model)
modified_hidden_states[:, 0:1, :] += knowledge_vector

# Step 3: Pass MODIFIED encoder output to decoder manually
decoder_input_ids = torch.tensor([[model.config.decoder_start_token_id]])

decoder_output = model.decoder(
    input_ids=decoder_input_ids,
    encoder_hidden_states=modified_hidden_states,        # ← modified K, V
    encoder_attention_mask=inputs.attention_mask
)
print("Decoder output shape:", decoder_output.last_hidden_state.shape)
```

---

### 2.4 Custom Encoder Attention Mask

**What:** Override which tokens the encoder can attend to.  
**Why:** Force encoder to ignore certain positions (e.g., boilerplate, headers).

```python
import torch

inputs = tokenizer(
    "translate English to French: [HEADER] Hello how are you [FOOTER]",
    return_tensors="pt"
)

# Default mask: all 1s (attend to everything)
attention_mask = inputs.attention_mask.clone()

# Override: mask out first 2 tokens (force ignore [HEADER])
attention_mask[:, 0:2] = 0  # 0 = ignore these positions

encoder_output = model.encoder(
    input_ids=inputs.input_ids,
    attention_mask=attention_mask  # ← custom mask
)
print("Encoder ran with custom attention mask")
```

---

## 3. Decoder Overrides

---

### 3.1 LogitsProcessor — Override Token Scores

**What:** Intercept raw token probability scores before sampling.  
**Why:** Boost/suppress specific tokens at every generation step.

```python
from transformers import LogitsProcessor, LogitsProcessorList

class BoostTokenProcessor(LogitsProcessor):
    def __init__(self, boost_token_ids, boost_factor=2.0):
        # Store which tokens to boost and by how much
        self.boost_token_ids = boost_token_ids
        self.boost_factor = boost_factor

    def __call__(self, input_ids, scores):
        # scores shape: (batch, vocab_size) — called every decode step
        for token_id in self.boost_token_ids:
            # Multiply logit score → increases probability after softmax
            scores[:, token_id] *= self.boost_factor
        return scores

class BanTokenProcessor(LogitsProcessor):
    def __init__(self, ban_token_ids):
        self.ban_token_ids = ban_token_ids

    def __call__(self, input_ids, scores):
        for token_id in self.ban_token_ids:
            # Set to -inf → token will never be selected
            scores[:, token_id] = float("-inf")
        return scores

# Tokens to boost (formal French greeting)
boost_ids = tokenizer.encode("Bonjour", add_special_tokens=False)
# Tokens to ban
ban_ids = tokenizer.encode("Salut", add_special_tokens=False)

inputs = tokenizer("translate English to French: Hello", return_tensors="pt")

output_ids = model.generate(
    input_ids=inputs.input_ids,
    logits_processor=LogitsProcessorList([
        BoostTokenProcessor(boost_ids, boost_factor=3.0),
        BanTokenProcessor(ban_ids)
    ]),
    max_length=50
)
print(tokenizer.decode(output_ids[0], skip_special_tokens=True))
```

---

### 3.2 StoppingCriteria — Custom Stop Condition

**What:** Stop generation on your own condition, not just `<eos>`.  
**Why:** Stop on keyword, length, punctuation, or custom business rule.

```python
from transformers import StoppingCriteria, StoppingCriteriaList

class StopOnKeyword(StoppingCriteria):
    def __init__(self, stop_token_ids):
        # List of token ID sequences that trigger stop
        self.stop_token_ids = stop_token_ids

    def __call__(self, input_ids, scores, **kwargs):
        # Check if last generated token matches any stop token
        last_token = input_ids[0][-1].item()
        return last_token in self.stop_token_ids

class StopAfterNSentences(StoppingCriteria):
    def __init__(self, tokenizer, max_sentences=2):
        self.tokenizer = tokenizer
        self.max_sentences = max_sentences
        # Period token ID
        self.period_id = tokenizer.encode(".", add_special_tokens=False)[0]

    def __call__(self, input_ids, scores, **kwargs):
        # Count periods in generated output so far
        generated = input_ids[0].tolist()
        sentence_count = generated.count(self.period_id)
        return sentence_count >= self.max_sentences

inputs = tokenizer("summarize: The quick brown fox jumps. It is very fast. It lives in the forest.", return_tensors="pt")

output_ids = model.generate(
    input_ids=inputs.input_ids,
    stopping_criteria=StoppingCriteriaList([
        StopAfterNSentences(tokenizer, max_sentences=1)  # stop after 1 sentence
    ]),
    max_length=100
)
print(tokenizer.decode(output_ids[0], skip_special_tokens=True))
```

---

### 3.3 prefix_allowed_tokens_fn — Constrain to Valid Format

**What:** At each decode step, restrict which tokens are allowed.  
**Why:** Force output to be valid JSON, SQL, or domain-specific format.

```python
import json

# Define which tokens are valid at each position
def json_constrained_prefix(batch_id, input_ids):
    # Get current generated text
    generated_so_far = tokenizer.decode(input_ids, skip_special_tokens=True)

    # Allow only tokens that keep output valid JSON-like
    if generated_so_far.endswith("{"):
        # After opening brace, only allow quote (start of key)
        return tokenizer.encode('"', add_special_tokens=False)
    elif generated_so_far.endswith("}"):
        # After closing brace, only allow eos
        return [tokenizer.eos_token_id]
    else:
        # Otherwise allow all tokens
        return list(range(tokenizer.vocab_size))

inputs = tokenizer("generate JSON: name is John age is 30", return_tensors="pt")

output_ids = model.generate(
    input_ids=inputs.input_ids,
    prefix_allowed_tokens_fn=json_constrained_prefix,  # ← constrain here
    max_length=50
)
print(tokenizer.decode(output_ids[0], skip_special_tokens=True))
```

---

### 3.4 Forced / Banned Words

**What:** Declarative way to force or ban specific words without custom class.  
**Why:** Simpler than `LogitsProcessor` for straightforward word-level control.

```python
inputs = tokenizer("translate English to French: Hello", return_tensors="pt")

# Force the word "Bonjour" to appear in output
force_word_ids = [tokenizer.encode("Bonjour", add_special_tokens=False)]

# Ban the word "Salut" from appearing
bad_word_ids = [tokenizer.encode("Salut", add_special_tokens=False)]

output_ids = model.generate(
    input_ids=inputs.input_ids,
    force_words_ids=force_word_ids,   # ← must appear
    bad_words_ids=bad_word_ids,       # ← must not appear
    num_beams=4,                      # beam search required for force_words
    max_length=50
)
print(tokenizer.decode(output_ids[0], skip_special_tokens=True))
```

---

## 4. Override Summary Table

| Override | Class/Parameter | Encoder/Decoder | JSF Equivalent |
|---|---|---|---|
| Layer hook | `register_forward_hook` | Encoder | `PhaseListener.afterPhase()` on specific phase |
| Custom embeddings | `model.shared = custom_embed` | Encoder | Custom `Converter` in JSF binding |
| Modify enc output | Manual `model.decoder(encoder_hidden_states=...)` | Bridge | Pass modified data between phases |
| Custom attn mask | `attention_mask` override | Encoder | Filter which inputs reach the component |
| Token score boost/ban | `LogitsProcessor` | Decoder | `afterPhase()` — modify output before render |
| Custom stop | `StoppingCriteria` | Decoder | Custom `PhaseListener` exit condition |
| Format constraint | `prefix_allowed_tokens_fn` | Decoder | Validator in Render Response phase |
| Forced/banned words | `force_words_ids` / `bad_words_ids` | Decoder | Whitelist/blacklist in response filter |

---

## 5. Practical Combinations for Better Generation

| Goal | Settings |
|---|---|
| More accurate output | `num_beams=4`, `length_penalty=1.0` |
| More creative output | `do_sample=True`, `temperature=0.8`, `top_p=0.9` |
| No repetition | `repetition_penalty=1.3`, `no_repeat_ngram_size=3` |
| Constrained format (JSON/SQL) | `prefix_allowed_tokens_fn` |
| Domain-specific vocabulary | Custom embeddings (Section 2.2) |
| Stop on business rule | `StoppingCriteria` (Section 3.2) |
| Force key terms in output | `force_words_ids` (Section 3.4) |
