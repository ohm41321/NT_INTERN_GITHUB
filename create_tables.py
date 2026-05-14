# create_tables.py
# table -> models.py
from sqlalchemy import create_engine
from models import Base
import os
from dotenv import load_dotenv

load_dotenv()

# ใช้ sync engine (แทนที่จะใช้ create_async_engine)
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql+asyncpg", "postgresql")
engine = create_engine(DATABASE_URL)

def create_tables():
    print("Creating tables in the database...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    create_tables()

    
