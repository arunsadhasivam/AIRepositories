# Text Generation Strategies: Deterministic vs Stochastic

---

## 1. The Core Idea (Layman Terms)

**Real example everyone knows: Phone keyboard autocomplete**

When you type `"I am going to the"` — your phone suggests the next word.

The model internally ranks every possible next word with a probability:

```
"store"  → 40%
"park"   → 30%
"gym"    → 20%
"moon"   →  8%
"xyz"    →  2%
```

**How you pick from this ranked list = your strategy.**

- **Deterministic** = Always pick same word for same input. Predictable. No surprise.
- **Stochastic** = Pick randomly based on weights. Different result each time. Creative.

---

## 2. Deterministic Strategies (Same output every run)

---

### 2.1 Greedy Search

**Layman:** Phone always suggests the #1 word. Always "store". Every single time.

**How it works:**
- At every step → pick the single highest probability token
- No alternatives explored

```
Input:  "I am going to the"
Step 1: pick "store" (40%) ← always highest
Step 2: pick "to"    (55%) ← always highest
Step 3: pick "buy"   (60%) ← always highest

Output: "I am going to the store to buy"
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    max_length=20
    # default = greedy, no other params needed
)
```

**Good for:** Simple factual tasks where one answer is clearly right.

**Problem:** Can get stuck. Like autocomplete always suggesting "store" even when you are near a park.

---

### 2.2 Beam Search

**Layman:** Phone keyboard does not just suggest one word — it shows **3 full sentence options** at the top. You pick the best complete sentence, not just the best next word.

**How it works:**
- Keep top-N (beams) full sequences alive at every step
- Expand all of them → score all next words
- Keep only top-N again
- At end → return sequence with best total score

```
num_beams = 2

Step 1 — expand from start:
  Path A: "...the store" (0.40)
  Path B: "...the park"  (0.30)

Step 2 — expand both paths:
  Path A → "...the store to"    (0.40 × 0.55 = 0.22)
  Path A → "...the store and"   (0.40 × 0.20 = 0.08)
  Path B → "...the park to"     (0.30 × 0.55 = 0.17)
  Path B → "...the park and"    (0.30 × 0.20 = 0.06)

Keep top 2: Path A (0.22), Path B (0.17)

Final winner: "I am going to the store to buy groceries"

```

Backtracking (keep all):        Beam Search (keep top-2 only):

       root                            root
      /    \                          /    \
   "store" "park"                 "store" "park"   ← keep top-2
   /   \    /  \                  /   \    /  \
 "to" "and" "to" "and"         "to" "and" "to" "and"
                                 ↑ score  ↑ score
                               keep top-2 again, prune rest



```


Key difference from pure backtracking:
=======================================

Backtracking = explores ALL paths, prunes on constraint violation
Beam Search = explores top-N paths only, prunes on score (probability)
So beam search is bounded backtracking — same tree traversal idea but with a width limit (num_beams) instead of pruning on hard constraints.

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

**Good for:** Translation, summarization — needs globally coherent sentence.

**Problem:** Still deterministic. Tends to produce safe, boring output. 4x slower than greedy.

---

## 3. Stochastic Strategies (Different output each run)

---

### 3.1 Multinomial Sampling (Pure Sampling)

**Layman:** Spin a weighted roulette wheel across ALL words in dictionary. "store" has 40% slice but "moon" (8%) can still win. Anything is possible.

**How it works:**
- Sample randomly from the full probability distribution
- Every word has a chance proportional to its score
- Most unpredictable

```
"store"  → 40% chance of winning spin
"park"   → 30% chance
"gym"    → 20% chance
"moon"   →  8% chance  ← can still win!
"xyz"    →  2% chance  ← can still win!

Run 1 output: "I am going to the park"
Run 2 output: "I am going to the store"
Run 3 output: "I am going to the moon"   ← valid but weird
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,     # enable stochastic
    max_length=50
    # no top_k or top_p = pure multinomial over full vocab
)
```

**Good for:** Maximum creativity. Story writing.

**Problem:** "moon" and "xyz" can win. Output can go off-rails.

---

### 3.2 Top-K Sampling

**Layman:** Phone autocomplete shows only **top 3 suggestions**. You randomly pick one of those 3. "xyz" is never even shown to you.

**How it works:**
- Keep only top-K highest probability words
- Cut off everything else
- Re-normalize remaining K words to sum to 100%
- Sample randomly from those K only

```
top_k = 3

Before:                    After cut + re-normalize:
"store"  → 40%             "store"  → 44%  (40/90)
"park"   → 30%             "park"   → 33%  (30/90)
"gym"    → 20%             "gym"    → 22%  (20/90)
"moon"   →  8%  ← CUT
"xyz"    →  2%  ← CUT

