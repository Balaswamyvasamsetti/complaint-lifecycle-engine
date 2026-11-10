# ai_engine.py — Amazon Bedrock (Claude) powered complaint intelligence
# Handles: classification, sentiment analysis, priority prediction, resolution suggestion

import json
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
REGION   = os.getenv("AWS_REGION", "us-east-1")

# ---------------------------------------------------------------------------
# Bedrock client (lazy init — safe to import without credentials)
# ---------------------------------------------------------------------------

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=REGION)
    return _client


def _invoke(prompt: str, max_tokens: int = 512) -> str:
    if not os.getenv("AWS_ACCESS_KEY_ID"):
        return _fallback_response(prompt)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    })
    try:
        response = _get_client().invoke_model(
            modelId=MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"].strip()
    except (NoCredentialsError, ClientError, Exception):
        return _fallback_response(prompt)


def _fallback_response(prompt: str) -> str:
    """
    Rule-based fallback when Bedrock credentials are not configured.
    Keeps the system fully functional without AWS access.
    """
    p = prompt.lower()
    if "classify" in p or "category" in p:
        if any(w in p for w in ["safety", "fire", "burn", "explode", "hazard"]):
            return json.dumps({"category": "Product Safety", "category_id": "CAT-04", "confidence": 0.95})
        if any(w in p for w in ["fraud", "unauthorized", "charge"]):
            return json.dumps({"category": "Fraud / Unauthorized", "category_id": "CAT-09", "confidence": 0.91})
        if any(w in p for w in ["refund", "return", "money back"]):
            return json.dumps({"category": "Refund / Return", "category_id": "CAT-06", "confidence": 0.88})
        if any(w in p for w in ["delivery", "shipping", "late", "not arrived"]):
            return json.dumps({"category": "Delivery / Logistics", "category_id": "CAT-03", "confidence": 0.85})
        if any(w in p for w in ["broken", "defect", "not working", "damaged"]):
            return json.dumps({"category": "Product Defect", "category_id": "CAT-02", "confidence": 0.87})
        if any(w in p for w in ["billing", "invoice", "payment", "charged"]):
            return json.dumps({"category": "Billing & Payment", "category_id": "CAT-01", "confidence": 0.84})
        if any(w in p for w in ["missing", "not received", "lost"]):
            return json.dumps({"category": "Missing Order", "category_id": "CAT-07", "confidence": 0.83})
        if any(w in p for w in ["app", "website", "login", "technical", "error"]):
            return json.dumps({"category": "Technical / App Issue", "category_id": "CAT-08", "confidence": 0.82})
        return json.dumps({"category": "General Enquiry", "category_id": "CAT-10", "confidence": 0.70})

    if "sentiment" in p:
        if any(w in p for w in ["angry", "furious", "terrible", "worst", "unacceptable", "disgusting"]):
            return json.dumps({"sentiment": "Negative", "score": -0.9})
        if any(w in p for w in ["unhappy", "disappointed", "frustrated", "bad", "poor"]):
            return json.dumps({"sentiment": "Negative", "score": -0.6})
        if any(w in p for w in ["great", "excellent", "happy", "satisfied", "good", "thank"]):
            return json.dumps({"sentiment": "Positive", "score": 0.8})
        return json.dumps({"sentiment": "Neutral", "score": 0.0})

    if "priority" in p:
        if any(w in p for w in ["safety", "fraud", "vulnerable", "critical"]):
            return json.dumps({"priority": "CRITICAL", "rule": "PR-01", "reason": "Safety/fraud/vulnerable trigger"})
        if any(w in p for w in ["urgent", "escalate", "high value"]):
            return json.dumps({"priority": "HIGH", "rule": "PR-02", "reason": "High urgency detected"})
        return json.dumps({"priority": "MEDIUM", "rule": "PR-03", "reason": "Standard complaint"})

    if "summar" in p or "resolution" in p:
        return "Customer reported an issue. Recommend reviewing order history and contacting the customer within the SLA window."

    return "Unable to process request."

# ---------------------------------------------------------------------------
# Public AI functions
# ---------------------------------------------------------------------------

def classify_complaint(text: str, order_value: float = 0.0) -> dict:
    """
    Classify complaint text into a category using Claude on Amazon Bedrock.
    Returns: {category, category_id, confidence}
    """
    prompt = """You are a complaint classification engine for a customer service platform.

Classify the following complaint into exactly ONE of these categories:
- CAT-01: Billing & Payment
- CAT-02: Product Defect
- CAT-03: Delivery / Logistics
- CAT-04: Product Safety
- CAT-05: Customer Service
- CAT-06: Refund / Return
- CAT-07: Missing Order
- CAT-08: Technical / App Issue
- CAT-09: Fraud / Unauthorized
- CAT-10: General Enquiry

Complaint: "%s"
Order value: GBP %.2f

Respond ONLY with valid JSON in this exact format:
{"category": "<name>", "category_id": "<CAT-NN>", "confidence": <0.0-1.0>}""" % (text, order_value)

    raw = _invoke(prompt, max_tokens=128)
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"category": "General Enquiry", "category_id": "CAT-10", "confidence": 0.5}


