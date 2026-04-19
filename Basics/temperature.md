# Temperature: Deterministic vs Stochastic + Sampling Strategy Decision

---

## 1. Temperature — The Master Dial

**Real example:** Phone autocomplete for `"I am going to the"`

Base probabilities at temp=1.0:
```
"store" → 40%
"park"  → 30%
"gym"   → 20%
"moon"  →  8%
"xyz"   →  2%
```

---

### How Temperature Shifts the Distribution

```
temp → 0 (fully deterministic):
  "store" → 99.9%   ← always wins, same as greedy
  "park"  →  0.1%
  "gym"   →  0.0%
  "moon"  →  0.0%

temp = 0.7 (focused stochastic):
  "store" → 75%
  "park"  → 20%
  "gym"   →  5%
  "moon"  →  0%

temp = 1.0 (default, no change):
  "store" → 40%
  "park"  → 30%
  "gym"   → 20%
  "moon"  →  8%
  "xyz"   →  2%

temp = 1.5 (creative):
  "store" → 28%
  "park"  → 26%
  "gym"   → 22%
  "moon"  → 15%
  "xyz"   →  9%

temp → ∞ (fully random):
  "store" → 20%   ← all words equally likely
  "park"  → 20%
  "gym"   → 20%
  "moon"  → 20%
  "xyz"   → 20%
```

---

### Temperature Summary Table

| Temperature | Behavior | Type |
|---|---|---|
| → 0 | Always picks top word | Fully deterministic |
| 0.1 – 0.7 | Mostly top words, rare surprises | Near deterministic |
| 1.0 | Default model distribution | Balanced |
| 1.2 – 1.5 | More random, creative | Stochastic |
| → ∞ | All words equally likely | Fully random |

---

### Code

```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    temperature=0.7,   # < 1 focused, 1.0 default, > 1 random
    max_length=50
)
```

---

## 2. How Multinomial vs Top-K vs Top-P is Decided

Temperature controls **how sharp or flat** the distribution is.  
The sampling strategy controls **which words you even consider** before picking.

---

### Decision Flow

```
do_sample=False?
    → Greedy or Beam Search (deterministic, temperature ignored)

do_sample=True?
    → Apply temperature first (reshape distribution)
    → Then apply sampling strategy:

        top_k provided?     → Top-K Sampling
        top_p provided?     → Top-P Sampling
        both provided?      → Top-P applied after Top-K filter
        neither provided?   → Pure Multinomial (full vocab)
```

---

### 2.1 When Multinomial is Used

**Condition:** `do_sample=True` + no `top_k` + no `top_p`

**What happens:** Sample from entire vocabulary distribution.  
**When to choose:** Maximum creativity, experimental use.  
**Risk:** Low probability words like "moon", "xyz" can still win.

```python
# Pure multinomial — no filtering at all
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    temperature=0.9,
    max_length=50
    # no top_k, no top_p
)
```

```
Distribution after temp=0.9:
  "store" → 42%  ← can be picked
  "park"  → 31%  ← can be picked
  "gym"   → 19%  ← can be picked
  "moon"  →  6%  ← can be picked
  "xyz"   →  2%  ← can be picked  ← RISK
```

---

### 2.2 When Top-K is Used

**Condition:** `do_sample=True` + `top_k=N` provided

**What happens:** Keep only top-N words, cut the rest, sample from those N.  
**When to choose:** You want creativity but want to eliminate garbage words.  
**Fixed width** — always exactly K words regardless of distribution shape.

```python
# Top-K sampling
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    top_k=3,           # consider only top 3 words
    temperature=0.8,
    max_length=50
)
```

```
After temp=0.8, apply top_k=3:
  "store" → 42%  ← keep
  "park"  → 31%  ← keep
  "gym"   → 19%  ← keep
  "moon"  →  6%  ← CUT
  "xyz"   →  2%  ← CUT

Re-normalize {store, park, gym} → sum to 100%
  "store" → 45%
  "park"  → 34%
  "gym"   → 21%

Sample from these 3 only.
```

