import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal
from api.models import User, Worker
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
import uuid

db = SessionLocal()

# ── Mock workers data ────────────────────────────────────
workers_data = [
    { "name": "Ram Thapa",       "email": "ram@sewabot.com",     "skill_tags": ["plumber","pipe repair","water leakage","tap installation"],              "lat": 27.7172, "lng": 85.3240, "rate": 500, "rating": 4.8, "reviews": 42 },
    { "name": "Sita Maharjan",   "email": "sita@sewabot.com",    "skill_tags": ["electrician","wiring","short circuit","light installation","fan repair"], "lat": 27.7000, "lng": 85.3100, "rate": 600, "rating": 4.6, "reviews": 38 },
    { "name": "Bikram Shrestha", "email": "bikram@sewabot.com",  "skill_tags": ["carpenter","furniture repair","door fitting","wood work"],               "lat": 27.7300, "lng": 85.3350, "rate": 550, "rating": 4.5, "reviews": 29 },
    { "name": "Kiran Tamang",    "email": "kiran@sewabot.com",   "skill_tags": ["plumber","drain cleaning","toilet repair","bathroom fitting"],            "lat": 27.7050, "lng": 85.3180, "rate": 450, "rating": 4.3, "reviews": 19 },
    { "name": "Anita Gurung",    "email": "anita@sewabot.com",   "skill_tags": ["painter","wall painting","interior painting","waterproofing"],            "lat": 27.7220, "lng": 85.3290, "rate": 400, "rating": 4.7, "reviews": 55 },
    { "name": "Dinesh Rai",      "email": "dinesh@sewabot.com",  "skill_tags": ["electrician","inverter installation","solar panel","electrical wiring"],  "lat": 27.7150, "lng": 85.3400, "rate": 700, "rating": 4.9, "reviews": 61 },
    { "name": "Priya Shrestha",  "email": "priya@sewabot.com",   "skill_tags": ["cleaner","deep cleaning","kitchen cleaning","bathroom cleaning"],         "lat": 27.7080, "lng": 85.3250, "rate": 350, "rating": 4.4, "reviews": 33 },
    { "name": "Suresh Karki",    "email": "suresh@sewabot.com",  "skill_tags": ["ac_technician","AC repair","AC installation","refrigerator repair"],      "lat": 27.7190, "lng": 85.3160, "rate": 650, "rating": 4.6, "reviews": 47 },
    { "name": "Maya Lama",       "email": "maya@sewabot.com",    "skill_tags": ["carpenter","cabinet making","shelf installation","wood polishing"],       "lat": 27.7260, "lng": 85.3320, "rate": 500, "rating": 4.2, "reviews": 14 },
    { "name": "Aakash Pandey",   "email": "aakash@sewabot.com",  "skill_tags": ["plumber","gas pipe fitting","water pump repair","pipe leakage"],          "lat": 27.7120, "lng": 85.3210, "rate": 480, "rating": 4.5, "reviews": 22 },
]

print(f"Seeding {len(workers_data)} workers...")

for w in workers_data:
    # 1. Create user account
    user = User(
        id            = str(uuid.uuid4()),
        email         = w["email"],
        password_hash = "hashed_password_placeholder",
        role          = "worker",
        full_name     = w["name"],
        phone         = "98XXXXXXXX",
        is_active     = True
    )
    db.add(user)
    db.flush()  # get user.id before creating worker

    # 2. Create worker profile linked to user
    # PostGIS expects POINT(longitude latitude)
    point = from_shape(Point(w["lng"], w["lat"]), srid=4326)

    worker = Worker(
        id            = str(uuid.uuid4()),
        user_id       = user.id,
        skill_tags    = w["skill_tags"],
        hourly_rate   = w["rate"],
        rating_avg    = w["rating"],
        total_reviews = w["reviews"],
        is_available  = True,
        is_verified   = True,
        location      = point,
        bio           = f"Experienced {w['skill_tags'][0]} based in Kathmandu."
    )
    db.add(worker)
    print(f"  ✓ {w['name']} ({w['skill_tags'][0]})")

db.commit()
db.close()
print("\nDone! Database seeded successfully.")