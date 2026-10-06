from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()


def init_db():
    from models.user import User
    from models.skill import Skill, UserSkill
    from models.swap import SwapRequest
    from models.message import Message
    from models.review import Review
    from models.notification import Notification

    Base.metadata.create_all(bind=engine)