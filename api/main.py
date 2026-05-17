import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles

from api.database import get_db
from api.routers.auth_router import router as auth_router
from api.routers.websocket_router import router as ws_router
from api.routers.payment_router import router as payment_router
from core.classifier import classify_job
from core.matcher import match_workers_db

# ── App setup ────────────────────────────────────────────
app = FastAPI(
    title="SewaBot API",
    description="Uber for skilled workers — AI-powered job matching",
    version="1.0.0"
)
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(ws_router)
app.include_router(payment_router)

# ── Schemas ──────────────────────────────────────────────
class JobRequest(BaseModel):
    description: str
    client_lat:  float = 27.7172
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
def match(request: JobRequest, db: Session = Depends(get_db)):
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")

    job     = classify_job(request.description)
    workers = match_workers_db(job, request.client_lat, request.client_lng, db)

    if not workers:
        raise HTTPException(status_code=404, detail="No available workers found nearby")

    return {"job": job, "workers": workers}

@app.get("/workers")
def get_all_workers(db: Session = Depends(get_db)):
    from api.models import Worker, User
    from sqlalchemy import text
    rows = db.execute(text("""
        SELECT u.full_name, w.skill_tags, w.rating_avg, w.hourly_rate,
                ST_X(w.location::geometry) AS lng,
                ST_Y(w.location::geometry) AS lat
        FROM workers w
        JOIN users u ON u.id = w.user_id
        WHERE w.is_available = TRUE
    """)).fetchall()

    workers = [
        {
            "name":        r.full_name,
            "skill_tags":  r.skill_tags,
            "rating":      r.rating_avg,
            "hourly_rate": r.hourly_rate,
            "lat":         float(r.lat),
            "lng":         float(r.lng),
        }
        for r in rows
    ]
    return {"total": len(workers), "workers": workers}