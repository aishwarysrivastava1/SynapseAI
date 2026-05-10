import secrets
import string
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta, timezone

def _now() -> datetime:
    """Return current UTC time as a naive datetime (matches DB storage convention)."""
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)

from api.schemas import AuthResponse
from db.base import get_db
from db.models import (
    User, NGO, VolunteerProfile, ConsentEvent,
    Task, Assignment, Event, Resource, Notification,
)
from utils.auth_utils import hash_password, verify_password, create_token
from utils.errors import safe_http_error
from middleware.rbac import get_current_user, CurrentUser

router = APIRouter()


def _random_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _seed_ngo_demo_data(admin_user_id: str, ngo_id: str, db: AsyncSession) -> None:
    """Seed realistic mock data for a guest NGO admin demo session."""
    now = _now()

    # ── 5 volunteer users + profiles ────────────────────────────────────────
    vol_specs = [
        ("Amit Kumar",   "amit",  ["medical_aid", "search_rescue"],          "Mumbai",    85, 4),
        ("Priya Sharma", "priya", ["logistics", "water_purification"],        "Delhi",     52, 3),
        ("Rahul Singh",  "rahul", ["logistics", "community_outreach"],        "Pune",      120, 6),
        ("Meera Patel",  "meera", ["medical_aid", "teaching"],                "Bangalore", 35, 2),
        ("Arjun Nair",   "arjun", ["search_rescue", "structural_assessment"], "Chennai",   91, 5),
    ]
    volunteer_ids: list[str] = []
    for name, sfx, skills, city, tasks_done, yrs in vol_specs:
        vu = User(
            email=f"demo_{sfx}_{ngo_id[:6]}@guest.hackathon",
            password_hash=hash_password("demo123"),
            role="volunteer", ngo_id=ngo_id,
            full_name=name, phone=f"+9198{random.randint(1000000,9999999)}",
            profile_completed_at=now,
        )
        db.add(vu)
        await db.flush()
        db.add(VolunteerProfile(
            user_id=vu.id, ngo_id=ngo_id, skills=skills,
            availability={"mon": True, "tue": True, "wed": True, "thu": True, "fri": True, "sat": False, "sun": False},
            full_name=name, city=city, languages=["English", "Hindi"],
            causes_supported=["Disaster Relief", "Healthcare"],
            bio=f"Dedicated volunteer with {tasks_done} completed missions. Highly reliable.",
            years_experience=yrs, profile_completeness_score=0.85,
        ))
        volunteer_ids.append(vu.id)

    # ── 8 tasks ──────────────────────────────────────────────────────────────
    task_specs = [
        ("Flood Relief — Food Distribution",  "Distribute 2,000 food packets to families in Dharavi flood zones.",        ["logistics", "community_outreach"],        "high",   "open",        3,  19.040, 72.854),
        ("Medical Camp Setup",                "Set up emergency triage camp for 300 patients. Requires medical training.", ["medical_aid"],                            "high",   "in_progress", 2,  19.076, 72.877),
        ("Drinking Water Distribution",       "Distribute 5,000 litres of purified water to 10 relief sites.",            ["logistics", "water_purification"],        "medium", "open",        1,  19.052, 72.852),
        ("Rescue Operations — Rooftop",       "Rescue 45 stranded persons from flooded rooftops using inflatable boats.", ["search_rescue"],                          "high",   "in_progress", 1,  19.062, 72.833),
        ("Temporary Shelter Construction",    "Build 20 temporary shelters accommodating 100 displaced families.",         ["structural_assessment"],                  "high",   "completed",   -3, 19.035, 72.849),
        ("Flood Safety Awareness Drive",      "Conduct safety sessions for 200 children and parents in relief camps.",    ["teaching", "community_outreach"],         "low",    "open",        7,  19.048, 72.862),
        ("Damage Assessment Survey",          "Survey 50 households to record structural damage for relief planning.",    ["community_outreach"],                     "medium", "in_progress", 4,  19.057, 72.841),
        ("Medical Supply Convoy",             "Escort and distribute medical supplies (ORS, antibiotics) to 3 camps.",    ["medical_aid", "logistics"],               "high",   "open",        2,  19.069, 72.869),
    ]
    task_ids: list[str] = []
    for title, desc, skills, priority, status, days, lat, lng in task_specs:
        t = Task(
            ngo_id=ngo_id, title=title, description=desc,
            required_skills=skills, priority=priority, status=status,
            deadline=now + timedelta(days=days), lat=lat, lng=lng,
            urgency_score=90 if priority == "high" else 55,
        )
        db.add(t)
        await db.flush()
        task_ids.append(t.id)

    # ── assignments ───────────────────────────────────────────────────────────
    assign_specs = [
        (0, 0, "accepted"), (1, 1, "accepted"), (2, 2, "assigned"),
        (3, 3, "accepted"), (4, 4, "completed"), (5, 0, "assigned"),
        (6, 1, "accepted"), (7, 2, "assigned"),
    ]
    for ti, vi, status in assign_specs:
        a = Assignment(task_id=task_ids[ti], volunteer_id=volunteer_ids[vi], ngo_id=ngo_id, status=status)
        if status == "completed":
            a.completed_at = now - timedelta(days=2)
            a.accepted_at  = now - timedelta(days=4)
        elif status == "accepted":
            a.accepted_at = now - timedelta(hours=random.randint(2, 48))
        db.add(a)

    # ── events ────────────────────────────────────────────────────────────────
    event_specs = [
        ("Flood Relief Mega Drive",       "Large-scale relief effort across 5 zones of Mumbai.", "drive",    7,  "Dharavi, Mumbai",    100),
        ("Medical Awareness & Free Camp", "Free health checkups and medicine distribution.",      "camp",     4,  "Kurla East, Mumbai", 50),
        ("Volunteer First Aid Training",  "Mandatory first-aid certification for field teams.",   "training", 14, "NGO Headquarters",   30),
        ("Environmental Cleanup Drive",   "Post-flood cleanup of 3 km stretch in Bandra West.",  "drive",    21, "Bandra West, Mumbai",80),
    ]
    for title, desc, etype, days, location, maxv in event_specs:
        db.add(Event(
            ngo_id=ngo_id, title=title, description=desc,
            event_type=etype, date=now + timedelta(days=days),
            location=location, max_volunteers=maxv, status="upcoming",
        ))

    # ── resources ─────────────────────────────────────────────────────────────
    resource_specs = [
        ("Medical Kits",               50,  "available"),
        ("Water Purification Tablets", 200, "available"),
        ("Food Packages",              150, "in_use"),
        ("Rescue Boats",               8,   "in_use"),
        ("Temporary Shelters",         25,  "available"),
        ("First Aid Boxes",            40,  "available"),
    ]
    for rtype, qty, rstatus in resource_specs:
        db.add(Resource(ngo_id=ngo_id, type=rtype, quantity=qty, availability_status=rstatus))

    # ── admin notifications ───────────────────────────────────────────────────
    admin_notifs = [
        ("Priya Sharma accepted the 'Drinking Water Distribution' task.",            "status_update"),
        ("New volunteer joined your NGO: Meera Patel.",                              "general"),
        ("Task 'Medical Camp Setup' is 80% complete — 1 volunteer active.",          "status_update"),
        ("Resource alert: Food Packages running low. Current stock: 150 units.",     "general"),
        ("Upcoming event: Flood Relief Mega Drive in 7 days — volunteers needed!",   "general"),
        ("Rahul Singh completed 'Temporary Shelter Construction' — 100% verified.",  "status_update"),
    ]
    for msg, ntype in admin_notifs:
        db.add(Notification(user_id=admin_user_id, message=msg, type=ntype))



