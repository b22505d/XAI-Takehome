from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from . import models
from .schemas import (
    LeadCreate, LeadUpdate, LeadOut,
    ActivityOut,
    ScoringConfigIn, ScoringConfigOut
)
from .settings import XAI_MODEL_SCORE, XAI_MODEL_MSG
from .llm import call_xai
from .scoring import DEFAULT_CRITERIA, build_qual_prompt, normalize_stage, fallback_stage_from_score
from .eval import run_eval

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_activity(db: Session, lead_id: int, type_: str, detail: str | None = None):
    db.add(models.Activity(lead_id=lead_id, type=type_, detail=detail or ""))

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        cfg = db.query(models.ScoringConfig).first()
        if not cfg:
            cfg = models.ScoringConfig(criteria=DEFAULT_CRITERIA, updated_at=datetime.utcnow())
            db.add(cfg)
            db.commit()
    finally:
        db.close()

@app.get("/health")
def health():
    return {"ok": True}

# ----- Scoring config (user defines what’s important) -----

@app.get("/scoring-config", response_model=ScoringConfigOut)
def get_scoring_config(db: Session = Depends(get_db)):
    cfg = db.query(models.ScoringConfig).first()
    if not cfg:
        cfg = models.ScoringConfig(criteria=DEFAULT_CRITERIA, updated_at=datetime.utcnow())
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return {"criteria": cfg.criteria, "updated_at": cfg.updated_at}

@app.put("/scoring-config", response_model=ScoringConfigOut)
def set_scoring_config(payload: ScoringConfigIn, db: Session = Depends(get_db)):
    # normalize: ensure weights sum doesn’t have to be 100, but keep in 0..100
    crit = [c.model_dump() for c in payload.criteria]
    cfg = db.query(models.ScoringConfig).first()
    if not cfg:
        cfg = models.ScoringConfig(criteria=crit, updated_at=datetime.utcnow())
        db.add(cfg)
    else:
        cfg.criteria = crit
        cfg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cfg)

    # optional: log as a global activity by attaching to lead_id=0 not allowed; so skip DB log here.
    return {"criteria": cfg.criteria, "updated_at": cfg.updated_at}

# ----- Leads CRUD -----

@app.post("/leads", response_model=LeadOut)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    lead = models.Lead(
        name=payload.name,
        company=payload.company,
        role=payload.role,
        industry=payload.industry,
        notes=payload.notes,
        stage="new",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    log_activity(db, lead.id, "created", f"Lead created: {lead.name} @ {lead.company}")
    db.commit()
    return lead

@app.get("/leads", response_model=list[LeadOut])
def list_leads(
    q: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Lead)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.Lead.name.ilike(like)) |
            (models.Lead.company.ilike(like)) |
            (models.Lead.role.ilike(like)) |
            (models.Lead.industry.ilike(like)) |
            (models.Lead.notes.ilike(like))
        )
    if stage:
        query = query.filter(models.Lead.stage == stage)
    return query.order_by(models.Lead.id.desc()).all()

@app.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    before_stage = lead.stage

    for k, v in payload.model_dump(exclude_unset=True).items():
        if k == "stage":
            if v and v not in models.PIPELINE_STAGES:
                raise HTTPException(status_code=400, detail="Invalid stage")
        setattr(lead, k, v)

    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)

    log_activity(db, lead.id, "updated", "Lead updated")
    if before_stage != lead.stage:
        log_activity(db, lead.id, "stage_change", f"{before_stage} -> {lead.stage}")
    db.commit()

    return lead

