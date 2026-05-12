import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine — the connection to PostgreSQL
engine = create_engine(
    DATABASE_URL,
    echo=False,       # set True to see SQL queries in terminal (useful for debugging)
    pool_size=5,      # keep 5 connections open
    max_overflow=10   # allow 10 extra connections under load
)

# SessionLocal — used to create DB sessions in FastAPI
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI dependency — gives each request its own DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()