async def _seed_volunteer_demo_data(vol_user_id: str, ngo_id: str, db: AsyncSession) -> None:
    """Seed tasks and assignments for a guest volunteer demo session."""
    now = _now()

    # ── open tasks in NGO ────────────────────────────────────────────────────
    open_task_specs = [
        ("Flood Relief — Food Distribution",  "Distribute 2,000 food packets to Dharavi flood zones.",             ["logistics"],         "high",   1,  19.040, 72.854),
        ("Medical Supply Convoy",             "Escort medical supplies to 3 remote camps across Dharavi.",         ["medical_aid"],       "high",   2,  19.069, 72.869),
        ("Flood Safety Awareness Drive",      "Conduct flood safety sessions for 200 children in relief camps.",   ["teaching"],          "low",    5,  19.048, 72.862),
        ("Community Kitchen Volunteer",       "Help cook and serve meals for 500 flood-affected residents daily.", ["cooking"],           "medium", 3,  19.055, 72.845),
        ("Water Distribution — Zone 4",       "Distribute 3,000 bottles of mineral water across Zone 4 shelters.", ["logistics"],         "medium", 2,  19.061, 72.858),
    ]
    open_task_ids: list[str] = []
    for title, desc, skills, priority, days, lat, lng in open_task_specs:
        t = Task(
            ngo_id=ngo_id, title=title, description=desc,
            required_skills=skills, priority=priority, status="open",
            deadline=now + timedelta(days=days), lat=lat, lng=lng,
            urgency_score=88 if priority == "high" else 55,
        )
        db.add(t)
        await db.flush()
        open_task_ids.append(t.id)

    # ── tasks assigned to this volunteer ──────────────────────────────────────
    assigned_specs = [
        ("Rescue Operations — Rooftop",    "Rescue 45 stranded persons from flooded rooftops using inflatable boats.", ["search_rescue"],                   "high",   "accepted",  1,  19.062, 72.833),
        ("Damage Assessment Survey",       "Survey 50 households to record structural damage for relief planning.",    ["community_outreach"],              "medium", "assigned",  3,  19.057, 72.841),
        ("Temporary Shelter Construction", "Build 20 temporary shelters accommodating 100 displaced families.",        ["structural_assessment"],           "high",   "completed", -2, 19.035, 72.849),
    ]
    for title, desc, skills, priority, status, days, lat, lng in assigned_specs:
        t = Task(
            ngo_id=ngo_id, title=title, description=desc,
            required_skills=skills, priority=priority, status="in_progress" if status != "completed" else "completed",
            deadline=now + timedelta(days=days), lat=lat, lng=lng,
            urgency_score=85 if priority == "high" else 50,
        )
        db.add(t)
        await db.flush()
        a = Assignment(task_id=t.id, volunteer_id=vol_user_id, ngo_id=ngo_id, status=status)
        if status == "completed":
            a.accepted_at  = now - timedelta(days=3)
            a.completed_at = now - timedelta(days=2)
        elif status == "accepted":
            a.accepted_at = now - timedelta(hours=6)
        db.add(a)

    # ── volunteer notifications ────────────────────────────────────────────────
    vol_notifs = [
        ("You have been assigned: 'Rescue Operations — Rooftop'. Accept or decline.", "task_assigned"),
        ("Your task 'Temporary Shelter Construction' was verified — great work!",     "status_update"),
        ("Upcoming event: Flood Relief Mega Drive in 7 days. Register now!",          "general"),
        ("Your profile is 85% complete. Add more skills to get better task matches.", "general"),
    ]
    for msg, ntype in vol_notifs:
        db.add(Notification(user_id=vol_user_id, message=msg, type=ntype))


