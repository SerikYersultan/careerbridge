from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean,
    UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .database import Base

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_role = Column(String(120), nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="roadmaps")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    resume_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    roadmaps = relationship("Roadmap", back_populates="user", cascade="all, delete-orphan")
class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=True)

    user_links = relationship("UserSkill", back_populates="skill", cascade="all, delete-orphan")
    job_links = relationship("JobSkill", back_populates="skill", cascade="all, delete-orphan")


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    confirmed = Column(Boolean, default=True, nullable=False)
    source = Column(String(32), default="manual", nullable=False)

    user = relationship("User", back_populates="skills")
    skill = relationship("Skill", back_populates="user_links")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    location = Column(String(128), nullable=True)
    seniority = Column(String(32), nullable=True)
    description = Column(Text, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String(8), default="KZT")
    source_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    skill_links = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),)

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    weight = Column(Float, default=1.0, nullable=False)

    job = relationship("Job", back_populates="skill_links")
    skill = relationship("Skill", back_populates="job_links")




Index("ix_user_skills_user", UserSkill.user_id)
Index("ix_job_skills_job", JobSkill.job_id)
