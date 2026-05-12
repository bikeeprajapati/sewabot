import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    Text, DateTime, Enum, ForeignKey, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from geoalchemy2 import Geography

Base = declarative_base()

# ── Helper — auto UUID ───────────────────────────────────
def gen_uuid():
    return str(uuid.uuid4())

# ════════════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password_hash= Column(String(255), nullable=False)
    role         = Column(Enum("client", "worker", name="user_role"), nullable=False)
    full_name    = Column(String(255), nullable=False)
    phone        = Column(String(20), nullable=True)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    # Relationships
    worker_profile = relationship("Worker", back_populates="user", uselist=False)
    jobs_as_client = relationship("Job", back_populates="client", foreign_keys="Job.client_id")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# ════════════════════════════════════════════════════════
# WORKERS
# ════════════════════════════════════════════════════════
class Worker(Base):
    __tablename__ = "workers"

    id            = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id       = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, unique=True)
    skill_tags    = Column(ARRAY(String), nullable=False, default=[])
    bio           = Column(Text, nullable=True)
    hourly_rate   = Column(Integer, nullable=False, default=500)   # in NPR
    rating_avg    = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    is_available  = Column(Boolean, default=True)
    is_verified   = Column(Boolean, default=False)  # admin must approve

    # PostGIS geography column — stores GPS coordinates
    # POINT(longitude latitude) in WGS84 coordinate system
    location      = Column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True
    )

    created_at    = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user          = relationship("User", back_populates="worker_profile")
    jobs          = relationship("Job", back_populates="worker", foreign_keys="Job.worker_id")
    reviews       = relationship("Review", back_populates="worker")

    def __repr__(self):
        return f"<Worker {self.user_id} rate={self.hourly_rate}>"


# ════════════════════════════════════════════════════════
# JOBS
# ════════════════════════════════════════════════════════
class Job(Base):
    __tablename__ = "jobs"

    id             = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    client_id      = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    worker_id      = Column(UUID(as_uuid=False), ForeignKey("workers.id"), nullable=True)  # NULL until accepted

    description    = Column(Text, nullable=False)       # original client input
    skill_category = Column(String(100), nullable=True) # output from AI classifier
    urgency        = Column(
        Enum("low", "medium", "high", name="urgency_level"),
        default="medium"
    )

    # Client's location when they posted the job
    location       = Column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True
    )

    status         = Column(
        Enum("pending", "accepted", "in_progress", "done", "cancelled", name="job_status"),
        default="pending"
    )

    created_at     = Column(DateTime, default=datetime.utcnow)
    accepted_at    = Column(DateTime, nullable=True)
    completed_at   = Column(DateTime, nullable=True)

    # Relationships
    client         = relationship("User", back_populates="jobs_as_client", foreign_keys=[client_id])
    worker         = relationship("Worker", back_populates="jobs", foreign_keys=[worker_id])
    review         = relationship("Review", back_populates="job", uselist=False)
    payment        = relationship("Payment", back_populates="job", uselist=False)

    def __repr__(self):
        return f"<Job {self.id[:8]} {self.skill_category} ({self.status})>"


# ════════════════════════════════════════════════════════
# REVIEWS
# ════════════════════════════════════════════════════════
class Review(Base):
    __tablename__ = "reviews"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id      = Column(UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=False, unique=True)
    reviewer_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    worker_id   = Column(UUID(as_uuid=False), ForeignKey("workers.id"), nullable=False)
    rating      = Column(Integer, nullable=False)   # 1 to 5
    comment     = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job         = relationship("Job", back_populates="review")
    worker      = relationship("Worker", back_populates="reviews")

    def __repr__(self):
        return f"<Review job={self.job_id[:8]} rating={self.rating}>"


# ════════════════════════════════════════════════════════
# PAYMENTS
# ════════════════════════════════════════════════════════
class Payment(Base):
    __tablename__ = "payments"

    id             = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id         = Column(UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=False, unique=True)
    amount         = Column(Integer, nullable=False)   # total in NPR
    worker_earning = Column(Integer, nullable=False)   # amount * 0.90
    platform_fee   = Column(Integer, nullable=False)   # amount * 0.10
    method         = Column(
        Enum("esewa", "khalti", "cash", name="payment_method"),
        default="esewa"
    )
    status         = Column(
        Enum("pending", "completed", "refunded", "failed", name="payment_status"),
        default="pending"
    )
    transaction_id = Column(String(255), nullable=True)  # from eSewa/Khalti
    paid_at        = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    # Relationship
    job            = relationship("Job", back_populates="payment")

    def __repr__(self):
        return f"<Payment job={self.job_id[:8]} amount={self.amount} ({self.status})>"