# ── Pydantic models ──────────────────────────────────────────────────────────

class SignupReq(BaseModel):
    email:       EmailStr
    password:    str = Field(..., min_length=8, max_length=128)
    role:        str = Field(..., pattern="^(ngo_admin|volunteer)$")
    invite_code: str | None = None
    full_name:   str | None = Field(None, max_length=200)
    phone:       str | None = Field(None, max_length=30)
    city:        str | None = Field(None, max_length=100)
    preferred_language: str = Field("en", max_length=32)
    communication_opt_in: bool = True
    consent_analytics: bool = True
    consent_personalization: bool = True
    consent_ai_training: bool = False
    motivation_statement: str | None = Field(None, max_length=2000)
    languages: list[str] = Field(default_factory=list)
    causes_supported: list[str] = Field(default_factory=list)
    education_level: str | None = Field(None, max_length=80)
    years_experience: int | None = Field(None, ge=0, le=80)
    skills: list[str] = Field(default_factory=list)
    bio: str | None = Field(None, max_length=2000)
    date_of_birth: date | None = None
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=30)
    preferred_roles: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    availability_notes: str | None = Field(None, max_length=1000)

class NGOCreateReq(BaseModel):
    name:        str = Field(..., min_length=2, max_length=200)
    description: str = Field("", max_length=1000)
    sector:      str | None = Field(None, max_length=120)
    website:     str | None = Field(None, max_length=300)
    headquarters_city: str | None = Field(None, max_length=120)
    primary_contact_name: str | None = Field(None, max_length=200)
    primary_contact_phone: str | None = Field(None, max_length=30)
    operating_regions: list[str] = Field(default_factory=list)
    mission_focus: list[str] = Field(default_factory=list)


