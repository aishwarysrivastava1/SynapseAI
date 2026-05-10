import uuid
from django.db import models


def _gen_uuid() -> str:
    return str(uuid.uuid4())


class Task(models.Model):
    PRIORITY_CHOICES = [("low", "low"), ("medium", "medium"), ("high", "high")]
    STATUS_CHOICES = [
        ("open", "open"), ("in_progress", "in_progress"),
        ("completed", "completed"), ("cancelled", "cancelled"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    ngo_id = models.CharField(max_length=36)
    title = models.CharField(max_length=300)
    description = models.TextField(default="")
    required_skills = models.JSONField(default=list)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    deadline = models.DateTimeField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    task_category = models.CharField(max_length=100, null=True, blank=True)
    estimated_hours = models.FloatField(null=True, blank=True)
    urgency_score = models.FloatField(default=50.0)
    impact_tags = models.JSONField(default=list)

    class Meta:
        db_table = "tasks"
        indexes = [
            models.Index(fields=["ngo_id"],          name="ix_task_ngo_id"),
            models.Index(fields=["status"],           name="ix_task_status"),
            models.Index(fields=["ngo_id", "status"], name="ix_task_ngo_status"),
        ]


class Assignment(models.Model):
    STATUS_CHOICES = [
        ("assigned", "assigned"), ("accepted", "accepted"),
        ("rejected", "rejected"), ("completed", "completed"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    task_id = models.CharField(max_length=36)
    volunteer_id = models.CharField(max_length=36)
    ngo_id = models.CharField(max_length=36)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="assigned")
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    hours_spent = models.FloatField(null=True, blank=True)
    completion_rating = models.IntegerField(null=True, blank=True)
    ngo_feedback = models.TextField(null=True, blank=True)
    match_score = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "assignments"
        indexes = [
            models.Index(fields=["ngo_id"], name="ix_assign_ngo_id"),
            models.Index(fields=["volunteer_id"], name="ix_assign_volunteer_id"),
            models.Index(fields=["task_id"], name="ix_assign_task_id"),
            models.Index(fields=["ngo_id", "status"], name="ix_assign_ngo_status"),
            models.Index(fields=["volunteer_id", "status"], name="ix_assign_volunteer_status"),
        ]


class Resource(models.Model):
    STATUS_CHOICES = [
        ("available", "available"), ("in_use", "in_use"), ("depleted", "depleted"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    ngo_id = models.CharField(max_length=36)
    type = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)
    availability_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    metadata = models.JSONField(default=dict, db_column="metadata")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "resources"
        indexes = [models.Index(fields=["ngo_id"], name="ix_res_ngo_id")]


class Allocation(models.Model):
    STATUS_CHOICES = [
        ("pending", "pending"), ("active", "active"), ("released", "released"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    resource_id = models.CharField(max_length=36)
    task_id = models.CharField(max_length=36)
    ngo_id = models.CharField(max_length=36)
    allocation_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        db_table = "allocations"


class Event(models.Model):
    TYPE_CHOICES = [
        ("drive", "drive"), ("campaign", "campaign"),
        ("camp", "camp"), ("training", "training"),
    ]
    STATUS_CHOICES = [
        ("upcoming", "upcoming"), ("active", "active"), ("completed", "completed"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    ngo_id = models.CharField(max_length=36)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="drive")
    date = models.DateTimeField()
    location = models.CharField(max_length=300)
    max_volunteers = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="upcoming")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "events"
        indexes = [models.Index(fields=["ngo_id"], name="ix_event_ngo_id")]


class EventAttendance(models.Model):
    STATUS_CHOICES = [
        ("invited", "invited"), ("present", "present"), ("absent", "absent"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    event_id = models.CharField(max_length=36)
    volunteer_id = models.CharField(max_length=36)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="invited")

    class Meta:
        db_table = "event_attendance"
        indexes = [models.Index(fields=["event_id"], name="ix_ea_event_id")]


class Notification(models.Model):
    TYPE_CHOICES = [
        ("task_assigned", "task_assigned"),
        ("status_update", "status_update"),
        ("general", "general"),
        ("urgent", "urgent"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    user_id = models.CharField(max_length=36)
    message = models.TextField()
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="general")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        indexes = [models.Index(fields=["user_id"], name="ix_notif_user_id")]


class TaskEnrollmentRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "pending"), ("approved", "approved"), ("rejected", "rejected"),
    ]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    task_id = models.CharField(max_length=36)
    volunteer_id = models.CharField(max_length=36)
    ngo_id = models.CharField(max_length=36)
    reason = models.TextField(default="")
    why_useful = models.TextField(default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "task_enrollment_requests"
        indexes = [
            models.Index(fields=["ngo_id"], name="ix_enroll_ngo_id"),
            models.Index(fields=["volunteer_id"], name="ix_enroll_volunteer_id"),
            models.Index(fields=["task_id"], name="ix_enroll_task_id"),
            models.Index(fields=["volunteer_id", "status"], name="ix_enroll_volunteer_status"),
        ]
