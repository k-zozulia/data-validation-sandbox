"""Database tables: datasets, saved rule sets and validation jobs."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(16))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(512))
    row_count: Mapped[int] = mapped_column(Integer)
    column_count: Mapped[int] = mapped_column(Integer)
    profile: Mapped[dict] = mapped_column(JSON)
    # Working draft of the rules for this dataset (autosaved by the editor).
    rules_yaml: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow,
                                                 onupdate=utcnow)

    jobs: Mapped[list[Job]] = relationship(back_populates="dataset",
                                           cascade="all, delete-orphan")


class RuleSet(Base):
    """A named, reusable set of rules that can be applied to any dataset."""
    __tablename__ = "rule_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    rules_yaml: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow,
                                                 onupdate=utcnow)


class Job(Base):
    """One validation run of a rules snapshot against a dataset (sample or full)."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    rule_set_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rule_sets.id", ondelete="SET NULL"), nullable=True)
    mode: Mapped[str] = mapped_column(String(16))              # sample | full
    status: Mapped[str] = mapped_column(String(16), default="queued")
    # queued | running | succeeded | failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0..100
    rules_yaml: Mapped[str] = mapped_column(Text)              # snapshot at launch time
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    violations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                        nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                         nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="jobs")
