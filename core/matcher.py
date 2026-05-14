import os
import json
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "all-MiniLM-L6-v2"
model      = SentenceTransformer(MODEL_NAME)

# ── Haversine distance ───────────────────────────────────
def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

# ── Scoring formula ──────────────────────────────────────
def score_worker(skill_sim, rating, distance_km) -> float:
    skill_score      = 0.5 * skill_sim
    rating_score     = 0.3 * (rating / 5)
    distance_penalty = 0.2 * min(distance_km / 10, 1.0)
    return round(skill_score + rating_score - distance_penalty, 4)

# ── Main function — now queries PostgreSQL ───────────────
def match_workers_db(
    job:        dict,
    client_lat: float,
    client_lng: float,
    db:         Session,
    radius_km:  int = 10,
    top_k:      int = 3
) -> list:
    """
    Queries PostgreSQL + PostGIS to find nearby available workers.
    Ranks them using skill similarity + rating + distance.

    Steps:
    1. PostGIS finds all workers within radius_km of client
    2. Sentence Transformer embeds the job query
    3. Cosine similarity scores each worker's skills vs job
    4. Weighted formula ranks final results
    """

    # 1. PostGIS radius query — find nearby available verified workers
    sql = text("""
        SELECT
            w.id,
            w.skill_tags,
            w.rating_avg,
            w.total_reviews,
            w.hourly_rate,
            w.bio,
            w.is_available,
            u.full_name,
            ST_X(w.location::geometry) AS lng,
            ST_Y(w.location::geometry) AS lat,
            ST_Distance(
                w.location,
                ST_MakePoint(:lng, :lat)::geography
            ) / 1000.0 AS distance_km
        FROM workers w
        JOIN users u ON u.id = w.user_id
        WHERE
            w.is_available = TRUE
            AND w.is_verified = TRUE
            AND ST_DWithin(
                w.location,
                ST_MakePoint(:lng, :lat)::geography,
                :radius_meters
            )
        ORDER BY distance_km ASC
        LIMIT 20
    """)

    rows = db.execute(sql, {
        "lat":           client_lat,
        "lng":           client_lng,
        "radius_meters": radius_km * 1000
    }).fetchall()

    # If no workers found within radius, expand search
    if not rows:
        rows = db.execute(sql, {
            "lat":           client_lat,
            "lng":           client_lng,
            "radius_meters": 50 * 1000   # expand to 50km
        }).fetchall()

    if not rows:
        return []

    # 2. Embed job query
    query_text      = job.get("skill_category", "") + " " + job.get("summary", "")
    query_embedding = model.encode([query_text])[0]

    # 3. Score each worker
    results = []
    for row in rows:
        # Embed worker skills
        skill_text       = " ".join(row.skill_tags)
        worker_embedding = model.encode([skill_text])[0]

        # Cosine similarity
        cos_sim = float(np.dot(query_embedding, worker_embedding) /
                       (np.linalg.norm(query_embedding) * np.linalg.norm(worker_embedding)))

        final_score = score_worker(cos_sim, row.rating_avg, row.distance_km)

        results.append({
            "id":            str(row.id),
            "name":          row.full_name,
            "skill_tags":    row.skill_tags,
            "rating":        float(row.rating_avg),
            "total_reviews": row.total_reviews,
            "hourly_rate":   row.hourly_rate,
            "distance_km":   round(float(row.distance_km), 2),
            "score":         final_score,
            "bio":           row.bio or "",
            "lat":           float(row.lat),
            "lng":           float(row.lng),
        })

    # 4. Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# ── Fallback — still works without DB (for testing) ──────
def match_workers(job, client_lat, client_lng, top_k=3):
    """
    Legacy function using JSON + FAISS.
    Kept as fallback if DB is unavailable.
    """
    import faiss
    from sentence_transformers import SentenceTransformer

    INDEX_PATH    = "embeddings/workers.faiss"
    METADATA_PATH = "embeddings/workers_meta.json"

    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH) as f:
        workers = json.load(f)

    query_text      = job.get("skill_category","") + " " + job.get("summary","")
    query_embedding = model.encode([query_text]).astype("float32")
    distances, indices = index.search(query_embedding, k=min(10, len(workers)))
    max_dist    = max(distances[0]) if max(distances[0]) > 0 else 1
    similarities = [1 - (d / max_dist) for d in distances[0]]

    results = []
    for i, idx in enumerate(indices[0]):
        w           = workers[idx]
        if not w.get("available", True):
            continue
        distance_km = haversine(client_lat, client_lng, w["lat"], w["lng"])
        final_score = score_worker(similarities[i], w.get("rating", 3.0), distance_km)
        results.append({
            "id":            w["id"],
            "name":          w["name"],
            "skill_tags":    w["skill_tags"],
            "rating":        w.get("rating", 0),
            "total_reviews": w.get("total_reviews", 0),
            "hourly_rate":   w.get("hourly_rate", 0),
            "distance_km":   round(distance_km, 2),
            "score":         final_score,
            "bio":           w.get("bio", ""),
            "lat":           w["lat"],
            "lng":           w["lng"],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]