class CheckEmailResponse(BaseModel):
    exists: bool
    role: str | None = None
    ngo_id: str | None = None


class LoginReq(BaseModel):
    email:    EmailStr
    password: str


class GoogleAuthReq(BaseModel):
    email:             EmailStr
    firebase_id_token: str          # raw Firebase ID token — verified server-side
    role:              str = Field(..., pattern="^(ngo_admin|volunteer)$")
    invite_code:  str | None = None
    full_name:   str | None = Field(None, max_length=200)
    phone:       str | None = Field(None, max_length=30)
    city:        str | None = Field(None, max_length=100)
    preferred_language: str = Field("en", max_length=32)
    communication_opt_in: bool = True
    consent_analytics: bool = True
    consent_personalization: bool = True
    consent_ai_training: bool = False
    motivation_statement: str | None = Field(None, max_length=2000)
    languages: list[str] = Field(default_factory=list)
    causes_supported: list[str] = Field(default_factory=list)
    education_level: str | None = Field(None, max_length=80)
    years_experience: int | None = Field(None, ge=0, le=80)
    skills: list[str] = Field(default_factory=list)
    bio: str | None = Field(None, max_length=2000)
    date_of_birth: date | None = None
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=30)
    preferred_roles: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    availability_notes: str | None = Field(None, max_length=1000)


def _record_consent_events(user_id: str, req: SignupReq | GoogleAuthReq, db: AsyncSession) -> None:
    db.add(ConsentEvent(user_id=user_id, scope="analytics", granted=req.consent_analytics, source="signup"))
    db.add(ConsentEvent(user_id=user_id, scope="personalization", granted=req.consent_personalization, source="signup"))
    db.add(ConsentEvent(user_id=user_id, scope="ai_training", granted=req.consent_ai_training, source="signup"))


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=AuthResponse)
@limiter.limit("10/minute")
async def signup(request: Request, req: SignupReq, db: AsyncSession = Depends(get_db)):
    # Duplicate email check
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    if req.role == "volunteer":
        if not req.invite_code:
            raise HTTPException(status_code=400, detail="invite_code required for volunteers")
        ngo = (await db.execute(select(NGO).where(NGO.invite_code == req.invite_code))).scalar_one_or_none()
        if not ngo:
            raise HTTPException(status_code=404, detail="Invalid invite code")

        user = User(
            email=req.email,
            password_hash=hash_password(req.password),
            role="volunteer",
            ngo_id=ngo.id,
            full_name=req.full_name,
            phone=req.phone,
            preferred_language=req.preferred_language,
            communication_opt_in=req.communication_opt_in,
            consent_analytics=req.consent_analytics,
            consent_personalization=req.consent_personalization,
            consent_ai_training=req.consent_ai_training,
            profile_completed_at=_now() if req.full_name and req.phone and req.city else None,
        )
        db.add(user)
        await db.flush()  # get user.id before commit

        profile = VolunteerProfile(
            user_id=user.id,
            ngo_id=ngo.id,
            skills=req.skills,
            availability={"mon": True, "tue": True, "wed": True, "thu": True, "fri": True, "sat": False, "sun": False},
            full_name=req.full_name,
            phone=req.phone,
            city=req.city,
            motivation_statement=req.motivation_statement,
            languages=req.languages,
            causes_supported=req.causes_supported,
            education_level=req.education_level,
            years_experience=req.years_experience,
            bio=req.bio,
            date_of_birth=req.date_of_birth,
            emergency_contact_name=req.emergency_contact_name,
            emergency_contact_phone=req.emergency_contact_phone,
            preferred_roles=req.preferred_roles,
            certifications=req.certifications,
            availability_notes=req.availability_notes,
        )
        db.add(profile)
        _record_consent_events(user.id, req, db)
        await db.commit()
        token = create_token(user.id, "volunteer", ngo.id, req.email)
        return {"token": token, "role": "volunteer", "ngo_id": ngo.id, "ngo_name": ngo.name}

    # ngo_admin — no ngo_id yet; must call /ngo/create next
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role="ngo_admin",
        ngo_id=None,
        full_name=req.full_name,
        phone=req.phone,
        preferred_language=req.preferred_language,
        communication_opt_in=req.communication_opt_in,
        consent_analytics=req.consent_analytics,
        consent_personalization=req.consent_personalization,
        consent_ai_training=req.consent_ai_training,
    )
    db.add(user)
    await db.flush()
    _record_consent_events(user.id, req, db)
    await db.commit()
    token = create_token(user.id, "ngo_admin", None, req.email)
    return {"token": token, "role": "ngo_admin", "ngo_id": None, "needs_ngo_setup": True}


