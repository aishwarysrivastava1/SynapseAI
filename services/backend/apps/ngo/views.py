import logging
import os
from datetime import datetime, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from apps.accounts.models import User, VolunteerProfile, NGO
from apps.ngo.models import (
    Task, Assignment, Resource, Allocation, Event, EventAttendance,
    Notification, TaskEnrollmentRequest,
)
from apps.core.authentication import SynapseJWTAuthentication
from apps.core.permissions import IsNGOAdminWithNGO, assert_same_ngo

logger = logging.getLogger(__name__)
ENABLE_DYNAMIC_REASSIGNMENT = os.getenv("ENABLE_DYNAMIC_REASSIGNMENT", "true").lower() == "true"


# ── Serializers ──────────────────────────────────────────────────────────────

class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=2, max_length=300)
    description = serializers.CharField(max_length=2000, default="")
    required_skills = serializers.ListField(child=serializers.CharField(), default=list)
    priority = serializers.ChoiceField(choices=["low","medium","high"], default="medium")
    deadline = serializers.DateTimeField(required=False, allow_null=True, default=None)
    lat = serializers.FloatField(required=False, allow_null=True, default=None)
    lng = serializers.FloatField(required=False, allow_null=True, default=None)
    task_category = serializers.CharField(required=False, allow_null=True, max_length=100, default=None)
    estimated_hours = serializers.FloatField(required=False, allow_null=True, default=None)
    urgency_score = serializers.FloatField(required=False, default=50.0)
    impact_tags = serializers.ListField(child=serializers.CharField(), default=list)


class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=300)
    description = serializers.CharField(required=False, max_length=2000)
    required_skills = serializers.ListField(child=serializers.CharField(), required=False)
    priority = serializers.ChoiceField(choices=["low","medium","high"], required=False)
    status = serializers.ChoiceField(choices=["open","in_progress","completed","cancelled"], required=False)
    deadline = serializers.DateTimeField(required=False, allow_null=True)
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)


class ResourceCreateSerializer(serializers.Serializer):
    type = serializers.CharField(min_length=2, max_length=100)
    quantity = serializers.IntegerField(min_value=0)
    metadata = serializers.DictField(default=dict)
    lat = serializers.FloatField(required=False, allow_null=True, default=None)
    lng = serializers.FloatField(required=False, allow_null=True, default=None)


class EventCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_null=True, default=None)
    event_type = serializers.ChoiceField(choices=["drive","campaign","camp","training"], default="drive")
    date = serializers.DateTimeField()
    location = serializers.CharField(max_length=300)
    max_volunteers = serializers.IntegerField(default=0)


# ── Dashboard ────────────────────────────────────────────────────────────────

class DashboardView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        total_vols = User.objects.filter(ngo_id=nid, role="volunteer").count()
        active_tasks = Task.objects.filter(ngo_id=nid, status="in_progress").count()
        open_tasks = Task.objects.filter(ngo_id=nid, status="open").count()
        completed_tasks = Task.objects.filter(ngo_id=nid, status="completed").count()
        resource_count = Resource.objects.filter(ngo_id=nid).count()
        pending_assignments = Assignment.objects.filter(ngo_id=nid, status="assigned").count()
        recent = Task.objects.filter(ngo_id=nid).order_by("-created_at")[:5]
        try:
            ngo = NGO.objects.get(id=nid)
            invite_code = ngo.invite_code
        except NGO.DoesNotExist:
            invite_code = None
        return Response({
            "total_volunteers": total_vols,
            "active_tasks": active_tasks,
            "open_tasks": open_tasks,
            "completed_tasks": completed_tasks,
            "resource_count": resource_count,
            "pending_assignments": pending_assignments,
            "invite_code": invite_code,
            "recent_tasks": [
                {"id": t.id, "title": t.title, "status": t.status,
                 "deadline": t.deadline, "priority": t.priority}
                for t in recent
            ],
        })


# ── Volunteers ───────────────────────────────────────────────────────────────

