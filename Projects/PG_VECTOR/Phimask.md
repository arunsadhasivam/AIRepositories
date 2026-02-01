
before mask:
==============


<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/ae730012-b91b-44d4-a225-7cec76cc689e" />


after mask:
===========


<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/d1c6de3e-28b7-47bc-a802-151c807577a7" />


<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/56321e71-af66-487b-b7ad-34178c3639a1" />


predio analyzer replace PII:
==============================

- presidio_analyzer==2.2.360
- presidio_anonymizer==2.2.360



<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/75cbeb40-5d05-432a-98a5-970a365ff684" />

<img width="3840" height="2400" alt="image" src="https://github.com/user-attachments/assets/128d6314-34bf-4c6d-a8bb-a6d65a6a8037" />



# PII Masking Tools Comparison

## Overview

This document compares three commonly used approaches for PII (Personally Identifiable Information) masking in Python before inserting data into vector databases like PGVector.

---

## Tools Compared

| Feature | Presidio | spaCy | re (Regex) |
|---|---|---|---|
| **Developer** | Microsoft | Explosion AI | Python Built-in |
| **Install** | `pip install presidio_analyzer presidio_anonymizer` | `pip install spacy` | No install needed |
| **Detection Method** | NER + Regex combined | NER (Context-based) | Pattern-based only |
| **Auto PII Detection** | Yes — detects all PII by default | Partial — only NER entities | No — you define every pattern |
| **Maintenance** | No code change needed for new PII types | No code change for NER entities | Code change needed for every new pattern |

---

## PII Detection Capability

| PII Type | Presidio | spaCy | re (Regex) |
|---|---|---|---|
| Person Name | ✅ Auto | ✅ Auto | ❌ Not possible |
| Phone Number | ✅ Auto | ❌ Misses | ✅ Manual pattern |
| Email Address | ✅ Auto | ❌ Misses | ✅ Manual pattern |
| Aadhaar Number | ✅ Auto | ❌ Misses | ✅ Manual pattern |
| PAN Card | ✅ Auto | ❌ Misses | ✅ Manual pattern |
| Date of Birth | ✅ Auto | ✅ Auto | ✅ Manual pattern |
| Location | ✅ Auto | ✅ Auto | ❌ Not possible |
| Organization | ✅ Auto | ✅ Auto | ❌ Not possible |
| SSN | ✅ Auto | ❌ Misses | ✅ Manual pattern |
| Credit Card | ✅ Auto | ❌ Misses | ✅ Manual pattern |

---

## Output Comparison

### Input Text
```
Patient John Doe, Phone: 9876543210, Email: john@gmail.com, Aadhaar: 1234 5678 9012, Located in Mumbai
```

### Presidio Output
```
Patient <PERSON>, Phone: <PHONE_NUMBER>, Email: <EMAIL_ADDRESS>, Aadhaar: <IN_AADHAAR>, Located in <LOCATION>
```

### spaCy + Regex Output
```
Patient <PERSON>, Phone: <PHONE_NUMBER>, Email: <EMAIL>, Aadhaar: <AADHAAR>, Located in <GPE>
```

### Regex Only Output
```
Patient John Doe, Phone: <PHONE_NUMBER>, Email: <EMAIL>, Aadhaar: <AADHAAR>, Located in Mumbai
```
> ❌ Regex misses Person Name and Location — cannot detect context-based PII.

---

## Code Complexity

### Presidio
```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def mask_pii(text: str) -> str:
    results = analyzer.analyze(text=text, language="en")
    if not results:
        return text
    masked_text = anonymizer.anonymize(text=text, analyzer_results=results).text
    return masked_text
```
> ✅ Simple — no manual pattern definition needed.

---

### spaCy + Regex
```python
import re
import spacy

nlp = spacy.load("en_core_web_lg")

def mask_pii(text: str) -> str:
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "DATE", "GPE", "ORG", "LOC"]:
            text = text.replace(ent.text, f"<{ent.label_}>")

    # Manual regex patterns needed
    text = re.sub(r'\b[7-9]\d{9}\b', '<PHONE_NUMBER>', text)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<EMAIL>', text)
    text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', '<AADHAAR>', text)
    text = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '<PAN>', text)

    return text
```
> ⚠️ You need to manually write regex for every pattern-based PII type.

---

### Regex Only
```python
import re

def mask_pii(text: str) -> str:
    text = re.sub(r'\b[7-9]\d{9}\b', '<PHONE_NUMBER>', text)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<EMAIL>', text)
    text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', '<AADHAAR>', text)
    text = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '<PAN>', text)
    return text
```
> ❌ Misses names and locations — not suitable for health documents.

---

## When to Use Which

| Scenario | Best Choice | Why |
|---|---|---|
| Health documents with names, locations, phone numbers | **Presidio** | Detects all PII types automatically |
| Simple use case — only phone, email masking | **Regex** | No install needed, lightweight |
| Budget on dependencies, need name detection | **spaCy + Regex** | Good balance of detection and control |
| SaaS product, multiple PII types, compliance required | **Presidio** | Most complete, least maintenance |
| Already have spaCy installed, presidio install issues | **spaCy + Regex** | Works as fallback |

---

## Installation

### Presidio
```bash
pip install presidio_analyzer presidio_anonymizer spacy
python -m spacy download en_core_web_lg
```

### spaCy + Regex
```bash
pip install spacy
python -m spacy download en_core_web_lg
```

### Regex
```
No installation needed — built into Python
```

---

## Summary

| | Presidio | spaCy + Regex | Regex Only |
|---|---|---|---|
| **Ease of Use** | ✅ Easiest | ⚠️ Medium | ✅ Simple |
| **Detection Coverage** | ✅ Best | ⚠️ Good | ❌ Limited |
| **Maintenance** | ✅ Lowest | ⚠️ Medium | ❌ Highest |
| **Dependencies** | ⚠️ Heavy | ⚠️ Medium | ✅ None |
| **Best For** | Health documents | Fallback option | Simple patterns only |
| **Recommended** | ✅ Yes | Only if Presidio fails | ❌ No for health docs |
