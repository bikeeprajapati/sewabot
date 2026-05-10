import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from math import radians, sin, cos, sqrt, atan2

# ── Config ───────────────────────────────────────────────
INDEX_PATH    = "embeddings/workers.faiss"
METADATA_PATH = "embeddings/workers_meta.json"
MODEL_NAME    = "all-MiniLM-L6-v2"

# ── Load once at startup ─────────────────────────────────
model   = SentenceTransformer(MODEL_NAME)
index   = faiss.read_index(INDEX_PATH)

with open(METADATA_PATH, "r") as f:
    workers = json.load(f)

# ── Haversine distance formula ───────────────────────────
def haversine(lat1, lng1, lat2, lng2) -> float:
    """
    Calculate real-world distance in km between two GPS coordinates.
    Used to penalise workers who are far from the client.
    """
    R = 6371  # Earth radius in km
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a    = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

# ── Scoring formula ──────────────────────────────────────
def score_worker(skill_sim, rating, distance_km) -> float:
    """
    Final ranking score for each worker.

    score = (0.5 × skill_similarity)
            + (0.3 × rating / 5)
            - (0.2 × distance_km / 10)

    Weights explained:
    - Skill fit is most important (0.5)
    - Trust via rating comes second (0.3)
    - Distance is a penalty, not disqualifier (0.2)
    """
    skill_score    = 0.5 * skill_sim
    rating_score   = 0.3 * (rating / 5)
    distance_penalty = 0.2 * min(distance_km / 10, 1.0)  # cap penalty at 1.0
    return round(skill_score + rating_score - distance_penalty, 4)

# ── Main function ────────────────────────────────────────
def match_workers(job: dict, client_lat: float, client_lng: float, top_k: int = 3) -> list:
    """
    Given a classified job and client location,
    returns top_k ranked workers as a list of dicts.

    job = {
        "skill_category": "plumber",
        "urgency": "high",
        "location_hint": "Lalitpur",
        "summary": "Kitchen pipe leaking badly"
    }
    """

    # 1. Embed the job query
    query_text      = job.get("skill_category", "") + " " + job.get("summary", "")
    query_embedding = model.encode([query_text]).astype("float32")

    # 2. Search FAISS — get top 10 candidates
    distances, indices = index.search(query_embedding, k=min(10, len(workers)))

    # 3. Convert L2 distances to similarity scores (0 to 1)
    #    Lower L2 distance = more similar = higher score
    max_dist = max(distances[0]) if max(distances[0]) > 0 else 1
    similarities = [1 - (d / max_dist) for d in distances[0]]

    # 4. Score and filter each candidate
    results = []
    for i, idx in enumerate(indices[0]):
        worker = workers[idx]

        # Skip unavailable workers
        if not worker.get("available", True):
            continue

        distance_km = haversine(client_lat, client_lng, worker["lat"], worker["lng"])
        skill_sim   = similarities[i]
        rating      = worker.get("rating", 3.0)

        final_score = score_worker(skill_sim, rating, distance_km)

        results.append({
            "id":           worker["id"],
            "name":         worker["name"],
            "skill_tags":   worker["skill_tags"],
            "rating":       rating,
            "total_reviews":worker.get("total_reviews", 0),
            "hourly_rate":  worker.get("hourly_rate", 0),
            "distance_km":  round(distance_km, 2),
            "score":        final_score,
            "bio":          worker.get("bio", ""),
            "lat":          worker["lat"],
            "lng":          worker["lng"],
        })

    # 5. Sort by score descending → return top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# ── Quick test ───────────────────────────────────────────
if __name__ == "__main__":
    from classifier import classify_job

    # Simulate client location — center of Kathmandu
    CLIENT_LAT = 27.7172
    CLIENT_LNG = 85.3240

    test_cases = [
        "My kitchen pipe is leaking badly, water is everywhere",
        "The lights in my bedroom stopped working suddenly",
        "I need someone to fix a broken door in Lalitpur",
        "My AC is making a loud noise and not cooling",
    ]

    for description in test_cases:
        print("\n" + "=" * 55)
        print(f"Job: {description}")

        job     = classify_job(description)
        matches = match_workers(job, CLIENT_LAT, CLIENT_LNG)

        print(f"Classified as: {job['skill_category']} | urgency: {job['urgency']}")
        print(f"\nTop {len(matches)} matched workers:")

        for rank, w in enumerate(matches, 1):
            print(f"\n  #{rank} {w['name']}")
            print(f"      Skills    : {', '.join(w['skill_tags'])}")
            print(f"      Rating    : {w['rating']} ⭐ ({w['total_reviews']} reviews)")
            print(f"      Distance  : {w['distance_km']} km")
            print(f"      Rate      : Rs. {w['hourly_rate']}/hr")
            print(f"      Score     : {w['score']}")