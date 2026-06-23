import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()

# Get DB_URL from .env, fallback to local sqlite if empty
database_url = os.getenv('DB_URL', '')
if not database_url:
    database_url = 'sqlite:///./notes.db'

print("!<----Initializing Request to Database")
if database_url.startswith("sqlite"):
    engine = create_engine(database_url, connect_args={'check_same_thread': False})
else:
    # Ensure psycopg2 is used for Neon/Postgres
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://") and "psycopg2" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        
    engine = create_engine(database_url)

print("!<----Initializing Session with Database---->!")
SessionLocal = sessionmaker(autoflush=False, autocommit=False,bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
