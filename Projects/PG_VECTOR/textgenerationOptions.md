# Text Generation Strategies: Deterministic vs Stochastic

---

## 1. The Core Idea (Layman Terms)

Imagine you are at a **restaurant choosing a dish**:

- **Deterministic** = You always order the same dish — the one you like most. No surprise. Same input, same output, every time.
- **Stochastic** = You roll a dice among top dishes. Different choice each time. Surprise possible.

In transformers, after every word generated, the model produces a **probability list** for every word in vocabulary:

```
"Bonjour" → 60%
"Salut"   → 25%
"Allo"    → 10%
"Ciao"    → 5%
```

**How you pick from this list = your strategy.**

---

## 2. Deterministic Strategies (Same output every run)

---

### 2.1 Greedy Search

**Layman:** Always pick the dish with highest rating. No exploration. Fast. Predictable.

**How it works:**
- At every step → pick the single highest probability token
- No alternatives considered
- Fastest but can get stuck in repetitive loops

```
Step 1: "Bonjour" (60%) ← always pick this
Step 2: "comment" (55%) ← always pick this
Step 3: "allez"   (70%) ← always pick this
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    max_length=50
    # no other params = greedy by default
)
```

**When to use:** Simple factual tasks. Translation where one answer is clearly correct.

**Problem:** Misses better overall sequences. Like always picking most popular dish — might miss a better meal combo.

---

### 2.2 Beam Search

**Layman:** Instead of ordering one dish — you ask the waiter to bring top 3 meals. You taste all 3 combos (starter + main + dessert) and pick the best full meal experience.

**How it works:**
- Keep top-N (beam width) sequences alive at every step
- Expand each sequence → score all next tokens
- Keep only top-N again
- At end → pick sequence with best overall score

```
Beam=2, Step 1:
  Path A: "Bonjour" (0.60)
  Path B: "Salut"   (0.25)

Step 2:
  Path A → "Bonjour comment" (0.60 × 0.55 = 0.33)
  Path A → "Bonjour ça"      (0.60 × 0.20 = 0.12)
  Path B → "Salut comment"   (0.25 × 0.55 = 0.14)
  Path B → "Salut ça"        (0.25 × 0.20 = 0.05)

Keep top 2: Path A (0.33), Path B-variant (0.14)
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    num_beams=4,           # explore 4 paths simultaneously
    early_stopping=True,   # stop when best beam hits <eos>
    length_penalty=1.0,    # 1.0=neutral, >1=favor longer, <1=favor shorter
    max_length=50
)
```

**When to use:** Translation, summarization — tasks needing globally coherent output.

**Problem:** Still deterministic. Tends to produce safe, generic output. Computationally heavier (4x vs greedy).

---

## 3. Stochastic Strategies (Different output each run)

---

### 3.1 Multinomial Sampling (Pure Sampling)

**Layman:** You spin a weighted roulette wheel. Higher probability = bigger slice. But any slice can win. Bonjour has 60% slice but Salut (25%) can still win.

**How it works:**
- Sample token randomly according to full probability distribution
- Every token has a chance proportional to its probability
- Most unpredictable — truly random

```
"Bonjour" → 60% chance of being picked
"Salut"   → 25% chance
"Allo"    → 10% chance
"Ciao"    → 5%  chance
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,        # enable stochastic sampling
    max_length=50
    # no top_k or top_p = full multinomial over entire vocab
)
```

**When to use:** Creative writing where any reasonable word is fine.

**Problem:** Can pick very low probability (weird) tokens. Output can go off-rails.

---

### 3.2 Top-K Sampling

**Layman:** Waiter brings only the **top 5 dishes** from the menu. You randomly pick from those 5 only. Bad dishes are not even on your table.

**How it works:**
- Keep only top-K highest probability tokens
- Re-normalize their probabilities to sum to 100%
- Sample randomly from those K tokens only
- Cuts off the long tail of low-probability tokens

```
Full vocab (before top-k=3):
  "Bonjour" → 60%
  "Salut"   → 25%
  "Allo"    → 10%
  "Ciao"    → 4%    ← cut
  "Hola"    → 1%    ← cut
  ... 30,000 more   ← cut

After top-k=3, re-normalize:
  "Bonjour" → 63%  (60/95)
  "Salut"   → 26%  (25/95)
  "Allo"    → 11%  (10/95)
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    top_k=50,         # consider only top 50 tokens
    max_length=50
)
```

**When to use:** Balanced creativity. Most commonly used default setting.

**Problem:** K is fixed regardless of distribution shape. When distribution is flat (many equally likely words), K=50 might still be too narrow or too wide.