Sample from: {store, park, gym} only
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    top_k=50,          # consider only top 50 words
    max_length=50
)
```

**Good for:** Balanced creativity. Most commonly used default.

**Problem:** K is fixed. When distribution is very flat (many equally likely words), 50 might still be too wide or too narrow.

---

### 3.3 Top-P Sampling (Nucleus Sampling)

**Layman:** Instead of fixed top-3 — keep adding words to your shortlist until the **total probability hits 90%**. Some moments only 2 words needed. Some moments 10 words needed. **Adapts automatically.**

**How it works:**
- Sort words high → low probability
- Keep adding until cumulative probability crosses threshold P
- Sample randomly from that dynamic group

```
top_p = 0.90

Sorted:
"store"  → 40% | cumulative: 40% ← include
"park"   → 30% | cumulative: 70% ← include
"gym"    → 20% | cumulative: 90% ← include (hit 90%, stop here)
"moon"   →  8% | cumulative: 98% ← EXCLUDED
"xyz"    →  2% | cumulative:100% ← EXCLUDED

Sample from: {store, park, gym}

--- Different moment, model is very confident ---

"store"  → 92% | cumulative: 92% ← include (already crossed 90%)
"park"   →  5% | cumulative: 97% ← EXCLUDED

Sample from: {store} only — nucleus automatically shrinks!
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    top_p=0.9,         # nucleus = words covering 90% probability mass
    max_length=50
)
```

**Good for:** Best general-purpose stochastic strategy. Self-adapts.

**Advantage over top-k:** When model is very confident → nucleus shrinks to 1 word automatically. When model is uncertain → nucleus expands. Top-K cannot do this.

---

### 3.4 Temperature Scaling

**Layman:** Temperature is the **confidence dial** on your phone autocomplete.
- Turn it down (temp < 1) → phone becomes very confident, always picks top word
- Turn it up (temp > 1) → phone becomes adventurous, picks surprising words more often
- Keep at 1 → default behavior, no change

**How it works:**
- Divide all raw scores (logits) by temperature before converting to probabilities
- `temp < 1` → sharpens distribution (top word gets even more dominant)
- `temp > 1` → flattens distribution (low probability words get a bigger chance)

```
Raw scores (logits): [store=3.0, park=1.5, gym=0.5, moon=0.3]

temp = 0.5 (confident):
  Divided: [6.0, 3.0, 1.0, 0.6]
  After softmax: store=85%, park=12%, gym=2%, moon=1%
  → Model becomes very sure about "store"

temp = 1.0 (default):
  Divided: [3.0, 1.5, 0.5, 0.3]
  After softmax: store=60%, park=25%, gym=10%, moon=5%
  → Normal distribution

temp = 2.0 (adventurous):
  Divided: [1.5, 0.75, 0.25, 0.15]
  After softmax: store=45%, park=30%, gym=15%, moon=10%
  → "moon" gets a much bigger slice now
```

**Code:**
```python
output = model.generate(
    input_ids=inputs.input_ids,
    do_sample=True,
    temperature=0.7,   # < 1 focused, > 1 random, 1.0 = default
    top_p=0.9,         # combine temperature with top_p for best results
    max_length=50
)
```

**Note:** Temperature is not a standalone strategy — it is a **modifier** applied before top-k or top-p sampling.

---

## 4. All Strategies Side by Side

| Strategy | Type | Phone Autocomplete Analogy | Same output each run? | Best for |
|---|---|---|---|---|
| Greedy | Deterministic | Always pick #1 suggestion | Yes | Simple factual tasks |
| Beam Search | Deterministic | Show 3 full sentence options, pick best complete one | Yes | Translation, summarization |
| Multinomial | Stochastic | Spin full roulette across all words | No | Maximum creativity |
| Top-K | Stochastic | Show only top-3 suggestions, pick randomly from those | No | Balanced creativity |
| Top-P | Stochastic | Show suggestions until 90% confidence covered, pick randomly | No | Best general purpose |
| Temperature | Modifier | Confidence dial — how bold vs safe the suggestions are | No | Combined with top-k/top-p |

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
# Factual / Translation (deterministic - safe)
model.generate(input_ids=ids, num_beams=4, early_stopping=True)

# Balanced creative (stochastic - most common default)
model.generate(input_ids=ids, do_sample=True, top_k=50, top_p=0.9, temperature=0.7)

# Maximum creativity (stochastic - adventurous)
model.generate(input_ids=ids, do_sample=True, temperature=1.2, top_p=0.95)

# No repetition (add to any strategy above)
model.generate(input_ids=ids, repetition_penalty=1.3, no_repeat_ngram_size=3)
```

---

## 7. Decision Flow

```
Need same output every time?
        ↓ Yes                      ↓ No (do_sample=True)
   Simple task?               Need max creativity?
   ↓ Yes     ↓ No             ↓ Yes            ↓ No
 Greedy   Beam Search     Multinomial        Top-P (0.9)
                          + high temp        + Top-K (50)
                                             + temp (0.7)
```
