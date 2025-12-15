XAI TAKEHOME – GROK AI SDR SYSTEM

OVERVIEW
This project is a Grok-powered Sales Development Representative (SDR) prototype built for the xAI take-home assignment.  
The system demonstrates how Grok can be used as the core intelligence layer for lead qualification, scoring, personalized outreach, pipeline tracking, and model evaluation.

The goal is to showcase working features, clean architecture, and effective Grok integration rather than full production completeness.

--------------------------------------------------
FEATURES IMPLEMENTED

GROK API INTEGRATION
- Grok used as the core intelligence layer
- Prompt engineering optimized for sales use cases
- Response validation and error handling

LEAD QUALIFICATION & MANAGEMENT
- Create and store leads (CRUD)
- Grok-based lead scoring and qualification
- User-defined scoring weights with re-scoring
- Automated sales pipeline stages
- Lead progress tracking across the pipeline
- Detailed activity and interaction logging

PIPELINE STAGES
new → scored → contacted → replied → meeting → won / lost

Stages advance automatically based on user actions.

PERSONALIZED MESSAGING
- Grok generates customized outreach messages per lead
- Message sending is logged as activity

MODEL EVALUATION FRAMEWORK
- Evaluation dataset included
- Runs evaluation across multiple Grok models
- Metrics collected:
  - Accuracy (rule-based expectation match)
  - Relevance & quality checks
  - Latency (avg, p50, p95)
  - Failure analysis
- Designed to simulate competitor/model comparison

USER INTERFACE
- Simple, sales-friendly UI
- Lead creation, scoring, messaging, and evaluation from UI
- Clear pipeline visibility

DATA MANAGEMENT
- SQLite database
- SQLAlchemy ORM
- Data validation and structured schemas
- Activity history stored per lead

--------------------------------------------------
TECH STACK

Backend:
- Python
- FastAPI
- SQLAlchemy
- SQLite

Frontend:
- React
- Vite

LLM:
- Grok (xAI API)

Infrastructure:
- Docker
- Docker Compose

--------------------------------------------------
LOCAL SETUP (DOCKER)

Run the full application:
docker-compose up --build

Frontend:
http://localhost:5173

Backend:
http://localhost:8000

--------------------------------------------------
ENVIRONMENT VARIABLES

XAI_API_KEY=your_api_key
XAI_BASE_URL=https://api.x.ai/v1

If no API key is provided, the system can run in mock mode for UI and flow demonstration.

--------------------------------------------------
PROJECT STRUCTURE

backend/
  - main.py
  - models.py
  - llm.py
  - eval.py

frontend/
  - src/
  - App.jsx

docker-compose.yml
Dockerfile

--------------------------------------------------
NOTES

- Built as a time-boxed 4-hour prototype
- Focus on quality over quantity
- Designed for client demo and extensibility
- Emphasis on Grok usage, evaluation, and SDR workflows

--------------------------------------------------
END
