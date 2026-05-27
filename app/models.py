from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()

# using explicit Python string enums to enforce clean serialization boundaries
# and prevent database mapping overhead when transforming models to JSON responses
class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Category(str, Enum):
    WORK = "work"
    PERSONAL = "personal"
    SHOPPING = "shopping"
    OTHER = "other"

class SubTask(Base):
    """
    SQLAlchemy model representing individual checklist items nested under a parent task.
    This allows granular tracking of action items for complex goals.
    """
    __tablename__ = "subtasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # timezone-aware timestamping ensures database records remain standard
    # regardless of backend server hosting location (UTC alignment)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="subtasks")

class Task(Base):
    """
    Primary database entity representing a single to-do item.
    Supports description texts, due dates, categories, priorities, and relational subtasks.
    """
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[Priority] = mapped_column(SQLEnum(Priority), default=Priority.MEDIUM, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="other", nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # cascade="all, delete-orphan" guarantees that when a task is deleted,
    # all its child subtasks are scrubbed from the database automatically, preventing dangling foreign key references
    subtasks: Mapped[List[SubTask]] = relationship("SubTask", back_populates="task", cascade="all, delete-orphan", lazy="selectin")


# --- PYDANTIC SCHEMAS FOR INBOUND/OUTBOUND VALIDATION ---

class SubTaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    is_completed: bool = False

class SubTaskCreate(SubTaskBase):
    pass

class SubTaskResponse(SubTaskBase):
    id: int
    task_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="after")
    @classmethod
    def ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    is_completed: bool = False
    priority: Priority = Priority.MEDIUM
    category: str = "other"
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    # allowing tasks to be initialized with subtasks directly during POST creation,
    # enabling bulk operations and smooth AI task decomposition
    subtasks: Optional[List[SubTaskCreate]] = Field(default_factory=list)

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    is_completed: Optional[bool] = None
    priority: Optional[Priority] = None
    category: Optional[str] = None
    due_date: Optional[datetime] = None

    # field validator to ensure clients cannot set empty titles if they explicitly submit a title field
    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Task title cannot be empty or whitespace-only")
        return v

class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    subtasks: List[SubTaskResponse] = []

    # from_attributes allows Pydantic to read database ORM objects directly
    # bypassing the need for manual dictionary conversion
    model_config = ConfigDict(from_attributes=True)

    @field_validator("due_date", "created_at", "completed_at", mode="after")
    @classmethod
    def ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