@app.delete("/leads/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"ok": True}

@app.get("/leads/{lead_id}/activities", response_model=list[ActivityOut])
def lead_activities(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    acts = db.query(models.Activity).filter(models.Activity.lead_id == lead_id).order_by(models.Activity.id.desc()).all()
    return acts

# ----- Qualification + automated progression -----

def apply_auto_progression(lead: models.Lead, score: int | None, stage_from_llm: str | None, caused_by: str):
    # Respect terminal stages
    if lead.stage in ["won", "lost"]:
        return

    stage = normalize_stage(stage_from_llm)
    if not stage:
        stage = fallback_stage_from_score(score)

    # minimum progression rules
    # - message sent => at least contacted
    if caused_by == "message" and lead.stage == "new":
        lead.stage = "contacted"
        return

    # do not regress by default (except LLM sets lost)
    order = {s: i for i, s in enumerate(models.PIPELINE_STAGES)}
    if stage == "lost":
        lead.stage = "lost"
        return

    if stage and order.get(stage, 0) >= order.get(lead.stage, 0):
        lead.stage = stage

@app.post("/leads/{lead_id}/score", response_model=LeadOut)
def score_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    cfg = db.query(models.ScoringConfig).first()
    criteria = cfg.criteria if cfg else DEFAULT_CRITERIA

    acts = (
        db.query(models.Activity)
        .filter(models.Activity.lead_id == lead_id)
        .order_by(models.Activity.id.desc())
        .limit(25)
        .all()
    )
    act_summaries = [f"{a.type}: {a.detail}" for a in acts]

    prompt = build_qual_prompt(
        criteria,
        {
            "name": lead.name,
            "company": lead.company,
            "role": lead.role,
            "industry": lead.industry,
            "notes": lead.notes,
            "current_stage": lead.stage,
            "current_score": lead.score,
        },
        act_summaries
    )

    try:
        out = call_xai(XAI_MODEL_SCORE, prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    score = out.get("score") if isinstance(out, dict) else None
    stage_from_llm = out.get("stage") if isinstance(out, dict) else None

    if isinstance(score, int):
        lead.score = max(0, min(100, score))

    before_stage = lead.stage
    apply_auto_progression(lead, lead.score, stage_from_llm, caused_by="score")

    lead.updated_at = datetime.utcnow()

    log_activity(db, lead.id, "score", f"score={lead.score} stage={lead.stage} next={out.get('next_action')} rationale={out.get('rationale')}")
    if before_stage != lead.stage:
        log_activity(db, lead.id, "stage_change", f"{before_stage} -> {lead.stage}")
    db.commit()
    db.refresh(lead)
    return lead

@app.post("/leads/{lead_id}/message")
def generate_message(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    prompt = f"""
Write a short outbound message (2-4 sentences).
Direct, professional, no fluff.
Return STRICT JSON ONLY: {{ "message": "..." }}

Lead:
name={lead.name}
company={lead.company}
role={lead.role}
industry={lead.industry}
notes={lead.notes}
stage={lead.stage}
score={lead.score}
""".strip()

    try:
        out = call_xai(XAI_MODEL_MSG, prompt)
        msg = out.get("message") if isinstance(out, dict) else None
        if not msg or not isinstance(msg, str):
            raise ValueError(f'No "message" in output: {out}')
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    before_stage = lead.stage
    lead.last_message = msg
    apply_auto_progression(lead, lead.score, None, caused_by="message")
    lead.updated_at = datetime.utcnow()

    log_activity(db, lead.id, "message", msg)
    if before_stage != lead.stage:
        log_activity(db, lead.id, "stage_change", f"{before_stage} -> {lead.stage}")
    db.commit()
    return {"message": msg, "stage": lead.stage}

@app.post("/leads/rescore-all")
def rescore_all(db: Session = Depends(get_db)):
    leads = db.query(models.Lead).all()
    updated = 0
    for lead in leads:
        if lead.stage in ["won", "lost"]:
            continue
        # reuse score logic quickly
        cfg = db.query(models.ScoringConfig).first()
        criteria = cfg.criteria if cfg else DEFAULT_CRITERIA
        acts = (
            db.query(models.Activity)
            .filter(models.Activity.lead_id == lead.id)
            .order_by(models.Activity.id.desc())
            .limit(25)
            .all()
        )
        prompt = build_qual_prompt(
            criteria,
            {
                "name": lead.name,
                "company": lead.company,
                "role": lead.role,
                "industry": lead.industry,
                "notes": lead.notes,
                "current_stage": lead.stage,
                "current_score": lead.score,
            },
            [f"{a.type}: {a.detail}" for a in acts]
        )
        try:
            out = call_xai(XAI_MODEL_SCORE, prompt)
        except Exception:
            continue

        score = out.get("score") if isinstance(out, dict) else None
        stage_from_llm = out.get("stage") if isinstance(out, dict) else None

        if isinstance(score, int):
            lead.score = max(0, min(100, score))

        before_stage = lead.stage
        apply_auto_progression(lead, lead.score, stage_from_llm, caused_by="score")
        lead.updated_at = datetime.utcnow()

        log_activity(db, lead.id, "score", f"[rescore-all] score={lead.score} stage={lead.stage}")
        if before_stage != lead.stage:
            log_activity(db, lead.id, "stage_change", f"{before_stage} -> {lead.stage}")
        updated += 1

    db.commit()
    return {"updated": updated}
@app.post("/eval/run")
def eval_run(db: Session = Depends(get_db)):
    cfg = db.query(models.ScoringConfig).first()
    criteria = cfg.criteria if cfg else DEFAULT_CRITERIA
    return run_eval(criteria=criteria)