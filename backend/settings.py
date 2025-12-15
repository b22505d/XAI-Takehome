import os

XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").strip()

XAI_MODEL_SCORE = os.getenv("XAI_MODEL_SCORE", "grok-4-fast").strip()
XAI_MODEL_MSG = os.getenv("XAI_MODEL_MSG", "grok-4-fast").strip()
XAI_EVAL_MODEL_A = os.getenv("XAI_EVAL_MODEL_A", "grok-4-fast").strip()
XAI_EVAL_MODEL_B = os.getenv("XAI_EVAL_MODEL_B", "grok-3").strip()

MOCK_LLM = os.getenv("MOCK_LLM", "0").strip() == "1"
