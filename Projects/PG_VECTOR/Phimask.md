
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
