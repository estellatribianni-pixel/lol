from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL: 
    raise ValueError("DATABASE_URL environment variable is not set")
engine=create_engine(DATABASE_URL,pool_size=5,max_overflow=10)

SessionLocal=sessionmaker(autoflush=False,bind=engine)
base=declarative_base()

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()