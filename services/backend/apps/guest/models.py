import uuid
from django.db import models


def _gen_uuid() -> str:
    return str(uuid.uuid4())


class Guest(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)
    is_converted_to_user = models.BooleanField(default=False)

    class Meta:
        db_table = "guests"


class GuestData(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    guest_id = models.CharField(max_length=36, unique=True, db_index=True)
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "guest_data"