---

### 3.3 Top-P Sampling (Nucleus Sampling)

**Layman:** Instead of fixed top-5 dishes — you keep adding dishes to the table until the total customer satisfaction rating hits 90%. Some days 2 dishes cover 90%. Some days you need 10 dishes. **Dynamic** selection.

**How it works:**
- Sort tokens by probability high → low
- Keep adding tokens until their cumulative probability hits threshold P
- Sample randomly from that dynamic nucleus
- Nucleus size adapts to distribution shape

```
top_p = 0.90

Sorted tokens:
  "Bonjour" → 60%  | cumulative: 60%  ← include
  "Salut"   → 25%  | cumulative: 85%  ← include
  "Allo"    → 10%  | cumulative: 95%  ← include (crossed 90%, stop here)
  "Ciao"    → 4%   | cumulative: 99%  ← excluded
  "Hola"    → 1%   | cumulative: 100% ← excluded

Sample from: {Bonjour, Salut, Allo}
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    top_p=0.9,        # nucleus = tokens covering 90% probability mass
    max_length=50
)
```

**When to use:** Best general-purpose stochastic strategy. Adapts automatically.

**Advantage over top-k:** When model is very confident (one token = 95% prob), nucleus = 1 token. When model is uncertain (flat distribution), nucleus expands automatically.

---

### 3.4 Temperature Scaling

**Layman:** Temperature is like **spice level** on the menu.
- Low spice (temp < 1) = safe, predictable flavors, everyone agrees
- High spice (temp > 1) = adventurous, polarizing, unexpected combos

**How it works:**
- Divide all logits (raw scores) by temperature before softmax
- `temp < 1` → sharpens distribution (confident picks)
- `temp > 1` → flattens distribution (more random picks)
- `temp = 1` → no change (default)

```
Original logits: [3.0, 1.5, 0.5]

temp=0.5 (low) → [6.0, 3.0, 1.0] → after softmax → [0.84, 0.14, 0.02]  sharper
temp=1.0       → [3.0, 1.5, 0.5] → after softmax → [0.67, 0.28, 0.05]  default
temp=2.0 (high)→ [1.5, 0.75,0.25]→ after softmax → [0.50, 0.35, 0.15]  flatter
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    temperature=0.7,   # < 1 = more focused, > 1 = more random
    top_p=0.9,         # combine with top_p for best results
    max_length=50
)
```

**Note:** Temperature is not a standalone strategy — it is applied **before** top-k or top-p sampling.

---

## 4. All Strategies Side by Side

| Strategy | Type | Restaurant Analogy | Same output each run? | Best for |
|---|---|---|---|---|
| Greedy | Deterministic | Always order #1 rated dish | Yes | Simple factual tasks |
| Beam Search | Deterministic | Try top-N full meal combos, pick best | Yes | Translation, summarization |
| Multinomial | Stochastic | Spin full roulette wheel | No | Maximum creativity |
| Top-K | Stochastic | Pick randomly from top-5 dishes only | No | Balanced creativity |
| Top-P | Stochastic | Pick randomly until 90% satisfaction covered | No | Best general purpose |
| Temperature | Modifier | Spice level dial (applied before sampling) | No | Combined with top-k/top-p |

---

## 5. Deterministic vs Stochastic Summary

| Aspect | Deterministic | Stochastic |
|---|---|---|
| Same input → same output? | Always | No — different each run |
| Strategies | Greedy, Beam Search | Multinomial, Top-K, Top-P |
| Trigger in code | `do_sample=False` (default) | `do_sample=True` |
| Predictable? | Yes | No |
| Creative? | No | Yes |
| Safe from weird outputs? | Yes | Depends on K, P, temperature |

---

## 6. Recommended Combinations

```python
# Factual / Translation (deterministic)
model.generate(input_ids=ids, num_beams=4, early_stopping=True)

# Balanced creative (stochastic - most common)
model.generate(input_ids=ids, do_sample=True, top_k=50, top_p=0.9, temperature=0.7)

# Maximum creativity (stochastic - adventurous)
model.generate(input_ids=ids, do_sample=True, temperature=1.2, top_p=0.95)

# No repetition (add to any strategy)
model.generate(input_ids=ids, repetition_penalty=1.3, no_repeat_ngram_size=3)
```

---

## 7. Decision Flow

```
Need same output every time?
        ↓ Yes                    ↓ No
   Simple task?             Need creativity?
   ↓ Yes   ↓ No             ↓ Yes         ↓ No
 Greedy  Beam Search    Top-P (0.9)    Top-K (50)
                        + temp (0.7)
```
