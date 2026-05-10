from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# ── Pagination ────────────────────────────────────────────────────────────────

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard page/page_size query parameters for list endpoints."""
    page:      int = Field(1,  ge=1,  description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=200, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response envelope."""
    items:     List[Any]
    total:     int
    page:      int
    page_size: int
    pages:     int
    has_next:  bool
    has_prev:  bool


def make_paginated(items: list, total: int, p: PaginationParams) -> Dict[str, Any]:
    """Build a PaginatedResponse dict from items + total + pagination params."""
    pages = max(1, math.ceil(total / p.page_size))
    return {
        "items":     items,
        "total":     total,
        "page":      p.page,
        "page_size": p.page_size,
        "pages":     pages,
        "has_next":  p.page < pages,
        "has_prev":  p.page > 1,
    }


class UserResponse(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role")
    ngo_id: Optional[str] = Field(None, description="Associated NGO identifier")
    full_name: Optional[str] = Field(None, description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")
    preferred_language: str = Field("en", description="Preferred language")
    communication_opt_in: bool = Field(True, description="Communication opt-in")
    consent_analytics: bool = Field(True, description="Analytics consent flag")
    consent_personalization: bool = Field(True, description="Personalization consent flag")
    consent_ai_training: bool = Field(False, description="AI training consent flag")
    profile_completed_at: Optional[datetime] = Field(None, description="Profile completion timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    email_verified: bool = Field(False, description="Email verification flag")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class NGOResponse(BaseModel):
    id: str = Field(..., description="Unique NGO identifier")
    name: str = Field(..., description="NGO name")
    description: str = Field("", description="NGO description")
    sector: Optional[str] = Field(None, description="Sector")
    website: Optional[str] = Field(None, description="Website URL")
    headquarters_city: Optional[str] = Field(None, description="Headquarters city")
    primary_contact_name: Optional[str] = Field(None, description="Primary contact name")
    primary_contact_phone: Optional[str] = Field(None, description="Primary contact phone")
    operating_regions: list[str] = Field(default_factory=list, description="Operating regions")
    mission_focus: list[str] = Field(default_factory=list, description="Mission focus tags")
    invite_code: str = Field(..., description="Invite code")
    created_by: str = Field(..., description="Creator user identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class VolunteerProfileResponse(BaseModel):
    id: str = Field(..., description="Profile identifier")
    user_id: str = Field(..., description="Associated user identifier")
    email: Optional[str] = Field(None, description="Associated email address")
    ngo_id: str = Field(..., description="Associated NGO identifier")
    skills: list[str] = Field(default_factory=list, description="Skills list")
    availability: dict = Field(default_factory=dict, description="Availability schedule")
    status: str = Field(..., description="Profile status")
    share_location: bool = Field(False, description="Location sharing flag")
    lat: Optional[float] = Field(None, description="Latitude")
    lng: Optional[float] = Field(None, description="Longitude")
    full_name: Optional[str] = Field(None, description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")
    city: Optional[str] = Field(None, description="City")
    bio: Optional[str] = Field(None, description="Biography")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    emergency_contact_name: Optional[str] = Field(None, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, description="Emergency contact phone")
    education_level: Optional[str] = Field(None, description="Education level")
    years_experience: Optional[int] = Field(None, description="Years of experience", ge=0)
    preferred_roles: list[str] = Field(default_factory=list, description="Preferred roles")
    certifications: list[str] = Field(default_factory=list, description="Certifications")
    languages: list[str] = Field(default_factory=list, description="Languages")
    causes_supported: list[str] = Field(default_factory=list, description="Causes supported")
    motivation_statement: Optional[str] = Field(None, description="Motivation statement")
    availability_notes: Optional[str] = Field(None, description="Availability notes")
    work_preferences: dict = Field(default_factory=dict, description="Work preferences")
    last_active_at: Optional[datetime] = Field(None, description="Last active timestamp")
    profile_completeness_score: float = Field(0.0, description="Profile completeness score", ge=0, le=100)
    completed_tasks: int = Field(0, description="Completed tasks count", ge=0)
    total_assigned: int = Field(0, description="Total assigned tasks", ge=0)
    acceptance_rate: float = Field(0.0, description="Acceptance rate as a fraction", ge=0, le=1)
    performance_score: float = Field(0.0, description="Performance score", ge=0, le=100)

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str = Field(..., description="Task identifier")
    ngo_id: str = Field(..., description="Associated NGO identifier")
    title: str = Field(..., description="Task title")
    description: str = Field("", description="Task description")
    required_skills: list[str] = Field(default_factory=list, description="Required skills")
    priority: str = Field("medium", description="Task priority")
    status: str = Field("open", description="Task status")
    deadline: Optional[datetime] = Field(None, description="Deadline timestamp")
    lat: Optional[float] = Field(None, description="Latitude")
    lng: Optional[float] = Field(None, description="Longitude")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    task_category: Optional[str] = Field(None, description="Task category")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours")
    urgency_score: float = Field(50.0, description="Urgency score", ge=0, le=100)
    impact_tags: list[str] = Field(default_factory=list, description="Impact tags")

    class Config:
        from_attributes = True


class AssignmentResponse(BaseModel):
    id: str = Field(..., description="Assignment identifier")
    task_id: str = Field(..., description="Task identifier")
    volunteer_id: str = Field(..., description="Volunteer identifier")
    ngo_id: str = Field(..., description="NGO identifier")
    status: str = Field("assigned", description="Assignment status")
    assigned_at: datetime = Field(..., description="Assigned timestamp")
    accepted_at: Optional[datetime] = Field(None, description="Accepted timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completed timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    hours_spent: Optional[float] = Field(None, description="Hours spent")
    completion_rating: Optional[int] = Field(None, description="Completion rating", ge=1, le=5)
    ngo_feedback: Optional[str] = Field(None, description="NGO feedback")
    match_score: Optional[float] = Field(None, description="AI match score", ge=0, le=100)

    class Config:
        from_attributes = True


class ConsentEventResponse(BaseModel):
    id: str = Field(..., description="Event identifier")
    user_id: str = Field(..., description="User identifier")
    scope: str = Field(..., description="Consent scope")
    granted: bool = Field(..., description="Consent granted flag")
    source: str = Field(..., description="Consent event source")
    created_at: datetime = Field(..., description="Event timestamp")

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str = Field(..., description="JWT access token")
    role: str = Field(..., description="Authenticated role")
    ngo_id: Optional[str] = Field(None, description="Associated NGO identifier")
    ngo_name: Optional[str] = Field(None, description="Associated NGO name")
    needs_ngo_setup: Optional[bool] = Field(None, description="Whether NGO setup is required")
    invite_code: Optional[str] = Field(None, description="Invite code for NGO setup or join flow")

    class Config:
        from_attributes = True