def analyse_sentiment(text: str) -> dict:
    """
    Analyse sentiment of complaint text using Claude on Amazon Bedrock.
    Returns: {sentiment, score}
    """
    prompt = """Analyse the sentiment of this customer complaint.

Complaint: "%s"

Respond ONLY with valid JSON:
{"sentiment": "Positive" | "Neutral" | "Negative", "score": <-1.0 to 1.0>}""" % text

    raw = _invoke(prompt, max_tokens=64)
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"sentiment": "Neutral", "score": 0.0}


def predict_priority(text: str, is_safety: bool, is_vulnerable: bool,
                     order_value: float, recurrence: int, category_id: str) -> dict:
    """
    Predict complaint priority using Claude + business rules on Amazon Bedrock.
    Returns: {priority, rule, reason}
    """
    prompt = """You are a complaint priority engine. Apply these rules strictly:
- CRITICAL (PR-01): safety issue OR fraud (CAT-09) OR vulnerable customer
- HIGH     (PR-02): negative sentiment AND order_value > 500 OR recurrence >= 3
- MEDIUM   (PR-03): negative sentiment OR order_value 100-500
- LOW      (PR-04): neutral/positive sentiment AND order_value < 100

Complaint: "%s"
is_safety_issue: %s
is_vulnerable_customer: %s
order_value: GBP %.2f
recurrence_count: %d
category_id: %s

Respond ONLY with valid JSON:
{"priority": "CRITICAL"|"HIGH"|"MEDIUM"|"LOW", "rule": "PR-0N", "reason": "<brief reason>"}""" % (
        text, is_safety, is_vulnerable, order_value, recurrence, category_id
    )

    raw = _invoke(prompt, max_tokens=128)
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"priority": "MEDIUM", "rule": "PR-03", "reason": "Default fallback"}


def suggest_resolution(complaint_text: str, category: str, priority: str, history: list = None) -> str:
    """
    Suggest a resolution action using Claude on Amazon Bedrock.
    Returns a plain-text resolution recommendation.
    """
    history_str = ""
    if history:
        history_str = "\nPrevious messages:\n" + "\n".join(
            "- [%s] %s" % (m.get("sender_type",""), m.get("message_text","")) for m in history[-5:]
        )

    prompt = """You are a customer service resolution assistant.

Complaint: "%s"
Category: %s
Priority: %s%s

Suggest a concise resolution action (2-3 sentences). Be specific and actionable.""" % (
        complaint_text, category, priority, history_str
    )

    return _invoke(prompt, max_tokens=256)


def generate_summary(complaint: dict, messages: list = None) -> str:
    """
    Generate a brief case summary for agent handoff using Claude on Amazon Bedrock.
    """
    msg_str = ""
    if messages:
        msg_str = "\nMessages:\n" + "\n".join(
            "[%s] %s" % (m.get("sender_type",""), m.get("message_text","")) for m in messages[-3:]
        )

    prompt = """Summarise this complaint case for an agent handoff in 2-3 sentences.

Complaint ID: %s
Category: %s
Priority: %s
Status: %s
Channel: %s%s

Be concise and factual.""" % (
        complaint.get("complaint_id",""),
        complaint.get("category_name",""),
        complaint.get("priority",""),
        complaint.get("status",""),
        complaint.get("channel",""),
        msg_str
    )

    return _invoke(prompt, max_tokens=200)
