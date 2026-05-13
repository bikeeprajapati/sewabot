from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# ── So Python finds core/ from api/ ─────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.classifier import classify_job
from core.matcher import match_workers



# ── App setup ────────────────────────────────────────────
app = FastAPI(
    title="SewaBot API",
    description="Uber for skilled workers — AI-powered job matching",
    version="1.0.0"
)

# ── CORS — allows Streamlit to talk to FastAPI ───────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request/Response schemas ─────────────────────────────
class JobRequest(BaseModel):
    description: str
    client_lat:  float = 27.7172   # default: Kathmandu center
    client_lng:  float = 85.3240

class WorkerOut(BaseModel):
    id:            str
    name:          str
    skill_tags:    list
    rating:        float
    total_reviews: int
    hourly_rate:   int
    distance_km:   float
    score:         float
    bio:           str
    lat:           float
    lng:           float

class MatchResponse(BaseModel):
    job:     dict
    workers: list[WorkerOut]

# Add at the top with other imports
from api.routers.auth_router import router as auth_router

# Add after app = FastAPI(...)
app.include_router(auth_router)

# ── Routes ───────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "app":     "SewaBot",
        "version": "1.0.0",
        "status":  "running",
        "docs":    "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/match", response_model=MatchResponse)
def match(request: JobRequest):
    """
    Main endpoint.
    Accepts a job description + client location.
    Returns classified job + top 3 matched workers.
    """
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")

    job     = classify_job(request.description)
    workers = match_workers(job, request.client_lat, request.client_lng)

    if not workers:
        raise HTTPException(status_code=404, detail="No available workers found")

    return {"job": job, "workers": workers}

@app.get("/workers")
def get_all_workers():
    """
    Returns all workers with their locations.
    Used by the frontend to plot pins on the map at startup.
    """
    from core.matcher import workers as all_workers
    return {"total": len(all_workers), "workers": all_workers}