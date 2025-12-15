from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field

class LeadCreate(BaseModel):
    name: str
    company: str
    role: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None
    stage: Optional[str] = None

class LeadOut(BaseModel):
    id: int
    name: str
    company: str
    role: Optional[str]
    industry: Optional[str]
    notes: Optional[str]
    stage: str
    score: Optional[int]
    last_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ActivityOut(BaseModel):
    id: int
    lead_id: int
    type: str
    detail: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class CriteriaItem(BaseModel):
    name: str = Field(..., min_length=1)
    weight: int = Field(..., ge=0, le=100)
    description: str = ""

class ScoringConfigOut(BaseModel):
    criteria: List[CriteriaItem]
    updated_at: datetime

class ScoringConfigIn(BaseModel):
    criteria: List[CriteriaItem]
