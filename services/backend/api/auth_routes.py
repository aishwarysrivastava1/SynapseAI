import random
import string
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from db.base import get_db
from db.models import User, NGO, VolunteerProfile
from utils.auth_utils import hash_password, verify_password, create_token
from middleware.rbac import get_current_user, CurrentUser

router = APIRouter()


def _random_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ── Pydantic models ──────────────────────────────────────────────────────────

class SignupReq(BaseModel):
    email:       EmailStr
    password:    str = Field(..., min_length=8, max_length=128)
    role:        str = Field(..., pattern="^(ngo_admin|volunteer)$")
    invite_code: str | None = None


class NGOCreateReq(BaseModel):
    name:        str = Field(..., min_length=2, max_length=200)
    description: str = Field("", max_length=1000)


class LoginReq(BaseModel):
    email:    EmailStr
    password: str


class GoogleAuthReq(BaseModel):
    email:        EmailStr
    firebase_uid: str
    role:         str = Field(..., pattern="^(ngo_admin|volunteer)$")
    invite_code:  str | None = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/signup")
async def signup(req: SignupReq, db: AsyncSession = Depends(get_db)):
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

        user = User(email=req.email, password_hash=hash_password(req.password), role="volunteer", ngo_id=ngo.id)
        db.add(user)
        await db.flush()  # get user.id before commit

        profile = VolunteerProfile(
            user_id=user.id,
            ngo_id=ngo.id,
            skills=[],
            availability={"mon": True, "tue": True, "wed": True, "thu": True, "fri": True, "sat": False, "sun": False},
        )
        db.add(profile)
        token = create_token(user.id, "volunteer", ngo.id, req.email)
        return {"token": token, "role": "volunteer", "ngo_id": ngo.id, "ngo_name": ngo.name}

    # ngo_admin — no ngo_id yet; must call /ngo/create next
    user = User(email=req.email, password_hash=hash_password(req.password), role="ngo_admin", ngo_id=None)
    db.add(user)
    await db.flush()
    token = create_token(user.id, "ngo_admin", None, req.email)
    return {"token": token, "role": "ngo_admin", "ngo_id": None, "needs_ngo_setup": True}


@router.post("/ngo/create")
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

    ngo = NGO(name=req.name, description=req.description, invite_code=code, created_by=user.user_id)
    db.add(ngo)
    await db.flush()

    await db.execute(update(User).where(User.id == user.user_id).values(ngo_id=ngo.id))
    token = create_token(user.user_id, "ngo_admin", ngo.id, user.email)

    return {"token": token, "ngo_id": ngo.id, "invite_code": code, "name": ngo.name}


@router.post("/login")
async def login(req: LoginReq, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.id, user.role, user.ngo_id, user.email)
    return {
        "token":  token,
        "role":   user.role,
        "ngo_id": user.ngo_id,
        "needs_ngo_setup": user.role == "ngo_admin" and not user.ngo_id,
    }


@router.post("/google")
async def google_auth(req: GoogleAuthReq, db: AsyncSession = Depends(get_db)):
    """Google Sign-In: find or create user by email, return JWT. No password needed."""
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()

    if user:
        # Existing user — return token regardless of how they originally signed up
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

        user = User(email=req.email, password_hash=None, role="volunteer", ngo_id=ngo.id)
        db.add(user)
        await db.flush()

        profile = VolunteerProfile(
            user_id=user.id,
            ngo_id=ngo.id,
            skills=[],
            availability={"mon": True, "tue": True, "wed": True, "thu": True, "fri": True, "sat": False, "sun": False},
        )
        db.add(profile)
        token = create_token(user.id, "volunteer", ngo.id, req.email)
        return {"token": token, "role": "volunteer", "ngo_id": ngo.id, "ngo_name": ngo.name}

    # ngo_admin — NGO created separately via /ngo/create
    user = User(email=req.email, password_hash=None, role="ngo_admin", ngo_id=None)
    db.add(user)
    await db.flush()
    token = create_token(user.id, "ngo_admin", None, req.email)
    return {"token": token, "role": "ngo_admin", "ngo_id": None, "needs_ngo_setup": True}


@router.post("/logout")
async def logout():
    return {"message": "Logged out — delete token client-side"}
