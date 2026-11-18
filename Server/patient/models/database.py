import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database Configuration: Supports Cloud PostgreSQL (Neon/Supabase) or local SQLite fallback
env_db_url = os.getenv("DATABASE_URL")

if env_db_url:
    # SQLAlchemy requires postgresql:// instead of postgres://
    if env_db_url.startswith("postgres://"):
        env_db_url = env_db_url.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = env_db_url
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    PATIENT_DATA_DIR = os.path.join(BASE_DIR, "data", "patient")
    os.makedirs(PATIENT_DATA_DIR, exist_ok=True)
    PATIENT_DB_PATH = os.path.join(PATIENT_DATA_DIR, "patient_records.db")
    DATABASE_URL = f"sqlite:///{PATIENT_DB_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency function to get database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize patient tables."""
    Base.metadata.create_all(bind=engine)

