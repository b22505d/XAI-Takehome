from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from .database import Base

PIPELINE_STAGES = ["new", "contacted", "qualified", "meeting", "won", "lost"]

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    company = Column(String, nullable=False)
    role = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    stage = Column(String, nullable=False, default="new")
    score = Column(Integer, nullable=True)
    last_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    activities = relationship("Activity", back_populates="lead", cascade="all, delete-orphan")

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True, nullable=False)

    type = Column(String, nullable=False)  # created, updated, score, message, stage_change, config_update, rescore_all
    detail = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    lead = relationship("Lead", back_populates="activities")

class ScoringConfig(Base):
    __tablename__ = "scoring_config"

    id = Column(Integer, primary_key=True, index=True)
    criteria = Column(JSON, nullable=False)  # list of {name, weight, description}
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
