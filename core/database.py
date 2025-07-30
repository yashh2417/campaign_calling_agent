import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def create_db_and_tables():
    """Creates database tables if they don't exist."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def get_db():
    """
    FastAPI dependency to get a DB session.
    This pattern ensures the session is always closed, even if errors occur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()