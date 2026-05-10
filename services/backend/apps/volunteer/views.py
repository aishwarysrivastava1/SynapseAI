import logging
import os
from datetime import datetime, timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from apps.accounts.models import User, VolunteerProfile
from apps.ngo.models import Task, Assignment, Notification, TaskEnrollmentRequest
from apps.core.authentication import SynapseJWTAuthentication
from apps.core.permissions import IsVolunteerWithNGO

logger = logging.getLogger(__name__)
ENABLE_DYNAMIC_REASSIGNMENT = os.getenv("ENABLE_DYNAMIC_REASSIGNMENT","true").lower()=="true"
REASSIGNMENT_MOVE_THRESHOLD_KM = float(os.getenv("REASSIGNMENT_MOVE_THRESHOLD_KM","0.2"))


class ProfileUpdateSerializer(serializers.Serializer):
    skills = serializers.ListField(child=serializers.CharField(), required=False)
    availability = serializers.DictField(required=False)
    full_name = serializers.CharField(required=False, max_length=200)
    phone = serializers.CharField(required=False, max_length=30)
    city = serializers.CharField(required=False, max_length=100)
    bio = serializers.CharField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    emergency_contact_name = serializers.CharField(required=False, allow_null=True, max_length=200)
    emergency_contact_phone = serializers.CharField(required=False, allow_null=True, max_length=30)
    education_level = serializers.CharField(required=False, allow_null=True, max_length=80)
    years_experience = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=80)
    preferred_roles = serializers.ListField(child=serializers.CharField(), required=False)
    certifications = serializers.ListField(child=serializers.CharField(), required=False)
    languages = serializers.ListField(child=serializers.CharField(), required=False)
    causes_supported = serializers.ListField(child=serializers.CharField(), required=False)
    motivation_statement = serializers.CharField(required=False, allow_null=True, max_length=2000)
    availability_notes = serializers.CharField(required=False, allow_null=True, max_length=1200)


class EnrollSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=10, max_length=2000)
    why_useful = serializers.CharField(min_length=10, max_length=2000)


class LocationUpdateSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    share_location = serializers.BooleanField(default=True)


class VolDashboardView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def get(self, request):
        uid = request.user.user_id
        nid = request.user.ngo_id
        active = Assignment.objects.filter(volunteer_id=uid, ngo_id=nid, status__in=["assigned","accepted"]).count()
        completed = Assignment.objects.filter(volunteer_id=uid, ngo_id=nid, status="completed").count()
        unread = Notification.objects.filter(user_id=uid, is_read=False).count()
        upcoming = []
        for a in Assignment.objects.filter(volunteer_id=uid, ngo_id=nid, status__in=["assigned","accepted"]).select_related()[:5]:
            try:
                t = Task.objects.get(id=a.task_id)
                if t.deadline:
                    upcoming.append({"task_id": t.id, "title": t.title, "deadline": t.deadline, "assignment_status": a.status})
            except Task.DoesNotExist:
                pass
        return Response({
            "active_assignments": active, "completed_tasks": completed,
            "unread_notifications": unread, "upcoming_deadlines": upcoming,
        })


class VolTasksView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def get(self, request):
        uid = request.user.user_id
        nid = request.user.ngo_id
        assignments = Assignment.objects.filter(volunteer_id=uid, ngo_id=nid).order_by("-assigned_at")
        result = []
        for a in assignments:
            try:
                t = Task.objects.get(id=a.task_id)
                result.append({
                    "assignment_id": a.id, "task_id": t.id, "title": t.title,
                    "description": t.description, "required_skills": t.required_skills,
                    "priority": t.priority, "task_status": t.status, "assignment_status": a.status,
                    "deadline": t.deadline, "lat": t.lat, "lng": t.lng,
                    "assigned_at": a.assigned_at, "accepted_at": a.accepted_at, "completed_at": a.completed_at,
                })
            except Task.DoesNotExist:
                pass
        return Response(result)


class VolOpenTasksView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def get(self, request):
        nid = request.user.ngo_id
        uid = request.user.user_id
        assigned_task_ids = set(Assignment.objects.filter(
            volunteer_id=uid, ngo_id=nid
        ).exclude(status="rejected").values_list("task_id", flat=True))
        tasks = Task.objects.filter(ngo_id=nid, status="open").exclude(id__in=assigned_task_ids).order_by("-urgency_score")
        return Response([{
            "id": t.id, "title": t.title, "description": t.description,
            "required_skills": t.required_skills, "priority": t.priority,
            "deadline": t.deadline, "lat": t.lat, "lng": t.lng, "urgency_score": t.urgency_score,
        } for t in tasks])


