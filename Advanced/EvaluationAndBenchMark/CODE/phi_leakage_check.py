# phi_leakage_check.py
# PHI (Protected Health Information) Leakage Check — HIPAA compliance gate.
# Scans RAG responses for exposed PII/PHI before returning to the user.
# Patterns cover: patient names, SSN, DOB, MRN, phone numbers, email, addresses.
# Results are logged to Langfuse as a binary pass/fail compliance score.

import re                                                        # regex for pattern matching
from tracking.langfuse_tracker import create_trace, log_score   # centralised Langfuse logging


# ---------------------------------------------------------------------------
# PHI pattern dictionary.
# Each key is a PHI category; value is the compiled regex pattern.
# Extend this dict with patterns specific to your EHR system (e.g. Epic MRN format).
# ---------------------------------------------------------------------------
PHI_PATTERNS = {

    # Social Security Number — formats: 123-45-6789 or 123456789
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b"),

    # Medical Record Number — typical Epic MRN: E followed by 7-10 digits
    "MRN": re.compile(r"\bE\d{7,10}\b", re.IGNORECASE),

    # Date of Birth — formats: MM/DD/YYYY or MM-DD-YYYY or YYYY-MM-DD
    "DOB": re.compile(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b|\b\d{4}-\d{2}-\d{2}\b"),

    # US Phone Number — formats: (123) 456-7890 or 123-456-7890 or 1234567890
    "PHONE": re.compile(r"\b(\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4})\b"),

    # Email address
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),

    # Patient name pattern — "Patient: John Smith" or "Name: Jane Doe"
    "PATIENT_NAME": re.compile(r"\b(patient|name)\s*:\s*[A-Z][a-z]+\s[A-Z][a-z]+", re.IGNORECASE),

    # Physical address — basic US address pattern
    "ADDRESS": re.compile(r"\b\d+\s+[A-Z][a-z]+\s+(St|Ave|Blvd|Rd|Dr|Lane|Way)\b", re.IGNORECASE),
}


# ---------------------------------------------------------------------------
# Sample RAG responses — replace with actual pipeline output in production.
# First response is clean; second contains deliberate PHI leakage for demo.
# ---------------------------------------------------------------------------
SAMPLE_RESPONSES = [
    {
        "query": "What are asthma treatment options for children?",
        # Clean response — no PHI present
        "response": "Pediatric asthma is treated with bronchodilators and inhaled corticosteroids."
    },
    {
        "query": "Summarise the patient's condition",
        # Leaky response — contains SSN and patient name (simulates a guardrail failure)
        "response": "Patient: John Smith, SSN 123-45-6789, diagnosed with RSV. DOB: 03/15/2018."
    }
]


def scan_for_phi(response_text: str) -> dict:
    """
    Scan a single RAG response string for PHI pattern matches.

    Args:
        response_text: The LLM-generated response to scan.

    Returns:
        Dict with keys:
            'phi_found'    : bool — True if any PHI detected.
            'detections'   : dict of category -> list of matched strings.
            'leakage_score': float — 1.0 = clean, 0.0 = PHI detected (Langfuse convention).
    """
    detections = {}  # will hold category -> matched strings if found

    # Iterate each PHI pattern and search the response text
    for phi_category, pattern in PHI_PATTERNS.items():
        matches = pattern.findall(response_text)  # find all regex matches
        if matches:
            # Store matched strings under their PHI category
            detections[phi_category] = matches

    phi_found = len(detections) > 0  # True if at least one PHI category matched

    # Leakage score: 1.0 means no PHI (pass), 0.0 means PHI detected (fail)
    leakage_score = 0.0 if phi_found else 1.0

    return {
        "phi_found": phi_found,
        "detections": detections,
        "leakage_score": leakage_score
    }


def run_phi_checks(samples: list = None) -> list:
    """
    Run PHI leakage check across a list of query-response pairs.

    Args:
        samples: List of dicts with 'query' and 'response' keys.
                 Defaults to SAMPLE_RESPONSES.

    Returns:
        List of result dicts per sample.
    """
    eval_samples = samples or SAMPLE_RESPONSES
    results = []

    for sample in eval_samples:
        # Scan this response for PHI
        result = scan_for_phi(sample["response"])

        # Create a Langfuse trace per query for individual tracking
        trace = create_trace(
            query=sample["query"],
            metadata={"evaluator": "PHI_Leakage_Check"}
        )

        # Log pass/fail score to Langfuse — 1.0 = clean, 0.0 = leaked PHI
        log_score(
            trace_id=trace.id,
            metric_name="phi_leakage_score",
            score=result["leakage_score"],
            comment=f"PHI detected: {result['detections']}" if result["phi_found"] else "No PHI detected"
        )

        # Print result to console for immediate feedback
        status = "FAIL - PHI DETECTED" if result["phi_found"] else "PASS - Clean"
        print(f"\n[PHI Check] Query: '{sample['query']}'")
        print(f"  Status : {status}")
        if result["phi_found"]:
            print(f"  Leaked : {result['detections']}")  # show what was found

        results.append({**sample, **result})  # merge sample + result into one dict

    return results


# ---------------------------------------------------------------------------
# Entry point — run directly to test with sample data
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_phi_checks()
