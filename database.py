import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DEFAULT_URL = "postgresql://user:password@postgres-auth/auth"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_URL)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
