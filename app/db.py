import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ytauto.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
metadata = Base.metadata


class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    stage = Column(String(32), nullable=False, default="idea")  # idea,guion,audio,edicion,miniatura,publicado
    hook_id = Column(Integer, ForeignKey("hooks.id"), nullable=True)
    notes = Column(Text, default="")
    due = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    scripts = relationship("Script", back_populates="video", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="video", cascade="all, delete-orphan")


class Hook(Base):
    __tablename__ = "hooks"
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    source = Column(String(64), default="manual")  # manual, reddit, youtube, trends
    tags = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Script(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    body = Column(Text, default="")
    philosophy = Column(String(64), default="espejo")  # espejo, sombra, pilares
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    video = relationship("Video", back_populates="scripts")


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="planned")  # planned, published, failed
    platform = Column(String(32), default="youtube")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    video = relationship("Video", back_populates="posts")


def init_db():
    Base.metadata.create_all(bind=engine)