**Problem with Top-K:**
```
Scenario: Model is very confident
  "store" → 92%   ← top-3 still forced
  "park"  →  5%
  "gym"   →  2%   ← included even though almost 0%
  "moon"  →  1%   ← CUT  (but gym at 2% kept — makes no sense)
```
K is fixed even when it should be smaller or larger.

---

### 2.3 When Top-P is Used

**Condition:** `do_sample=True` + `top_p=P` provided

**What happens:** Keep adding words (sorted high→low) until cumulative probability hits P. Sample from that dynamic group.  
**When to choose:** Best general purpose. Adapts automatically to distribution shape.  
**Dynamic width** — nucleus shrinks when model is confident, expands when uncertain.

```python
# Top-P (nucleus) sampling
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    top_p=0.9,         # include words covering 90% probability mass
    temperature=0.8,
    max_length=50
)
```

```
After temp=0.8, apply top_p=0.90:

Sorted cumulative:
  "store" → 42% | cumulative: 42% ← include
  "park"  → 31% | cumulative: 73% ← include
  "gym"   → 19% | cumulative: 92% ← include (crossed 90%, stop)
  "moon"  →  6% | cumulative: 98% ← EXCLUDED
  "xyz"   →  2% | cumulative:100% ← EXCLUDED

Sample from {store, park, gym}

--- Model very confident scenario ---
  "store" → 92% | cumulative: 92% ← include (already crossed 90%)
  "park"  →  5% | cumulative: 97% ← EXCLUDED

Nucleus auto-shrinks to {store} only — no garbage included!
```

---

### 2.4 When Both Top-K and Top-P are Used

**Condition:** `do_sample=True` + both `top_k` and `top_p` provided

**What happens:** Top-K filter applied first → then Top-P filter on remaining K words.  
**When to choose:** Extra safety — double filter to eliminate both fixed garbage and low-mass words.

```python
# Both top_k and top_p combined
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    top_k=50,          # first cut: keep top 50 words
    top_p=0.9,         # second cut: from those 50, keep nucleus covering 90%
    temperature=0.7,
    max_length=50
)
```

```
Step 1 — Top-K=50 filter:
  Keep top 50 words, cut remaining 30,000+

Step 2 — Top-P=0.9 filter on those 50:
  Keep adding from top-50 until cumulative hits 90%
  Might end up with only 5-10 words

Sample from final filtered set.
```

---

## 3. Strategy Selection Summary

| Condition in code | Strategy used | Distribution width |
|---|---|---|
| `do_sample=False` | Greedy or Beam | N/A (no sampling) |
| `do_sample=True` only | Multinomial | Full vocab (~30,000 words) |
| `do_sample=True` + `top_k=50` | Top-K | Fixed 50 words |
| `do_sample=True` + `top_p=0.9` | Top-P | Dynamic (auto-adapts) |
| `do_sample=True` + `top_k=50` + `top_p=0.9` | Top-K then Top-P | Fixed first, then dynamic |

---

## 4. Temperature + Strategy Combined Decision

```
What output do you need?
        |
        ├─ Same output every time?
        │       → do_sample=False
        │       → num_beams=1 (greedy) or num_beams=4 (beam search)
        │
        └─ Different / creative output?
                → do_sample=True
                → Set temperature first:
                │     focused output   → temperature=0.7
                │     balanced         → temperature=1.0
                │     creative         → temperature=1.2+
                │
                └─ Then pick filter:
                      max creativity, no filter  → (nothing, pure multinomial)
                      eliminate garbage, fixed   → top_k=50
                      eliminate garbage, adaptive→ top_p=0.9  ← recommended
                      extra safe                 → top_k=50 + top_p=0.9
```

---

## 5. Recommended Combinations

```python
# 1. Factual / deterministic
model.generate(input_ids=ids, num_beams=4, early_stopping=True)

# 2. Balanced creative (most common default)
model.generate(input_ids=ids, do_sample=True, top_k=50, top_p=0.9, temperature=0.7)

# 3. Maximum creativity
model.generate(input_ids=ids, do_sample=True, temperature=1.2, top_p=0.95)

# 4. No repetition (add to any above)
model.generate(input_ids=ids, repetition_penalty=1.3, no_repeat_ngram_size=3)
```
