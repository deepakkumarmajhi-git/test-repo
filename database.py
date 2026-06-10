import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

logger = logging.getLogger("app.database")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set!")

logger.info("Initializing database engine...")
try:
    engine = create_engine(DATABASE_URL)
    logger.info("Database engine successfully created.")
except Exception as e:
    logger.exception("Failed to create database engine.")
    raise e

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    logger.debug("Opening new database session...")
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.exception("Database session error encountered.")
        raise e
    finally:
        logger.debug("Closing database session.")
        db.close()