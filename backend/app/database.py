from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = 'postgresql://postgres:xoxot3041@127.0.0.1:5432/mtr' 



engine = create_engine(
    DATABASE_URL,
    echo=True 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    print(db)
    try:
        yield db
    finally:
        db.close()