class VolunteersView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        skill = request.query_params.get("skill")
        status = request.query_params.get("status")
        profiles = VolunteerProfile.objects.filter(ngo_id=nid)
        if skill:
            profiles = [p for p in profiles if skill in (p.skills or [])]
        else:
            profiles = list(profiles)
        if status:
            profiles = [p for p in profiles if p.status == status]
        user_map = {
            u["id"]: u
            for u in User.objects.filter(
                id__in=[p.user_id for p in profiles]
            ).values("id", "email")
        }
        result = []
        for p in profiles:
            u = user_map.get(p.user_id)
            if not u:
                continue
            completed = Assignment.objects.filter(volunteer_id=p.user_id, ngo_id=nid, status="completed").count()
            total = Assignment.objects.filter(volunteer_id=p.user_id, ngo_id=nid).count()
            result.append({
                "id": p.id, "user_id": p.user_id, "email": u["email"],
                "full_name": p.full_name, "skills": p.skills, "status": p.status,
                "city": p.city, "availability": p.availability,
                "profile_completeness_score": p.profile_completeness_score,
                "completed_tasks": completed, "total_assigned": total,
            })
        return Response(result)


class VolunteerDetailView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request, volunteer_id):
        nid = request.user.ngo_id
        try:
            p = VolunteerProfile.objects.get(user_id=volunteer_id, ngo_id=nid)
        except VolunteerProfile.DoesNotExist:
            return Response({"detail": "Volunteer not found"}, status=404)
        try:
            u = User.objects.get(id=volunteer_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        assignments = Assignment.objects.filter(volunteer_id=volunteer_id, ngo_id=nid)
        completed = assignments.filter(status="completed").count()
        total = assignments.count()
        return Response({
            "id": p.id, "user_id": p.user_id, "email": u.email, "ngo_id": p.ngo_id,
            "full_name": p.full_name, "skills": p.skills, "availability": p.availability,
            "status": p.status, "share_location": p.share_location,
            "lat": p.lat, "lng": p.lng, "city": p.city, "bio": p.bio,
            "education_level": p.education_level, "years_experience": p.years_experience,
            "languages": p.languages, "causes_supported": p.causes_supported,
            "certifications": p.certifications, "preferred_roles": p.preferred_roles,
            "profile_completeness_score": p.profile_completeness_score,
            "completed_tasks": completed, "total_assigned": total,
            "acceptance_rate": completed/total if total > 0 else 0.0,
        })

    def delete(self, request, volunteer_id):
        nid = request.user.ngo_id
        updated = VolunteerProfile.objects.filter(user_id=volunteer_id, ngo_id=nid).update(status="inactive")
        if not updated:
            return Response({"detail": "Volunteer not found"}, status=404)
        return Response({"message": "Volunteer deactivated"})


# ── Tasks ────────────────────────────────────────────────────────────────────

class TasksView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        status = request.query_params.get("status")
        priority = request.query_params.get("priority")
        qs = Task.objects.filter(ngo_id=nid)
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        qs = qs.order_by("-created_at")
        return Response([{
            "id": t.id, "ngo_id": t.ngo_id, "title": t.title, "description": t.description,
            "required_skills": t.required_skills, "priority": t.priority, "status": t.status,
            "deadline": t.deadline, "lat": t.lat, "lng": t.lng, "created_at": t.created_at,
            "updated_at": t.updated_at, "task_category": t.task_category,
            "estimated_hours": t.estimated_hours, "urgency_score": t.urgency_score,
            "impact_tags": t.impact_tags,
        } for t in qs])

    def post(self, request):
        nid = request.user.ngo_id
        s = TaskCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        task = Task.objects.create(ngo_id=nid, **d)
        try:
            from services.neo4j_service import neo4j_service
            from asgiref.sync import async_to_sync
            import threading
            _t, _nid = task, nid

            def _ingest():
                try:
                    async_to_sync(neo4j_service.upsert_task_node)(
                        task_id=_t.id, ngo_id=_nid, title=_t.title,
                        required_skills=_t.required_skills or [],
                        urgency=float(_t.urgency_score or 50), status=_t.status,
                        lat=_t.lat, lng=_t.lng,
                    )
                except Exception as exc:
                    logger.warning("Neo4j task ingest failed: %s", exc)

            threading.Thread(target=_ingest, daemon=True).start()
        except Exception:
            pass
        return Response({"id": task.id, "title": task.title, "status": task.status,
                         "ngo_id": nid, "created_at": task.created_at}, status=201)


class TaskDetailView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def _get_task(self, task_id, nid):
        try:
            return Task.objects.get(id=task_id, ngo_id=nid)
        except Task.DoesNotExist:
            return None

    def get(self, request, task_id):
        t = self._get_task(task_id, request.user.ngo_id)
        if not t:
            return Response({"detail": "Task not found"}, status=404)
        assignments = Assignment.objects.filter(task_id=task_id, ngo_id=request.user.ngo_id)
        return Response({
            "id": t.id, "ngo_id": t.ngo_id, "title": t.title, "description": t.description,
            "required_skills": t.required_skills, "priority": t.priority, "status": t.status,
            "deadline": t.deadline, "lat": t.lat, "lng": t.lng, "created_at": t.created_at,
            "updated_at": t.updated_at, "urgency_score": t.urgency_score,
            "assignments": [{"id": a.id, "volunteer_id": a.volunteer_id, "status": a.status} for a in assignments],
        })

    def put(self, request, task_id):
        nid = request.user.ngo_id
        t = self._get_task(task_id, nid)
        if not t:
            return Response({"detail": "Task not found"}, status=404)
        s = TaskUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        for field, val in s.validated_data.items():
            setattr(t, field, val)
        t.save()
        return Response({"id": t.id, "title": t.title, "status": t.status, "updated_at": t.updated_at})

    def delete(self, request, task_id):
        nid = request.user.ngo_id
        deleted, _ = Task.objects.filter(id=task_id, ngo_id=nid).delete()
        if not deleted:
            return Response({"detail": "Task not found"}, status=404)
        return Response({"message": "Task deleted"})


class AssignTaskView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request, task_id):
        nid = request.user.ngo_id
        volunteer_id = request.data.get("volunteer_id")
        if not volunteer_id:
            return Response({"detail": "volunteer_id required"}, status=400)
        try:
            task = Task.objects.get(id=task_id, ngo_id=nid)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found"}, status=404)
        if not VolunteerProfile.objects.filter(user_id=volunteer_id, ngo_id=nid).exists():
            return Response({"detail": "Volunteer not in this NGO"}, status=404)
        existing = Assignment.objects.filter(
            task_id=task_id, volunteer_id=volunteer_id, ngo_id=nid
        ).exclude(status="rejected").first()
        if existing:
            return Response({"detail": "Already assigned"}, status=409)
        a = Assignment.objects.create(task_id=task_id, volunteer_id=volunteer_id, ngo_id=nid, status="assigned")
        Notification.objects.create(
            user_id=volunteer_id,
            message=f"You have been assigned to task: {task.title}",
            type="task_assigned",
        )
        return Response({"assignment_id": a.id, "status": a.status}, status=201)


