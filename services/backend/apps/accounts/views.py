import random
import string
import logging
from datetime import timedelta
from django.utils import timezone as dj_tz

from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.accounts.models import User, NGO, VolunteerProfile, ConsentEvent
from apps.ngo.models import Task, Assignment, Event, Resource, Notification
from apps.core.auth_utils import hash_password, verify_password, create_token
from apps.core.authentication import SynapseJWTAuthentication
from apps.core.permissions import IsNGOAdmin
from apps.accounts.serializers import (
    SignupSerializer, LoginSerializer, GoogleAuthSerializer, NGOCreateSerializer,
)

logger = logging.getLogger(__name__)


def _random_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _record_consent_events(user_id: str, data: dict) -> None:
    ConsentEvent.objects.create(user_id=user_id, scope="analytics",
                                granted=data.get("consent_analytics", True), source="signup")
    ConsentEvent.objects.create(user_id=user_id, scope="personalization",
                                granted=data.get("consent_personalization", True), source="signup")
    ConsentEvent.objects.create(user_id=user_id, scope="ai_training",
                                granted=data.get("consent_ai_training", False), source="signup")


def _seed_ngo_demo_data(admin_user_id: str, ngo_id: str) -> None:
    now = dj_tz.now()
    vol_specs = [
        ("Amit Kumar",   "amit",  ["medical_aid", "search_rescue"],          "Mumbai",    4),
        ("Priya Sharma", "priya", ["logistics", "water_purification"],        "Delhi",     3),
        ("Rahul Singh",  "rahul", ["logistics", "community_outreach"],        "Pune",      6),
        ("Meera Patel",  "meera", ["medical_aid", "teaching"],                "Bangalore", 2),
        ("Arjun Nair",   "arjun", ["search_rescue", "structural_assessment"], "Chennai",   5),
    ]
    import uuid
    volunteer_ids = []
    for name, sfx, skills, city, yrs in vol_specs:
        vu = User.objects.create(
            email=f"demo_{sfx}_{ngo_id[:6]}@guest.hackathon",
            password_hash=hash_password("demo123"),
            role="volunteer", ngo_id=ngo_id,
            full_name=name, profile_completed_at=now,
        )
        VolunteerProfile.objects.create(
            user_id=vu.id, ngo_id=ngo_id, skills=skills,
            availability={"mon":True,"tue":True,"wed":True,"thu":True,"fri":True,"sat":False,"sun":False},
            full_name=name, city=city, languages=["English","Hindi"],
            causes_supported=["Disaster Relief","Healthcare"],
            bio=f"Dedicated volunteer. Highly reliable.",
            years_experience=yrs, profile_completeness_score=0.85,
        )
        volunteer_ids.append(vu.id)

    task_specs = [
        ("Flood Relief — Food Distribution", "Distribute food packets.", ["logistics","community_outreach"], "high", "open", 3, 19.040, 72.854),
        ("Medical Camp Setup", "Set up emergency triage camp.", ["medical_aid"], "high", "in_progress", 2, 19.076, 72.877),
        ("Drinking Water Distribution", "Distribute purified water.", ["logistics","water_purification"], "medium", "open", 1, 19.052, 72.852),
        ("Rescue Operations — Rooftop", "Rescue stranded persons.", ["search_rescue"], "high", "in_progress", 1, 19.062, 72.833),
        ("Temporary Shelter Construction", "Build shelters.", ["structural_assessment"], "high", "completed", -3, 19.035, 72.849),
        ("Flood Safety Awareness Drive", "Safety sessions.", ["teaching","community_outreach"], "low", "open", 7, 19.048, 72.862),
        ("Damage Assessment Survey", "Survey households.", ["community_outreach"], "medium", "in_progress", 4, 19.057, 72.841),
        ("Medical Supply Convoy", "Distribute medical supplies.", ["medical_aid","logistics"], "high", "open", 2, 19.069, 72.869),
    ]
    task_ids = []
    for title, desc, skills, priority, status, days, lat, lng in task_specs:
        t = Task.objects.create(
            ngo_id=ngo_id, title=title, description=desc,
            required_skills=skills, priority=priority, status=status,
            deadline=now + timedelta(days=days), lat=lat, lng=lng,
            urgency_score=90 if priority=="high" else 55,
        )
        task_ids.append(t.id)

    assign_specs = [(0,0,"accepted"),(1,1,"accepted"),(2,2,"assigned"),(3,3,"accepted"),
                    (4,4,"completed"),(5,0,"assigned"),(6,1,"accepted"),(7,2,"assigned")]
    for ti, vi, status in assign_specs:
        a = Assignment.objects.create(
            task_id=task_ids[ti], volunteer_id=volunteer_ids[vi], ngo_id=ngo_id, status=status)
        if status == "completed":
            a.accepted_at = now - timedelta(days=4)
            a.completed_at = now - timedelta(days=2)
            a.save(update_fields=["accepted_at","completed_at"])
        elif status == "accepted":
            a.accepted_at = now - timedelta(hours=random.randint(2,48))
            a.save(update_fields=["accepted_at"])

    for title, desc, etype, days, location, maxv in [
        ("Flood Relief Mega Drive","Large-scale relief.","drive",7,"Dharavi, Mumbai",100),
        ("Medical Awareness & Free Camp","Free checkups.","camp",4,"Kurla East, Mumbai",50),
        ("Volunteer First Aid Training","First-aid certification.","training",14,"NGO HQ",30),
        ("Environmental Cleanup Drive","Post-flood cleanup.","drive",21,"Bandra West, Mumbai",80),
    ]:
        Event.objects.create(ngo_id=ngo_id, title=title, description=desc,
                             event_type=etype, date=now+timedelta(days=days),
                             location=location, max_volunteers=maxv, status="upcoming")

    for rtype, qty, rstatus in [
        ("Medical Kits",50,"available"),("Water Purification Tablets",200,"available"),
        ("Food Packages",150,"in_use"),("Rescue Boats",8,"in_use"),
        ("Temporary Shelters",25,"available"),("First Aid Boxes",40,"available"),
    ]:
        Resource.objects.create(ngo_id=ngo_id, type=rtype, quantity=qty, availability_status=rstatus)

    for msg, ntype in [
        ("Priya Sharma accepted the Drinking Water Distribution task.","status_update"),
        ("New volunteer joined your NGO: Meera Patel.","general"),
        ("Task Medical Camp Setup is 80% complete.","status_update"),
        ("Resource alert: Food Packages running low.","general"),
        ("Upcoming event: Flood Relief Mega Drive in 7 days.","general"),
        ("Rahul Singh completed Temporary Shelter Construction.","status_update"),
    ]:
        Notification.objects.create(user_id=admin_user_id, message=msg, type=ntype)