@router.post("/guest", response_model=AuthResponse)
@limiter.limit("10/hour")
async def guest_login(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Guest Mode — creates an isolated demo NGO with seeded data.
    Disable in production by setting ENABLE_GUEST_MODE=false.
    """
    import os as _os
    if _os.getenv("ENABLE_GUEST_MODE", "true").lower() == "false":
        raise HTTPException(status_code=403, detail="Guest mode is disabled")

    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    guest_email = f"guest_{unique_suffix}@synapseai.hackathon"

    ngo_code = _random_code()
    from db.models import NGO, User

    user = User(
        email=guest_email,
        password_hash=hash_password(secrets.token_hex(24)),  # non-guessable; login not needed
        role="ngo_admin",
        ngo_id=None,
        full_name="Demo Admin",
        phone=None,
        profile_completed_at=_now()
    )
    db.add(user)
    await db.flush()
    
    ngo = NGO(
        name=f"Guest NGO {unique_suffix}",
        description="Auto-generated NGO for hackathon guest.",
        invite_code=ngo_code,
        created_by=user.id,
        sector="Hackathon",
    )
    db.add(ngo)
    await db.flush()
    
    user.ngo_id = ngo.id
    
    db.add(ConsentEvent(user_id=user.id, scope="analytics", granted=True, source="guest"))
    db.add(ConsentEvent(user_id=user.id, scope="personalization", granted=True, source="guest"))
    db.add(ConsentEvent(user_id=user.id, scope="ai_training", granted=True, source="guest"))

    # Seed demo data so the guest NGO dashboard is fully populated
    await _seed_ngo_demo_data(user.id, ngo.id, db)

    await db.commit()

    token = create_token(user.id, "ngo_admin", ngo.id, guest_email)
    return {"token": token, "role": "ngo_admin", "ngo_id": ngo.id, "ngo_name": ngo.name}


@router.post("/guest-volunteer", response_model=AuthResponse)
@limiter.limit("10/hour")
async def guest_volunteer_login(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Guest Volunteer Mode (for Hackathon Demo)
    Creates a temporary volunteer account with a demo NGO and pre-seeded tasks/assignments.
    """
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    guest_email = f"vol_guest_{unique_suffix}@synapseai.hackathon"

    # 1. Create volunteer user first so we have a real ID for NGO.created_by
    vol_user = User(
        email=guest_email,
        password_hash=hash_password(secrets.token_hex(24)),  # non-guessable
        role="volunteer",
        ngo_id=None,
        full_name="Demo Volunteer",
        phone=None,
        profile_completed_at=_now(),
    )
    db.add(vol_user)
    await db.flush()                       # get vol_user.id

    # 2. Create demo NGO with a valid created_by FK
    ngo_code = _random_code()
    ngo = NGO(
        name=f"Demo Relief NGO {unique_suffix}",
        description="Hackathon demo NGO for volunteer guest mode.",
        invite_code=ngo_code,
        created_by=vol_user.id,            # real FK — no constraint violation
        sector="Disaster Relief",
        headquarters_city="Mumbai",
    )
    db.add(ngo)
    await db.flush()                       # get ngo.id

    # 3. Link user to NGO
    vol_user.ngo_id = ngo.id

    # 3. Create volunteer profile
    db.add(VolunteerProfile(
        user_id=vol_user.id, ngo_id=ngo.id,
        skills=["search_rescue", "first_aid", "logistics"],
        availability={"mon": True, "tue": True, "wed": True, "thu": True, "fri": True, "sat": False, "sun": False},
        full_name="Demo Volunteer", city="Mumbai",
        languages=["English", "Hindi"],
        causes_supported=["Disaster Relief", "Healthcare"],
        bio="Passionate volunteer ready to make a difference in emergency response.",
        years_experience=2,
        education_level="undergraduate",
        certifications=["First Aid", "CPR"],
        profile_completeness_score=0.85,
    ))

    # 4. Consent events
    db.add(ConsentEvent(user_id=vol_user.id, scope="analytics",       granted=True, source="guest"))
    db.add(ConsentEvent(user_id=vol_user.id, scope="personalization", granted=True, source="guest"))
    db.add(ConsentEvent(user_id=vol_user.id, scope="ai_training",     granted=True, source="guest"))

    # 5. Seed tasks and assignments
    await _seed_volunteer_demo_data(vol_user.id, ngo.id, db)

    await db.commit()

    token = create_token(vol_user.id, "volunteer", ngo.id, guest_email)
    return {"token": token, "role": "volunteer", "ngo_id": ngo.id, "ngo_name": ngo.name}


@router.post("/ngo/create", response_model=AuthResponse)
async def create_ngo(
    req: NGOCreateReq,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "ngo_admin":
        raise HTTPException(status_code=403, detail="Only ngo_admin can create an NGO")
    if user.ngo_id:
        raise HTTPException(status_code=400, detail="NGO already created for this account")

    # Ensure unique invite code
    code = _random_code()
    while (await db.execute(select(NGO).where(NGO.invite_code == code))).scalar_one_or_none():
        code = _random_code()

    ngo = NGO(
        name=req.name,
        description=req.description,
        invite_code=code,
        created_by=user.user_id,
        sector=req.sector,
        website=req.website,
        headquarters_city=req.headquarters_city,
        primary_contact_name=req.primary_contact_name,
        primary_contact_phone=req.primary_contact_phone,
        operating_regions=req.operating_regions,
        mission_focus=req.mission_focus,
    )
    db.add(ngo)
    await db.flush()

    await db.execute(update(User).where(User.id == user.user_id).values(ngo_id=ngo.id))
    await db.commit()
    token = create_token(user.user_id, "ngo_admin", ngo.id, user.email)

    return {"token": token, "role": "ngo_admin", "ngo_id": ngo.id, "invite_code": code, "ngo_name": ngo.name}


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, req: LoginReq, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login_at = _now()
    await db.commit()
    token = create_token(user.id, user.role, user.ngo_id, user.email)
    return {
        "token":  token,
        "role":   user.role,
        "ngo_id": user.ngo_id,
        "needs_ngo_setup": user.role == "ngo_admin" and not user.ngo_id,
    }


@router.post("/google", response_model=AuthResponse)
@limiter.limit("5/minute")
async def google_auth(request: Request, req: GoogleAuthReq, db: AsyncSession = Depends(get_db)):
    """Google Sign-In: verify Firebase ID token server-side, find or create user, return JWT."""
    # Server-side Firebase token verification — prevents uid forgery
    try:
        import firebase_admin.auth as fb_auth
        decoded = fb_auth.verify_id_token(req.firebase_id_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    if decoded.get("email", "").lower() != str(req.email).lower():
        raise HTTPException(status_code=401, detail="Token email does not match request email")
    try:
        return await _google_auth_inner(req, db)
    except HTTPException:
        raise
    except Exception as exc:
        raise safe_http_error(503, "Service temporarily unavailable", exc, "google_auth")


async def _google_auth_inner(req: GoogleAuthReq, db: AsyncSession):
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()

    if user:
        # Existing user — return token regardless of how they originally signed up
        user.last_login_at = _now()
        token = create_token(user.id, user.role, user.ngo_id, user.email)
        return {
            "token": token,
            "role": user.role,
            "ngo_id": user.ngo_id,
            "needs_ngo_setup": user.role == "ngo_admin" and not user.ngo_id,
        }

    # New user via Google
    if req.role == "volunteer":
        if not req.invite_code:
            raise HTTPException(status_code=400, detail="invite_code required for volunteers")
        ngo = (await db.execute(select(NGO).where(NGO.invite_code == req.invite_code))).scalar_one_or_none()
        if not ngo:
            raise HTTPException(status_code=404, detail="Invalid invite code")

        try:
            user = User(
                email=req.email,
                password_hash=None,
                role="volunteer",
                ngo_id=ngo.id,
                full_name=req.full_name,
                phone=req.phone,
                preferred_language=req.preferred_language,
                communication_opt_in=req.communication_opt_in,
                consent_analytics=req.consent_analytics,
                consent_personalization=req.consent_personalization,
                consent_ai_training=req.consent_ai_training,
                profile_completed_at=_now() if req.full_name and req.phone and req.city else None,
            )
            db.add(user)
            await db.flush()

            profile = VolunteerProfile(
                user_id=user.id,
                ngo_id=ngo.id,
                skills=req.skills,
                availability={"mon": True, "tue": True, "wed": True, "thu": True, "fri": True, "sat": False, "sun": False},
                full_name=req.full_name,
                phone=req.phone,
                city=req.city,
                motivation_statement=req.motivation_statement,
                languages=req.languages,
                causes_supported=req.causes_supported,
                education_level=req.education_level,
                years_experience=req.years_experience,
                bio=req.bio,
                date_of_birth=req.date_of_birth,
                emergency_contact_name=req.emergency_contact_name,
                emergency_contact_phone=req.emergency_contact_phone,
                preferred_roles=req.preferred_roles,
                certifications=req.certifications,
                availability_notes=req.availability_notes,
            )
            db.add(profile)
            _record_consent_events(user.id, req, db)
            await db.commit()
            token = create_token(user.id, "volunteer", ngo.id, req.email)
            return {"token": token, "role": "volunteer", "ngo_id": ngo.id, "ngo_name": ngo.name}
        except IntegrityError:
            await db.rollback()
            existing_user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
            if existing_user:
                token = create_token(existing_user.id, existing_user.role, existing_user.ngo_id, existing_user.email)
                return {
                    "token": token,
                    "role": existing_user.role,
                    "ngo_id": existing_user.ngo_id,
                    "needs_ngo_setup": existing_user.role == "ngo_admin" and not existing_user.ngo_id,
                }
            raise

    # ngo_admin — NGO created separately via /ngo/create
    try:
        user = User(
            email=req.email,
            password_hash=None,
            role="ngo_admin",
            ngo_id=None,
            full_name=req.full_name,
            phone=req.phone,
            preferred_language=req.preferred_language,
            communication_opt_in=req.communication_opt_in,
            consent_analytics=req.consent_analytics,
            consent_personalization=req.consent_personalization,
            consent_ai_training=req.consent_ai_training,
        )
        db.add(user)
        await db.flush()
        _record_consent_events(user.id, req, db)
        await db.commit()
        token = create_token(user.id, "ngo_admin", None, req.email)
        return {"token": token, "role": "ngo_admin", "ngo_id": None, "needs_ngo_setup": True}
    except IntegrityError:
        await db.rollback()
        existing_user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
        if existing_user:
            token = create_token(existing_user.id, existing_user.role, existing_user.ngo_id, existing_user.email)
            return {
                "token": token,
                "role": existing_user.role,
                "ngo_id": existing_user.ngo_id,
                "needs_ngo_setup": existing_user.role == "ngo_admin" and not existing_user.ngo_id,
            }
        raise


@router.get("/check-email", response_model=CheckEmailResponse)
@limiter.limit("30/minute")
async def check_email(request: Request, email: str, db: AsyncSession = Depends(get_db)):
    """Public — no auth. Returns whether email is registered and their role/ngo_id."""
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        return CheckEmailResponse(exists=False)
    return CheckEmailResponse(exists=True, role=user.role, ngo_id=str(user.ngo_id) if user.ngo_id else None)


@router.post("/logout")
async def logout(
    creds: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
    """Revoke the current JWT by adding its jti to the Redis blacklist."""
    if creds:
        try:
            from utils.auth_utils import decode_token, blacklist_token, EXPIRE_MINS
            payload = decode_token(creds.credentials)
            jti = payload.get("jti")
            if jti:
                await blacklist_token(jti, EXPIRE_MINS * 60)
        except Exception:
            pass  # always return success; don't leak token details
    return {"message": "Logged out successfully"}


@router.get("/ngo/lookup/{invite_code}")
@limiter.limit("30/minute")
async def lookup_ngo(request: Request, invite_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NGO).where(NGO.invite_code == invite_code.upper()))
    ngo = result.scalar_one_or_none()
    if not ngo:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    return {"ngo_name": ngo.name, "invite_code": ngo.invite_code}