class BulkAssignView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request):
        from asgiref.sync import async_to_sync
        nid = request.user.ngo_id
        max_assignments = request.data.get("max_assignments")
        try:
            from services.assignment_dispatcher import dispatch_optimized_assignments
            results = async_to_sync(dispatch_optimized_assignments)(
                ngo_id=nid, max_assignments=max_assignments
            )
            return Response({"assignments": results, "count": len(results)})
        except Exception as e:
            logger.error("Bulk assign failed: %s", e)
            return Response({"detail": f"Assignment failed: {e}"}, status=500)


# ── Resources ────────────────────────────────────────────────────────────────

class ResourcesView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        resources = Resource.objects.filter(ngo_id=nid)
        return Response([{
            "id": r.id, "ngo_id": r.ngo_id, "type": r.type, "quantity": r.quantity,
            "availability_status": r.availability_status, "metadata": r.metadata,
            "lat": r.lat, "lng": r.lng,
        } for r in resources])

    def post(self, request):
        nid = request.user.ngo_id
        s = ResourceCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        r = Resource.objects.create(ngo_id=nid, type=d["type"], quantity=d["quantity"],
                                    metadata=d.get("metadata",{}), lat=d.get("lat"), lng=d.get("lng"))
        return Response({"id": r.id, "type": r.type, "quantity": r.quantity}, status=201)