def _seed_volunteer_demo_data(vol_user_id: str, ngo_id: str) -> None:
    now = dj_tz.now()

    open_task_specs = [
        ("Flood Relief — Food Distribution","Distribute food packets.",["logistics"],"high",1,19.040,72.854),
        ("Medical Supply Convoy","Escort medical supplies.",["medical_aid"],"high",2,19.069,72.869),
        ("Flood Safety Awareness Drive","Safety sessions.",["teaching"],"low",5,19.048,72.862),
        ("Community Kitchen Volunteer","Cook and serve meals.",["cooking"],"medium",3,19.055,72.845),
        ("Water Distribution — Zone 4","Distribute water.",["logistics"],"medium",2,19.061,72.858),
    ]
    for title, desc, skills, priority, days, lat, lng in open_task_specs:
        Task.objects.create(ngo_id=ngo_id, title=title, description=desc,
                            required_skills=skills, priority=priority, status="open",
                            deadline=now+timedelta(days=days), lat=lat, lng=lng,
                            urgency_score=88 if priority=="high" else 55)

    for title, desc, skills, priority, status, days, lat, lng in [
        ("Rescue Operations — Rooftop","Rescue stranded persons.",["search_rescue"],"high","accepted",1,19.062,72.833),
        ("Damage Assessment Survey","Survey households.",["community_outreach"],"medium","assigned",3,19.057,72.841),
        ("Temporary Shelter Construction","Build shelters.",["structural_assessment"],"high","completed",-2,19.035,72.849),
    ]:
        t = Task.objects.create(ngo_id=ngo_id, title=title, description=desc,
                                required_skills=skills, priority=priority,
                                status="in_progress" if status!="completed" else "completed",
                                deadline=now+timedelta(days=days), lat=lat, lng=lng,
                                urgency_score=85 if priority=="high" else 50)
        a = Assignment.objects.create(task_id=t.id, volunteer_id=vol_user_id, ngo_id=ngo_id, status=status)
        if status == "completed":
            a.accepted_at = now - timedelta(days=3)
            a.completed_at = now - timedelta(days=2)
            a.save(update_fields=["accepted_at","completed_at"])
        elif status == "accepted":
            a.accepted_at = now - timedelta(hours=6)
            a.save(update_fields=["accepted_at"])

    for msg, ntype in [
        ("You have been assigned: Rescue Operations — Rooftop.","task_assigned"),
        ("Your task Temporary Shelter Construction was verified.","status_update"),
        ("Upcoming event: Flood Relief Mega Drive in 7 days.","general"),
        ("Your profile is 85% complete.","general"),
    ]:
        Notification.objects.create(user_id=vol_user_id, message=msg, type=ntype)


class SignupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = SignupSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        existing = User.objects.filter(email=d["email"]).first()
        if existing:
            role_label = "NGO Admin" if existing.role == "ngo_admin" else "Volunteer"
            if existing.role != d["role"]:
                return Response(
                    {"detail": f"This email is already registered as a {role_label} account. Please use the {role_label} sign-in button."},
                    status=409,
                )
            return Response({"detail": "Email already registered"}, status=409)

        if d["role"] == "volunteer":
            if not d.get("invite_code"):
                return Response({"detail": "invite_code required for volunteers"}, status=400)
            try:
                ngo = NGO.objects.get(invite_code=d["invite_code"])
            except NGO.DoesNotExist:
                return Response({"detail": "Invalid invite code"}, status=404)

            user = User.objects.create(
                email=d["email"], password_hash=hash_password(d["password"]),
                role="volunteer", ngo_id=ngo.id, full_name=d.get("full_name"),
                phone=d.get("phone"), preferred_language=d.get("preferred_language","en"),
                communication_opt_in=d.get("communication_opt_in",True),
                consent_analytics=d.get("consent_analytics",True),
                consent_personalization=d.get("consent_personalization",True),
                consent_ai_training=d.get("consent_ai_training",False),
                profile_completed_at=dj_tz.now() if d.get("full_name") and d.get("phone") else None,
            )
            VolunteerProfile.objects.create(
                user_id=user.id, ngo_id=ngo.id, skills=d.get("skills",[]),
                availability={"mon":True,"tue":True,"wed":True,"thu":True,"fri":True,"sat":False,"sun":False},
                full_name=d.get("full_name"), phone=d.get("phone"), city=d.get("city"),
                motivation_statement=d.get("motivation_statement"),
                languages=d.get("languages",[]), causes_supported=d.get("causes_supported",[]),
                education_level=d.get("education_level"), years_experience=d.get("years_experience"),
                bio=d.get("bio"), date_of_birth=d.get("date_of_birth"),
                emergency_contact_name=d.get("emergency_contact_name"),
                emergency_contact_phone=d.get("emergency_contact_phone"),
                preferred_roles=d.get("preferred_roles",[]),
                certifications=d.get("certifications",[]),
                availability_notes=d.get("availability_notes"),
            )
            _record_consent_events(user.id, d)
            token = create_token(user.id, "volunteer", ngo.id, d["email"])
            return Response({"token": token, "role": "volunteer", "ngo_id": ngo.id, "ngo_name": ngo.name})

        # ngo_admin
        user = User.objects.create(
            email=d["email"], password_hash=hash_password(d["password"]),
            role="ngo_admin", ngo_id=None, full_name=d.get("full_name"),
            phone=d.get("phone"), preferred_language=d.get("preferred_language","en"),
            communication_opt_in=d.get("communication_opt_in",True),
            consent_analytics=d.get("consent_analytics",True),
            consent_personalization=d.get("consent_personalization",True),
            consent_ai_training=d.get("consent_ai_training",False),
        )
        _record_consent_events(user.id, d)
        token = create_token(user.id, "ngo_admin", None, d["email"])
        return Response({"token": token, "role": "ngo_admin", "ngo_id": None, "needs_ngo_setup": True})


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            user = User.objects.get(email=d["email"])
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=401)
        if not user.password_hash or not verify_password(d["password"], user.password_hash):
            return Response({"detail": "Invalid credentials"}, status=401)
        user.last_login_at = dj_tz.now()
        user.save(update_fields=["last_login_at"])
        token = create_token(user.id, user.role, user.ngo_id, user.email)
        return Response({
            "token": token, "role": user.role, "ngo_id": user.ngo_id,
            "needs_ngo_setup": user.role == "ngo_admin" and not user.ngo_id,
        })


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = GoogleAuthSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            user = User.objects.get(email=d["email"])
            if user.role != d["role"]:
                role_label = "NGO Admin" if user.role == "ngo_admin" else "Volunteer"
                return Response(
                    {"detail": f"This email is already registered as a {role_label} account. Please use the {role_label} sign-in button."},
                    status=409,
                )
            user.last_login_at = dj_tz.now()
            user.save(update_fields=["last_login_at"])
            token = create_token(user.id, user.role, user.ngo_id, user.email)
            return Response({
                "token": token, "role": user.role, "ngo_id": user.ngo_id,
                "needs_ngo_setup": user.role == "ngo_admin" and not user.ngo_id,
            })
        except User.DoesNotExist:
            pass

        if d["role"] == "volunteer":
            if not d.get("invite_code"):
                return Response({"detail": "invite_code required for volunteers"}, status=400)
            try:
                ngo = NGO.objects.get(invite_code=d["invite_code"])
            except NGO.DoesNotExist:
                return Response({"detail": "Invalid invite code"}, status=404)
            try:
                user = User.objects.create(
                    email=d["email"], password_hash=None, role="volunteer", ngo_id=ngo.id,
                    full_name=d.get("full_name"), phone=d.get("phone"),
                    preferred_language=d.get("preferred_language","en"),
                    communication_opt_in=d.get("communication_opt_in",True),
                    consent_analytics=d.get("consent_analytics",True),
                    consent_personalization=d.get("consent_personalization",True),
                    consent_ai_training=d.get("consent_ai_training",False),
                    profile_completed_at=dj_tz.now() if d.get("full_name") and d.get("phone") else None,
                )
                VolunteerProfile.objects.create(
                    user_id=user.id, ngo_id=ngo.id, skills=d.get("skills",[]),
                    availability={"mon":True,"tue":True,"wed":True,"thu":True,"fri":True,"sat":False,"sun":False},
                    full_name=d.get("full_name"), phone=d.get("phone"), city=d.get("city"),
                    motivation_statement=d.get("motivation_statement"),
                    languages=d.get("languages",[]), causes_supported=d.get("causes_supported",[]),
                    education_level=d.get("education_level"), years_experience=d.get("years_experience"),
                    bio=d.get("bio"), date_of_birth=d.get("date_of_birth"),
                    preferred_roles=d.get("preferred_roles",[]), certifications=d.get("certifications",[]),
                )
                _record_consent_events(user.id, d)
                token = create_token(user.id, "volunteer", ngo.id, d["email"])
                return Response({"token": token, "role": "volunteer", "ngo_id": ngo.id, "ngo_name": ngo.name})
            except IntegrityError:
                try:
                    user = User.objects.get(email=d["email"])
                    if user.role != d["role"]:
                        role_label = "NGO Admin" if user.role == "ngo_admin" else "Volunteer"
                        return Response(
                            {"detail": f"This email is already registered as a {role_label} account. Please use the {role_label} sign-in button."},
                            status=409,
                        )
                    token = create_token(user.id, user.role, user.ngo_id, user.email)
                    return Response({"token": token, "role": user.role, "ngo_id": user.ngo_id})
                except User.DoesNotExist:
                    return Response({"detail": "Registration conflict"}, status=409)

        try:
            user = User.objects.create(
                email=d["email"], password_hash=None, role="ngo_admin", ngo_id=None,
                full_name=d.get("full_name"), phone=d.get("phone"),
                preferred_language=d.get("preferred_language","en"),
                communication_opt_in=d.get("communication_opt_in",True),
                consent_analytics=d.get("consent_analytics",True),
                consent_personalization=d.get("consent_personalization",True),
                consent_ai_training=d.get("consent_ai_training",False),
            )
            _record_consent_events(user.id, d)
            token = create_token(user.id, "ngo_admin", None, d["email"])
            return Response({"token": token, "role": "ngo_admin", "ngo_id": None, "needs_ngo_setup": True})
        except IntegrityError:
            try:
                user = User.objects.get(email=d["email"])
                if user.role != d["role"]:
                    role_label = "NGO Admin" if user.role == "ngo_admin" else "Volunteer"
                    return Response(
                        {"detail": f"This email is already registered as a {role_label} account. Please use the {role_label} sign-in button."},
                        status=409,
                    )
                token = create_token(user.id, user.role, user.ngo_id, user.email)
                return Response({"token": token, "role": user.role, "ngo_id": user.ngo_id,
                                 "needs_ngo_setup": user.role=="ngo_admin" and not user.ngo_id})
            except User.DoesNotExist:
                return Response({"detail": "Registration conflict"}, status=409)


class GuestLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        guest_email = f"guest_{unique_suffix}@synapseai.hackathon"
        user = User.objects.create(
            email=guest_email, password_hash=hash_password("guest_password123"),
            role="ngo_admin", ngo_id=None, full_name="Hackathon Guest",
            phone="555-0000", profile_completed_at=dj_tz.now(),
        )
        code = _random_code()
        while NGO.objects.filter(invite_code=code).exists():
            code = _random_code()
        ngo = NGO.objects.create(
            name=f"Guest NGO {unique_suffix}", description="Auto-generated NGO for hackathon guest.",
            invite_code=code, created_by=user.id, sector="Hackathon",
        )
        user.ngo_id = ngo.id
        user.save(update_fields=["ngo_id"])
        for scope, granted in [("analytics",True),("personalization",True),("ai_training",True)]:
            ConsentEvent.objects.create(user_id=user.id, scope=scope, granted=granted, source="guest")
        _seed_ngo_demo_data(user.id, ngo.id)
        token = create_token(user.id, "ngo_admin", ngo.id, guest_email)
        return Response({"token": token, "role": "ngo_admin", "ngo_id": ngo.id, "ngo_name": ngo.name})


class GuestVolunteerLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        guest_email = f"vol_guest_{unique_suffix}@synapseai.hackathon"
        vol_user = User.objects.create(
            email=guest_email, password_hash=hash_password("guest_password123"),
            role="volunteer", ngo_id=None, full_name="Demo Volunteer",
            phone="+919876543210", profile_completed_at=dj_tz.now(),
        )
        code = _random_code()
        while NGO.objects.filter(invite_code=code).exists():
            code = _random_code()
        ngo = NGO.objects.create(
            name=f"Demo Relief NGO {unique_suffix}", description="Hackathon demo NGO.",
            invite_code=code, created_by=vol_user.id, sector="Disaster Relief",
            headquarters_city="Mumbai",
        )
        vol_user.ngo_id = ngo.id
        vol_user.save(update_fields=["ngo_id"])
        VolunteerProfile.objects.create(
            user_id=vol_user.id, ngo_id=ngo.id,
            skills=["search_rescue","first_aid","logistics"],
            availability={"mon":True,"tue":True,"wed":True,"thu":True,"fri":True,"sat":False,"sun":False},
            full_name="Demo Volunteer", city="Mumbai",
            languages=["English","Hindi"], causes_supported=["Disaster Relief","Healthcare"],
            bio="Passionate volunteer.", years_experience=2,
            education_level="undergraduate", certifications=["First Aid","CPR"],
            profile_completeness_score=0.85,
        )
        for scope, granted in [("analytics",True),("personalization",True),("ai_training",True)]:
            ConsentEvent.objects.create(user_id=vol_user.id, scope=scope, granted=granted, source="guest")
        _seed_volunteer_demo_data(vol_user.id, ngo.id)
        token = create_token(vol_user.id, "volunteer", ngo.id, guest_email)
        return Response({"token": token, "role": "volunteer", "ngo_id": ngo.id, "ngo_name": ngo.name})


