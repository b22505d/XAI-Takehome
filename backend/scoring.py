import json
from typing import List, Dict
from .models import PIPELINE_STAGES

DEFAULT_CRITERIA = [
    {"name": "Urgency / Buying intent", "weight": 25, "description": "Signals they need it soon / asked for timeline."},
    {"name": "Budget / ability to pay", "weight": 20, "description": "Budget mentioned, enterprise, funded, etc."},
    {"name": "Fit / relevance", "weight": 25, "description": "Role + industry aligns with what we offer."},
    {"name": "Authority / decision maker", "weight": 15, "description": "Is this person who can say yes?"},
    {"name": "Access / warm intro", "weight": 15, "description": "Mutual connections, inbound, referral."},
]

def build_qual_prompt(criteria: List[Dict], lead: Dict, activity_summaries: List[str]) -> str:
    return f"""
You are qualifying a sales lead based on USER-DEFINED criteria and weights.

Pipeline stages allowed: {PIPELINE_STAGES}

USER CRITERIA (weight out of 100):
{json.dumps(criteria, indent=2)}

LEAD:
{json.dumps(lead, indent=2)}

RECENT ACTIVITIES (most recent first):
{json.dumps(activity_summaries[:15], indent=2)}

Return STRICT JSON ONLY:
{{
  "score": integer 0-100,
  "stage": one of {PIPELINE_STAGES},
  "next_action": string,
  "rationale": string
}}

Rules:
- Keep rationale <= 280 chars.
- Score must reflect the weights.
- If poor fit, stage can be "lost".
- If strong fit + intent, stage should be "qualified" or "meeting".
""".strip()

def normalize_stage(stage: str | None) -> str | None:
    if not stage or not isinstance(stage, str):
        return None
    s = stage.strip().lower()
    return s if s in PIPELINE_STAGES else None

def fallback_stage_from_score(score: int | None) -> str | None:
    if not isinstance(score, int):
        return None
    if score >= 90:
        return "meeting"
    if score >= 75:
        return "qualified"
    if score >= 45:
        return "contacted"
    return "new"
