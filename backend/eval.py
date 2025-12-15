from __future__ import annotations
import statistics
from typing import Any, Dict, List, Tuple

from .llm import call_xai
from .scoring import DEFAULT_CRITERIA, build_qual_prompt, normalize_stage
from .settings import XAI_EVAL_MODEL_A, XAI_EVAL_MODEL_B
from .eval_cases import EVAL_CASES
from .models import PIPELINE_STAGES

REQUIRED_FIELDS = ["score", "stage", "next_action", "rationale"]

def _quality_check(out: dict) -> Tuple[bool, List[str]]:
    errs = []
    if not isinstance(out, dict):
        return False, ["not_dict"]

    for k in REQUIRED_FIELDS:
        if k not in out or out[k] in (None, ""):
            errs.append(f"missing_{k}")

    score = out.get("score")
    if not isinstance(score, int):
        errs.append("score_not_int")
    else:
        if score < 0 or score > 100:
            errs.append("score_out_of_range")

    stage = normalize_stage(out.get("stage"))
    if stage is None:
        errs.append("invalid_stage")

    return (len(errs) == 0), errs

def _agreement(a: dict, b: dict) -> bool:
    # agreement = same stage AND score close
    sa = normalize_stage(a.get("stage"))
    sb = normalize_stage(b.get("stage"))
    if sa is None or sb is None:
        return False
    if sa != sb:
        return False
    if not isinstance(a.get("score"), int) or not isinstance(b.get("score"), int):
        return False
    return abs(a["score"] - b["score"]) <= 10

def _gold_accuracy(out: dict, gold: dict) -> bool:
    # supports stage exact and score bounds
    stage_ok = True
    if "stage" in gold:
        stage_ok = (normalize_stage(out.get("stage")) == gold["stage"])
    score_ok = True
    sc = out.get("score")
    if isinstance(sc, int):
        if "score_min" in gold and sc < gold["score_min"]:
            score_ok = False
        if "score_max" in gold and sc > gold["score_max"]:
            score_ok = False
    else:
        score_ok = False
    return stage_ok and score_ok

def run_eval(criteria: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    criteria = criteria or DEFAULT_CRITERIA

    lat_a, lat_b = [], []
    parse_fail = 0
    quality_fail = 0
    gold_total = 0
    gold_correct = 0
    agree_total = 0
    agree_correct = 0

    samples = []

    for case in EVAL_CASES:
        prompt = build_qual_prompt(criteria, case["lead"], activity_summaries=[])

        out_a = call_xai(XAI_EVAL_MODEL_A, prompt)
        out_b = call_xai(XAI_EVAL_MODEL_B, prompt)

        la = int(out_a.get("_latency_ms", 0))
        lb = int(out_b.get("_latency_ms", 0))
        lat_a.append(la)
        lat_b.append(lb)

        ok_a, errs_a = _quality_check(out_a)
        ok_b, errs_b = _quality_check(out_b)

        # parse failures already handled in llm.py; treat schema fail as quality
        if not ok_a or not ok_b:
            quality_fail += 1

        # accuracy: if gold exists -> gold accuracy on model A
        if "gold" in case and isinstance(case["gold"], dict):
            gold_total += 1
            if ok_a and _gold_accuracy(out_a, case["gold"]):
                gold_correct += 1

        # otherwise report agreement between A and B
        agree_total += 1
        if ok_a and ok_b and _agreement(out_a, out_b):
            agree_correct += 1

        samples.append({
            "case_id": case["id"],
            "lead": case["lead"],
            "model_a": {"model": XAI_EVAL_MODEL_A, "out": out_a, "quality_ok": ok_a, "errors": errs_a},
            "model_b": {"model": XAI_EVAL_MODEL_B, "out": out_b, "quality_ok": ok_b, "errors": errs_b},
            "gold": case.get("gold"),
        })

    def stats(xs):
        if not xs:
            return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "min_ms": 0, "max_ms": 0}
        xs2 = sorted(xs)
        p50 = xs2[int(0.50 * (len(xs2) - 1))]
        p95 = xs2[int(0.95 * (len(xs2) - 1))]
        return {
            "avg_ms": int(sum(xs2) / len(xs2)),
            "p50_ms": int(p50),
            "p95_ms": int(p95),
            "min_ms": int(xs2[0]),
            "max_ms": int(xs2[-1]),
        }

    quality_pass_rate = 1 - (quality_fail / max(1, len(EVAL_CASES)))
    agreement_rate = agree_correct / max(1, agree_total)

    result = {
        "n": len(EVAL_CASES),
        "lat_model_a": stats(lat_a),
        "lat_model_b": stats(lat_b),
        "quality_failures": quality_fail,
        "quality_pass_rate": quality_pass_rate,
        "agreement_rate": agreement_rate,  # used when no gold exists
        "accuracy": (gold_correct / gold_total) if gold_total > 0 else None,  # true accuracy only if gold provided
        "gold_total": gold_total,
        "gold_correct": gold_correct,
        "samples": samples[:3],  # keep response small
    }
    return result