class VolEnrollView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def post(self, request, task_id):
        nid = request.user.ngo_id
        uid = request.user.user_id
        s = EnrollSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            task = Task.objects.get(id=task_id, ngo_id=nid, status="open")
        except Task.DoesNotExist:
            return Response({"detail": "Task not found or not open"}, status=404)
        if TaskEnrollmentRequest.objects.filter(task_id=task_id, volunteer_id=uid, ngo_id=nid).exists():
            return Response({"detail": "Already enrolled"}, status=409)
        enr = TaskEnrollmentRequest.objects.create(
            task_id=task_id, volunteer_id=uid, ngo_id=nid,
            reason=d["reason"], why_useful=d["why_useful"], status="pending",
        )
        return Response({"enrollment_id": enr.id, "status": enr.status}, status=201)


class VolAssignmentActionView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def post(self, request, assignment_id, action):
        uid = request.user.user_id
        nid = request.user.ngo_id
        if action not in ("accept","reject","complete"):
            return Response({"detail": "Invalid action"}, status=400)
        try:
            a = Assignment.objects.get(id=assignment_id, volunteer_id=uid, ngo_id=nid)
        except Assignment.DoesNotExist:
            return Response({"detail": "Assignment not found"}, status=404)
        if action == "accept":
            a.status = "accepted"
            a.accepted_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        elif action == "reject":
            a.status = "rejected"
        elif action == "complete":
            if a.status != "accepted":
                return Response({"detail": "Assignment must be accepted before completing"}, status=400)
            a.status = "completed"
            a.completed_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
            hours = request.data.get("hours_spent")
            if hours:
                a.hours_spent = hours
            try:
                t = Task.objects.get(id=a.task_id)
                t.status = "completed"
                t.save(update_fields=["status"])
            except Task.DoesNotExist:
                pass
        a.save()
        return Response({"assignment_id": a.id, "status": a.status})


class VolProfileView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def get(self, request):
        uid = request.user.user_id
        nid = request.user.ngo_id
        try:
            p = VolunteerProfile.objects.get(user_id=uid, ngo_id=nid)
        except VolunteerProfile.DoesNotExist:
            return Response({"detail": "Profile not found"}, status=404)
        completed = Assignment.objects.filter(volunteer_id=uid, ngo_id=nid, status="completed").count()
        total = Assignment.objects.filter(volunteer_id=uid, ngo_id=nid).count()
        return Response({
            "id": p.id, "user_id": p.user_id, "ngo_id": p.ngo_id,
            "skills": p.skills, "availability": p.availability, "status": p.status,
            "full_name": p.full_name, "phone": p.phone, "city": p.city, "bio": p.bio,
            "education_level": p.education_level, "years_experience": p.years_experience,
            "languages": p.languages, "causes_supported": p.causes_supported,
            "certifications": p.certifications, "preferred_roles": p.preferred_roles,
            "profile_completeness_score": p.profile_completeness_score,
            "completed_tasks": completed, "total_assigned": total,
            "acceptance_rate": completed/total if total > 0 else 0.0,
        })

    def put(self, request):
        uid = request.user.user_id
        nid = request.user.ngo_id
        s = ProfileUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        updated = s.validated_data
        VolunteerProfile.objects.filter(user_id=uid, ngo_id=nid).update(**updated)
        return Response({"message": "Profile updated"})


class VolLocationView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def post(self, request):
        from asgiref.sync import async_to_sync
        uid = request.user.user_id
        nid = request.user.ngo_id
        s = LocationUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            from services.live_location_cache import live_location_cache
            async_to_sync(live_location_cache.update)(
                volunteer_id=uid, lat=d["lat"], lng=d["lng"], share_location=d["share_location"]
            )
        except Exception as e:
            logger.warning("Location cache update failed: %s", e)
        VolunteerProfile.objects.filter(user_id=uid, ngo_id=nid).update(
            lat=d["lat"], lng=d["lng"], share_location=d["share_location"]
        )
        return Response({"message": "Location updated"})

    def delete(self, request):
        from asgiref.sync import async_to_sync
        uid = request.user.user_id
        nid = request.user.ngo_id
        VolunteerProfile.objects.filter(user_id=uid, ngo_id=nid).update(
            lat=None, lng=None, share_location=False
        )
        try:
            from services.live_location_cache import live_location_cache
            async_to_sync(live_location_cache.update)(
                volunteer_id=uid, lat=None, lng=None, share_location=False
            )
        except Exception as e:
            logger.warning("Location cache clear failed: %s", e)
        return Response({"share_location": False})


class VolNotificationsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def get(self, request):
        notifs = Notification.objects.filter(user_id=request.user.user_id).order_by("-created_at")[:50]
        return Response([{
            "id": n.id, "message": n.message, "type": n.type,
            "is_read": n.is_read, "created_at": n.created_at,
        } for n in notifs])

    def patch(self, request):
        Notification.objects.filter(user_id=request.user.user_id).update(is_read=True)
        return Response({"message": "All notifications marked as read"})


class VolAssignmentsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def get(self, request):
        uid = request.user.user_id
        nid = request.user.ngo_id
        assignments = Assignment.objects.filter(volunteer_id=uid, ngo_id=nid).order_by("-assigned_at")
        return Response([{
            "id": a.id, "task_id": a.task_id, "status": a.status, "assigned_at": a.assigned_at,
        } for a in assignments])


class VolRecommendationsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def get(self, request):
        uid = request.user.user_id
        nid = request.user.ngo_id
        try:
            p = VolunteerProfile.objects.get(user_id=uid, ngo_id=nid)
            vol_skills = {s.lower() for s in (p.skills or [])}
        except VolunteerProfile.DoesNotExist:
            vol_skills = set()
        open_tasks = Task.objects.filter(ngo_id=nid, status="open")
        results = []
        for t in open_tasks:
            required = t.required_skills or []
            matched = [s for s in required if s.lower() in vol_skills]
            score = len(matched) / max(len(required), 1)
            results.append({
                "task_id": t.id, "title": t.title, "description": t.description,
                "required_skills": required, "deadline": t.deadline, "priority": t.priority,
                "match_score": round(score, 3), "matched_skills": matched,
            })
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return Response(results[:5])


class VolLocationClearView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def delete(self, request):
        uid = request.user.user_id
        nid = request.user.ngo_id
        VolunteerProfile.objects.filter(user_id=uid, ngo_id=nid).update(
            lat=None, lng=None, share_location=False
        )
        try:
            from services.live_location_cache import live_location_cache
            from asgiref.sync import async_to_sync
            async_to_sync(live_location_cache.update)(
                volunteer_id=uid, lat=None, lng=None, share_location=False
            )
        except Exception as e:
            logger.warning("Location cache clear failed: %s", e)
        return Response({"share_location": False})


class VolSOSView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def post(self, request):
        from asgiref.sync import async_to_sync
        from datetime import timezone as tz
        uid = request.user.user_id
        nid = request.user.ngo_id
        message = (request.data.get("message") or "Volunteer triggered SOS").strip()
        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if lat is None or lng is None:
            try:
                p = VolunteerProfile.objects.get(user_id=uid, ngo_id=nid)
                lat = lat if lat is not None else p.lat
                lng = lng if lng is not None else p.lng
            except VolunteerProfile.DoesNotExist:
                pass
        admins = list(User.objects.filter(ngo_id=nid, role="ngo_admin"))
        for admin in admins:
            Notification.objects.create(
                user_id=admin.id,
                message=f"SOS from {request.user.email}: {message}",
                type="urgent",
            )
        try:
            from services.realtime_events import realtime_bus
            async_to_sync(realtime_bus.publish)(
                nid, "sos_alert", {
                    "volunteer_id": uid, "email": request.user.email,
                    "message": message, "lat": lat, "lng": lng,
                    "created_at": datetime.now(tz=timezone.utc).isoformat() + "Z",
                }
            )
        except Exception as e:
            logger.warning("SOS realtime publish failed: %s", e)
        return Response({"status": "sent", "notified": len(admins)})


class VolEnrollmentRequestsView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def get(self, request):
        uid = request.user.user_id
        enrollments = TaskEnrollmentRequest.objects.filter(volunteer_id=uid).order_by("-created_at")
        result = []
        for e in enrollments:
            try:
                t = Task.objects.get(id=e.task_id)
                title = t.title
            except Task.DoesNotExist:
                title = None
            result.append({
                "id": e.id, "task_id": e.task_id, "task_title": title,
                "reason": e.reason, "why_useful": e.why_useful,
                "status": e.status, "created_at": e.created_at,
            })
        return Response(result)


class VolNotificationReadView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsVolunteerWithNGO]

    def post(self, request, notif_id):
        n = Notification.objects.filter(id=notif_id, user_id=request.user.user_id).first()
        if not n:
            return Response({"detail": "Notification not found"}, status=404)
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response({"id": n.id, "is_read": True})
