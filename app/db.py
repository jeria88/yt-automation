import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum
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


class ReelPipeline(Base):
    __tablename__ = "reel_pipeline"
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)

    status = Column(String(32), nullable=False, default="topic_pending")
    # topic_pending -> script_pending -> script_sent -> awaiting_audio -> audio_received ->
    # storyboard_pending -> storyboard_ready -> rendering -> render_ready ->
    # publishing -> published -> monitoring -> regenerating_hook -> republishing -> error

    topic_source = Column(String(64))
    script_text = Column(Text)
    hook_variant = Column(Integer, default=1)

    title = Column(String(200))
    description = Column(Text)
    thumbnail_path = Column(String(500))

    telegram_chat_id = Column(String(32))
    telegram_script_message_id = Column(String(32))
    telegram_audio_message_id = Column(String(32))
    telegram_gate1_message_id = Column(String(32))

    audio_file_path = Column(String(255))
    audio_duration_seconds = Column(Integer)

    storyboard_json = Column(Text)

    rendered_video_path = Column(String(500))
    youtube_video_id = Column(String(32))
    youtube_url = Column(String(255))
    youtube_privacy_status = Column(String(16), default="public")

    last_error = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class YoutubeCredential(Base):
    __tablename__ = "youtube_credential"
    id = Column(Integer, primary_key=True)
    channel_id = Column(String(64))
    channel_title = Column(String(255))
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class VideoMetrics(Base):
    __tablename__ = "video_metrics"
    id = Column(Integer, primary_key=True)
    reel_pipeline_id = Column(Integer, ForeignKey("reel_pipeline.id"))
    captured_at = Column(DateTime, default=datetime.datetime.utcnow)
    views = Column(Integer)
    impressions = Column(Integer)
    ctr = Column(Float)
    avg_view_duration_seconds = Column(Float)
    likes = Column(Integer)


def init_db():
    Base.metadata.create_all(bind=engine)