class NGOCreateView(APIView):
    authentication_classes = [SynapseJWTAuthentication]
    permission_classes = [IsNGOAdmin]

    def post(self, request):
        user = request.user
        if user.ngo_id:
            return Response({"detail": "NGO already created for this account"}, status=400)
        s = NGOCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        code = _random_code()
        while NGO.objects.filter(invite_code=code).exists():
            code = _random_code()
        ngo = NGO.objects.create(
            name=d["name"], description=d.get("description",""),
            invite_code=code, created_by=user.user_id,
            sector=d.get("sector"), website=d.get("website"),
            headquarters_city=d.get("headquarters_city"),
            primary_contact_name=d.get("primary_contact_name"),
            primary_contact_phone=d.get("primary_contact_phone"),
            operating_regions=d.get("operating_regions",[]),
            mission_focus=d.get("mission_focus",[]),
        )
        User.objects.filter(id=user.user_id).update(ngo_id=ngo.id)
        token = create_token(user.user_id, "ngo_admin", ngo.id, user.email)
        return Response({"token": token, "role": "ngo_admin", "ngo_id": ngo.id,
                         "invite_code": code, "ngo_name": ngo.name})


class CheckEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        email = request.query_params.get("email", "")
        try:
            user = User.objects.get(email=email)
            return Response({"exists": True, "role": user.role})
        except User.DoesNotExist:
            return Response({"exists": False, "role": None})


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        return Response({"message": "Logged out — delete token client-side"})


class NGOLookupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, invite_code):
        try:
            ngo = NGO.objects.get(invite_code=invite_code.upper())
            return Response({"ngo_name": ngo.name, "invite_code": ngo.invite_code})
        except NGO.DoesNotExist:
            return Response({"detail": "Invalid invite code"}, status=404)