class ResourceDetailView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def put(self, request, resource_id):
        nid = request.user.ngo_id
        try:
            r = Resource.objects.get(id=resource_id, ngo_id=nid)
        except Resource.DoesNotExist:
            return Response({"detail": "Resource not found"}, status=404)
        for field in ["type","quantity","availability_status","metadata","lat","lng"]:
            if field in request.data:
                setattr(r, field, request.data[field])
        r.save()
        return Response({"id": r.id, "type": r.type, "quantity": r.quantity,
                         "availability_status": r.availability_status})

    def delete(self, request, resource_id):
        nid = request.user.ngo_id
        deleted, _ = Resource.objects.filter(id=resource_id, ngo_id=nid).delete()
        if not deleted:
            return Response({"detail": "Resource not found"}, status=404)
        return Response({"message": "Resource deleted"})


class AllocateResourceView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request, resource_id):
        nid = request.user.ngo_id
        task_id = request.data.get("task_id")
        if not task_id:
            return Response({"detail": "task_id required"}, status=400)
        try:
            resource = Resource.objects.get(id=resource_id, ngo_id=nid)
        except Resource.DoesNotExist:
            return Response({"detail": "Resource not found"}, status=404)
        if not Task.objects.filter(id=task_id, ngo_id=nid).exists():
            return Response({"detail": "Task not found"}, status=404)
        alloc = Allocation.objects.create(resource_id=resource_id, task_id=task_id,
                                          ngo_id=nid, allocation_status="active")
        resource.availability_status = "in_use"
        resource.save(update_fields=["availability_status"])
        return Response({"allocation_id": alloc.id, "status": alloc.allocation_status}, status=201)


# ── Events ────────────────────────────────────────────────────────────────────

class EventsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        events = Event.objects.filter(ngo_id=nid).order_by("-date")
        return Response([{
            "id": e.id, "title": e.title, "description": e.description,
            "event_type": e.event_type, "date": e.date, "location": e.location,
            "max_volunteers": e.max_volunteers, "status": e.status, "created_at": e.created_at,
        } for e in events])

    def post(self, request):
        nid = request.user.ngo_id
        s = EventCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        e = Event.objects.create(ngo_id=nid, **d)
        return Response({"id": e.id, "title": e.title, "date": e.date}, status=201)


# ── Enrollments ───────────────────────────────────────────────────────────────

class EnrollmentsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        status = request.query_params.get("status", "pending")
        enrollments = TaskEnrollmentRequest.objects.filter(ngo_id=nid, status=status).order_by("-created_at")
        result = []
        for e in enrollments:
            try:
                t = Task.objects.get(id=e.task_id)
                u = User.objects.get(id=e.volunteer_id)
            except (Task.DoesNotExist, User.DoesNotExist):
                continue
            result.append({
                "id": e.id, "task_id": e.task_id, "task_title": t.title,
                "volunteer_id": e.volunteer_id, "volunteer_name": u.full_name,
                "reason": e.reason, "why_useful": e.why_useful,
                "status": e.status, "created_at": e.created_at,
            })
        return Response(result)


class EnrollmentActionView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request, enrollment_id, action):
        nid = request.user.ngo_id
        if action not in ("approve", "reject"):
            return Response({"detail": "Action must be approve or reject"}, status=400)
        try:
            enr = TaskEnrollmentRequest.objects.get(id=enrollment_id, ngo_id=nid)
        except TaskEnrollmentRequest.DoesNotExist:
            return Response({"detail": "Enrollment not found"}, status=404)
        enr.status = "approved" if action == "approve" else "rejected"
        enr.save(update_fields=["status"])
        if action == "approve":
            Assignment.objects.get_or_create(
                task_id=enr.task_id, volunteer_id=enr.volunteer_id,
                ngo_id=nid, defaults={"status": "assigned"}
            )
            try:
                t = Task.objects.get(id=enr.task_id)
                Notification.objects.create(
                    user_id=enr.volunteer_id,
                    message=f"Your enrollment for '{t.title}' was approved!",
                    type="task_assigned",
                )
            except Task.DoesNotExist:
                pass
        return Response({"enrollment_id": enrollment_id, "status": enr.status})


# ── Notifications ─────────────────────────────────────────────────────────────

class NGONotificationsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        notifs = Notification.objects.filter(
            user_id=request.user.user_id
        ).order_by("-created_at")[:50]
        return Response([{
            "id": n.id, "message": n.message, "type": n.type,
            "is_read": n.is_read, "created_at": n.created_at,
        } for n in notifs])

    def patch(self, request, notif_id=None):
        qs = Notification.objects.filter(user_id=request.user.user_id)
        if notif_id:
            qs = qs.filter(id=notif_id)
        qs.update(is_read=True)
        return Response({"message": "Marked as read"})


# ── Analytics ─────────────────────────────────────────────────────────────────

class NGOAnalyticsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        tasks = Task.objects.filter(ngo_id=nid)
        assignments = Assignment.objects.filter(ngo_id=nid)
        return Response({
            "tasks_by_status": {
                "open": tasks.filter(status="open").count(),
                "in_progress": tasks.filter(status="in_progress").count(),
                "completed": tasks.filter(status="completed").count(),
                "cancelled": tasks.filter(status="cancelled").count(),
            },
            "tasks_by_priority": {
                "high": tasks.filter(priority="high").count(),
                "medium": tasks.filter(priority="medium").count(),
                "low": tasks.filter(priority="low").count(),
            },
            "assignments_by_status": {
                "assigned": assignments.filter(status="assigned").count(),
                "accepted": assignments.filter(status="accepted").count(),
                "completed": assignments.filter(status="completed").count(),
                "rejected": assignments.filter(status="rejected").count(),
            },
            "total_volunteers": User.objects.filter(ngo_id=nid, role="volunteer").count(),
            "total_resources": Resource.objects.filter(ngo_id=nid).count(),
        })


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        alerts = []
        high_urgent = Task.objects.filter(ngo_id=nid, priority="high", status__in=["open","in_progress"])
        for t in high_urgent[:5]:
            alerts.append({"type": "high_priority_task", "task_id": t.id, "title": t.title})
        return Response({"alerts": alerts, "count": len(alerts)})


# ── Task ping / complete / ai-match ───────────────────────────────────────────

class PingTaskView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request, task_id):
        nid = request.user.ngo_id
        try:
            task = Task.objects.get(id=task_id, ngo_id=nid)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found"}, status=404)
        message = (request.data.get("message") or f"NGO update on task: {task.title}").strip()
        assignments = list(Assignment.objects.filter(
            task_id=task_id, ngo_id=nid, status__in=["assigned", "accepted"]
        ))
        for a in assignments:
            Notification.objects.create(user_id=a.volunteer_id, message=message, type="general")
        return Response({"count": len(assignments)})


class CompleteTaskView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request, task_id):
        nid = request.user.ngo_id
        try:
            task = Task.objects.get(id=task_id, ngo_id=nid)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found"}, status=404)
        task.status = "completed"
        task.save(update_fields=["status"])
        active = list(Assignment.objects.filter(task_id=task_id, status__in=["assigned", "accepted"]))
        for a in active:
            a.status = "completed"
            a.save(update_fields=["status"])
            Notification.objects.create(
                user_id=a.volunteer_id,
                message=f"Task '{task.title}' has been marked complete",
                type="status_update",
            )
        return Response({"message": "Task completed", "completed_assignments": len(active)})


class AIMatchView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request, task_id):
        from asgiref.sync import async_to_sync
        nid = request.user.ngo_id
        try:
            Task.objects.get(id=task_id, ngo_id=nid)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found"}, status=404)
        try:
            from services.ai_matching import rank_volunteers
            ranked = async_to_sync(rank_volunteers)(task_id, nid)
            return Response({"task_id": task_id, "ranked_volunteers": ranked})
        except Exception as e:
            logger.error("AI match failed: %s", e)
            return Response({"detail": str(e)}, status=500)


# ── Route preview ─────────────────────────────────────────────────────────────

