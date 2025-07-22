from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from utils.settings import settings

DEFAULT_URL = "postgresql://user:password@postgres-auth/auth"

DATABASE_URL = settings.database_url or DEFAULT_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
