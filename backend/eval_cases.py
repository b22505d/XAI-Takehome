EVAL_CASES = [
  {
    "id": "case_1",
    "lead": {
      "name": "Anita",
      "company": "Seed-funded B2B SaaS",
      "role": "Head of Sales Ops",
      "industry": "SaaS",
      "notes": "Inbound demo request. Wants to move in 2 weeks. Has budget approval.",
      "current_stage": "new",
      "current_score": None
    },
    # optional gold (only if you want true accuracy)
    "gold": {"stage": "meeting", "score_min": 85}
  },
  {
    "id": "case_2",
    "lead": {
      "name": "Mike",
      "company": "Local retail",
      "role": "Owner",
      "industry": "Retail",
      "notes": "Curious but no timeline, no budget, wants free option.",
      "current_stage": "contacted",
      "current_score": 40
    },
    "gold": {"stage": "contacted", "score_max": 50}
  },
  {
    "id": "case_3",
    "lead": {
      "name": "Priya",
      "company": "Fortune 500",
      "role": "Director IT",
      "industry": "Manufacturing",
      "notes": "Warm intro via partner. Needs security review. Budget likely OK.",
      "current_stage": "new",
      "current_score": None
    },
    "gold": {"stage": "qualified", "score_min": 70}
  },
]