class RoutePreviewView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request):
        from asgiref.sync import async_to_sync
        nid = request.user.ngo_id
        volunteer_id = request.data.get("volunteer_id")
        task_id = request.data.get("task_id")
        if not volunteer_id or not task_id:
            return Response({"detail": "volunteer_id and task_id required"}, status=400)
        try:
            p = VolunteerProfile.objects.get(user_id=volunteer_id, ngo_id=nid)
        except VolunteerProfile.DoesNotExist:
            return Response({"detail": "Volunteer not found"}, status=404)
        if p.lat is None or p.lng is None:
            return Response({"detail": "Volunteer location unavailable"}, status=400)
        try:
            task = Task.objects.get(id=task_id, ngo_id=nid)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found"}, status=404)
        if task.lat is None or task.lng is None:
            return Response({"detail": "Task location unavailable"}, status=400)
        try:
            from services.geo_routing_service import geo_routing_service
            route = async_to_sync(geo_routing_service.get_route)(
                start=(p.lat, p.lng), end=(task.lat, task.lng)
            )
            return Response({"task_id": task_id, "volunteer_id": volunteer_id, **route})
        except Exception as e:
            logger.error("Route preview failed: %s", e)
            return Response({"detail": str(e)}, status=500)


# ── Assignments list ──────────────────────────────────────────────────────────

class AssignmentsListView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        status = request.query_params.get("status")
        qs = Assignment.objects.filter(ngo_id=nid)
        if status:
            qs = qs.filter(status=status)
        qs = qs.order_by("-assigned_at")
        return Response([{
            "id": a.id, "task_id": a.task_id, "volunteer_id": a.volunteer_id,
            "status": a.status, "assigned_at": a.assigned_at,
        } for a in qs])


# ── Event detail / attendance ─────────────────────────────────────────────────

class EventDetailView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def delete(self, request, event_id):
        nid = request.user.ngo_id
        try:
            event = Event.objects.get(id=event_id, ngo_id=nid)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found"}, status=404)
        EventAttendance.objects.filter(event_id=event_id).delete()
        event.delete()
        return Response({"message": "Deleted"})


class EventAttendanceView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request, event_id):
        nid = request.user.ngo_id
        try:
            Event.objects.get(id=event_id, ngo_id=nid)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found"}, status=404)
        volunteers = User.objects.filter(ngo_id=nid, role="volunteer")
        records = {a.volunteer_id: a.status for a in EventAttendance.objects.filter(event_id=event_id)}
        return Response([{
            "volunteer_id": v.id, "email": v.email,
            "status": records.get(v.id, "invited"),
        } for v in volunteers])

    def post(self, request, event_id, vol_id):
        nid = request.user.ngo_id
        try:
            Event.objects.get(id=event_id, ngo_id=nid)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found"}, status=404)
        if not User.objects.filter(id=vol_id, ngo_id=nid, role="volunteer").exists():
            return Response({"detail": "Volunteer not found"}, status=404)
        status = request.data.get("status")
        if status not in ("invited", "present", "absent"):
            return Response({"detail": "status must be invited, present, or absent"}, status=400)
        attendance, _ = EventAttendance.objects.update_or_create(
            event_id=event_id, volunteer_id=vol_id,
            defaults={"status": status},
        )
        return Response({"volunteer_id": vol_id, "status": attendance.status})


# ── Volunteer live locations ──────────────────────────────────────────────────

class VolunteerLocationsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        profiles = list(VolunteerProfile.objects.filter(
            ngo_id=nid, share_location=True, lat__isnull=False, lng__isnull=False
        ))
        user_map = {
            u["id"]: u
            for u in User.objects.filter(
                id__in=[p.user_id for p in profiles]
            ).values("id", "email")
        }
        result = []
        for p in profiles:
            u = user_map.get(p.user_id)
            if not u:
                continue
            result.append({
                "id": p.id, "user_id": p.user_id, "email": u["email"],
                "lat": p.lat, "lng": p.lng,
                "skills": p.skills, "availability": p.availability, "status": p.status,
            })
        return Response(result)


# ── NGO notification mark-read ────────────────────────────────────────────────

class NotificationReadView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request, notif_id):
        n = Notification.objects.filter(id=notif_id, user_id=request.user.user_id).first()
        if not n:
            return Response({"detail": "Notification not found"}, status=404)
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response({"id": n.id, "is_read": True})


class NotificationReadAllView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdminWithNGO]

    def post(self, request):
        count = Notification.objects.filter(
            user_id=request.user.user_id, is_read=False
        ).update(is_read=True)
        return Response({"marked": count})

