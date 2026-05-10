import uuid
import datetime
from django.db import models


def _gen_uuid() -> str:
    return str(uuid.uuid4())


class NGO(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    name = models.CharField(max_length=200)
    description = models.TextField(default="")
    invite_code = models.CharField(max_length=16, unique=True)
    # created_by kept as CharField to avoid circular FK with User
    created_by = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add=True)
    sector = models.CharField(max_length=120, null=True, blank=True)
    website = models.CharField(max_length=300, null=True, blank=True)
    headquarters_city = models.CharField(max_length=120, null=True, blank=True)
    primary_contact_name = models.CharField(max_length=200, null=True, blank=True)
    primary_contact_phone = models.CharField(max_length=30, null=True, blank=True)
    operating_regions = models.JSONField(default=list)
    mission_focus = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ngos"


class User(models.Model):
    ROLE_CHOICES = [("ngo_admin", "ngo_admin"), ("volunteer", "volunteer")]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    email = models.CharField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    # ngo_id as CharField to avoid circular FK with NGO
    ngo_id = models.CharField(max_length=36, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    preferred_language = models.CharField(max_length=32, default="en")
    communication_opt_in = models.BooleanField(default=True)
    consent_analytics = models.BooleanField(default=True)
    consent_personalization = models.BooleanField(default=True)
    consent_ai_training = models.BooleanField(default=False)
    profile_completed_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["ngo_id"],         name="ix_users_ngo_id"),
            models.Index(fields=["role"],            name="ix_users_role"),
            models.Index(fields=["ngo_id", "role"],  name="ix_users_ngo_role"),
        ]


class VolunteerProfile(models.Model):
    STATUS_CHOICES = [("active", "active"), ("inactive", "inactive")]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    user_id = models.CharField(max_length=36, unique=True)
    ngo_id = models.CharField(max_length=36)
    skills = models.JSONField(default=list)
    availability = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    share_location = models.BooleanField(default=False)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=200, null=True, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, null=True, blank=True)
    education_level = models.CharField(max_length=80, null=True, blank=True)
    years_experience = models.IntegerField(null=True, blank=True)
    preferred_roles = models.JSONField(default=list)
    certifications = models.JSONField(default=list)
    languages = models.JSONField(default=list)
    causes_supported = models.JSONField(default=list)
    motivation_statement = models.TextField(null=True, blank=True)
    availability_notes = models.TextField(null=True, blank=True)
    work_preferences = models.JSONField(default=dict)
    last_active_at = models.DateTimeField(null=True, blank=True)
    profile_completeness_score = models.FloatField(default=0.0)

    class Meta:
        db_table = "volunteer_profiles"
        indexes = [
            models.Index(fields=["ngo_id"],          name="ix_vol_ngo_id"),
            models.Index(fields=["status"],           name="ix_vol_status"),
            models.Index(fields=["ngo_id", "status"], name="ix_vol_ngo_status"),
        ]


class ConsentEvent(models.Model):
    SCOPE_CHOICES = [
        ("analytics", "analytics"),
        ("personalization", "personalization"),
        ("ai_training", "ai_training"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    user_id = models.CharField(max_length=36)
    scope = models.CharField(max_length=30, choices=SCOPE_CHOICES)
    granted = models.BooleanField()
    source = models.CharField(max_length=60, default="ui")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "consent_events"
        indexes = [
            models.Index(fields=["user_id"], name="ix_consent_user_id"),
            models.Index(fields=["scope"], name="ix_consent_scope"),
        ]
