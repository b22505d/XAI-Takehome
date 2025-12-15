import json
import time
import requests
from .settings import XAI_API_KEY, XAI_BASE_URL, MOCK_LLM

def _extract_json(text: str) -> dict:
    s = (text or "").strip()

    if s.startswith("```"):
        s = s.strip("`").strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()

    try:
        return json.loads(s)
    except Exception:
        pass

    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1 or j <= i:
        raise ValueError(f"Could not extract JSON from: {s[:200]}")
    return json.loads(s[i : j + 1])

def call_xai(model: str, prompt: str) -> dict:
    if MOCK_LLM or not XAI_API_KEY:
        p = prompt.lower()
        if '"message"' in p:
            return {"message": "Hi — quick note. I saw your work and thought we could help. Open to a 15-min chat this week?"}
        return {"score": 78, "stage": "qualified", "next_action": "Send intro + ask for 15-min call.", "rationale": "Mock qualification."}

    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return ONLY valid JSON. No markdown. No extra text."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    t0 = time.time()
    r = requests.post(f"{XAI_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
    latency_ms = int((time.time() - t0) * 1000)

    if not r.ok:
        raise RuntimeError(f"XAI HTTP {r.status_code}: {r.text[:800]}")

    content = r.json()["choices"][0]["message"]["content"]
    data = _extract_json(content)
    data["_latency_ms"] = latency_ms
    return data
