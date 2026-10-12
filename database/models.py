import os
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

PROJECT_ROOT = Path(os.environ.get("SWALLOW_PROJECT_ROOT") or Path(__file__).resolve().parent.parent).resolve()
DATABASE_PATH = PROJECT_ROOT / "database" / "swallow.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# -----------------------------
# Database Models
# -----------------------------

class Participant(Base):
    __tablename__ = "participants"

    id = Column(String, primary_key=True)
    age = Column(Integer)
    gender = Column(String)
    dx = Column(String)

    sessions = relationship("Session", back_populates="participant")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    participant_id = Column(String, ForeignKey("participants.id"))
    audio_file_path = Column(String)
    audio_start_time = Column(Float, default=0.0)
    aspirating = Column(Boolean)
    total_swallows = Column(Integer)
    which_swallows = Column(String)
    method_of_drinking = Column(String)

    participant = relationship("Participant", back_populates="sessions")
    swallows = relationship("Swallow", back_populates="session")


class Swallow(Base):
    __tablename__ = "swallows"

    __table_args__ = (UniqueConstraint("session_id", "swallow_number"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    # 1-based position within the session, matching "Swallow Number N" in the spreadsheet.
    swallow_number = Column(Integer, nullable=False)
    start_time = Column(Float)
    end_time = Column(Float)
    flagged = Column(Boolean, default=False, nullable=False)

    session = relationship("Session", back_populates="swallows")
    annotation = relationship("Annotation", back_populates="swallow", uselist=False)


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    swallow_id = Column(Integer, ForeignKey("swallows.id"), unique=True, nullable=False)
    text = Column(Text, default="")

    swallow = relationship("Swallow", back_populates="annotation")

# -----------------------------
# Create tables
# -----------------------------

def init_db():
    Base.metadata.create_all(bind=engine)

