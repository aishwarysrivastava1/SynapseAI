import uuid
import datetime
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime,
    ForeignKey, JSON, Index,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


def _gen_id() -> str:
    return str(uuid.uuid4())


# ── NGOs ────────────────────────────────────────────────────────────────────

class NGO(Base):
    __tablename__ = "ngos"

    id:          Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    name:        Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    created_by:  Mapped[str] = mapped_column(String(36), ForeignKey("users.id", use_alter=True, name="fk_ngo_created_by"), nullable=False)
    created_at:  Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# ── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_ngo_id", "ngo_id"),)

    id:            Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    email:         Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role:          Mapped[str] = mapped_column(
        SAEnum("ngo_admin", "volunteer", name="user_role"), nullable=False
    )
    ngo_id:        Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ngos.id"), nullable=True
    )
    created_at:    Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# ── Volunteer Profiles ───────────────────────────────────────────────────────

class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"
    __table_args__ = (Index("ix_vol_ngo_id", "ngo_id"),)

    id:           Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    user_id:      Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    ngo_id:       Mapped[str] = mapped_column(String(36), ForeignKey("ngos.id"), nullable=False)
    skills:       Mapped[list] = mapped_column(JSON, default=list)
    availability: Mapped[dict] = mapped_column(JSON, default=dict)
    status:       Mapped[str] = mapped_column(
        SAEnum("active", "inactive", name="vol_status"), default="active"
    )


# ── Tasks ────────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (Index("ix_task_ngo_id", "ngo_id"),)

    id:              Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    ngo_id:          Mapped[str] = mapped_column(String(36), ForeignKey("ngos.id"), nullable=False)
    title:           Mapped[str] = mapped_column(String(300), nullable=False)
    description:     Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    priority:        Mapped[str] = mapped_column(
        SAEnum("low", "medium", "high", name="task_priority"), default="medium"
    )
    status:          Mapped[str] = mapped_column(
        SAEnum("open", "in_progress", "completed", "cancelled", name="task_status"), default="open"
    )
    deadline:        Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at:      Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# ── Assignments ──────────────────────────────────────────────────────────────

class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (Index("ix_assign_ngo_id", "ngo_id"),)

    id:           Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    task_id:      Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False)
    volunteer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    ngo_id:       Mapped[str] = mapped_column(String(36), ForeignKey("ngos.id"), nullable=False)
    status:       Mapped[str] = mapped_column(
        SAEnum("assigned", "accepted", "rejected", "completed", name="assign_status"), default="assigned"
    )
    assigned_at:  Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# ── Resources ────────────────────────────────────────────────────────────────

class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (Index("ix_res_ngo_id", "ngo_id"),)

    id:                  Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    ngo_id:              Mapped[str] = mapped_column(String(36), ForeignKey("ngos.id"), nullable=False)
    type:                Mapped[str] = mapped_column(String(100), nullable=False)
    quantity:            Mapped[int] = mapped_column(Integer, default=0)
    availability_status: Mapped[str] = mapped_column(
        SAEnum("available", "in_use", "depleted", name="res_status"), default="available"
    )
    metadata_:           Mapped[dict] = mapped_column("metadata", JSON, default=dict)


# ── Allocations ──────────────────────────────────────────────────────────────

class Allocation(Base):
    __tablename__ = "allocations"

    id:                Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    resource_id:       Mapped[str] = mapped_column(String(36), ForeignKey("resources.id"), nullable=False)
    task_id:           Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False)
    ngo_id:            Mapped[str] = mapped_column(String(36), ForeignKey("ngos.id"), nullable=False)
    allocation_status: Mapped[str] = mapped_column(
        SAEnum("pending", "active", "released", name="alloc_status"), default="pending"
    )


# ── Events ───────────────────────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_event_ngo_id", "ngo_id"),)

    id:             Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    ngo_id:         Mapped[str] = mapped_column(String(36), ForeignKey("ngos.id"), nullable=False)
    title:          Mapped[str] = mapped_column(String(200), nullable=False)
    description:    Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type:     Mapped[str] = mapped_column(
        SAEnum("drive", "campaign", "camp", "training", name="event_type"), default="drive"
    )
    date:           Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    location:       Mapped[str] = mapped_column(String(300), nullable=False)
    max_volunteers: Mapped[int] = mapped_column(Integer, default=0)
    status:         Mapped[str] = mapped_column(
        SAEnum("upcoming", "active", "completed", name="event_status"), default="upcoming"
    )
    created_at:     Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class EventAttendance(Base):
    __tablename__ = "event_attendance"
    __table_args__ = (Index("ix_ea_event_id", "event_id"),)

    id:           Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    event_id:     Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    volunteer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status:       Mapped[str] = mapped_column(
        SAEnum("invited", "present", "absent", name="attend_status"), default="invited"
    )


# ── Notifications ─────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notif_user_id", "user_id"),)

    id:         Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    user_id:    Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    message:    Mapped[str] = mapped_column(Text, nullable=False)
    type:       Mapped[str] = mapped_column(
        SAEnum("task_assigned", "status_update", "general", name="notif_type"), default="general"
    )
    is_read:    Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
