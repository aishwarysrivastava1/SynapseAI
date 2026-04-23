from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/synapseai")

engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    pool_size=5, 
    max_overflow=10,
    pool_recycle=300, # Prevents stale connections common in serverless environments
    pool_pre_ping=True # Verifies connection before providing it to the session
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    from db import models  # noqa: F401 — ensure models are imported so metadata is populated
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent migrations for columns added after initial deploy
        for stmt in [
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS share_location BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION",
            "ALTER TABLE resources ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION",
            "ALTER TABLE resources ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS full_name VARCHAR(200)",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS phone VARCHAR(30)",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS city VARCHAR(100)",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS bio TEXT",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS date_of_birth DATE",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMP",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(200)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(30)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(32) NOT NULL DEFAULT 'en'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS communication_opt_in BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_analytics BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_personalization BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_ai_training BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_completed_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE ngos ADD COLUMN IF NOT EXISTS sector VARCHAR(120)",
            "ALTER TABLE ngos ADD COLUMN IF NOT EXISTS website VARCHAR(300)",
            "ALTER TABLE ngos ADD COLUMN IF NOT EXISTS headquarters_city VARCHAR(120)",
            "ALTER TABLE ngos ADD COLUMN IF NOT EXISTS primary_contact_name VARCHAR(200)",
            "ALTER TABLE ngos ADD COLUMN IF NOT EXISTS primary_contact_phone VARCHAR(30)",
            "ALTER TABLE ngos ADD COLUMN IF NOT EXISTS operating_regions JSONB DEFAULT '[]'",
            "ALTER TABLE ngos ADD COLUMN IF NOT EXISTS mission_focus JSONB DEFAULT '[]'",
            "ALTER TABLE ngos ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(200)",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR(30)",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS education_level VARCHAR(80)",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS years_experience INTEGER",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS preferred_roles JSONB DEFAULT '[]'",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS certifications JSONB DEFAULT '[]'",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS languages JSONB DEFAULT '[]'",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS causes_supported JSONB DEFAULT '[]'",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS motivation_statement TEXT",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS availability_notes TEXT",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS work_preferences JSONB DEFAULT '{}'",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP",
            "ALTER TABLE volunteer_profiles ADD COLUMN IF NOT EXISTS profile_completeness_score DOUBLE PRECISION NOT NULL DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_category VARCHAR(100)",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS estimated_hours DOUBLE PRECISION",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS urgency_score DOUBLE PRECISION NOT NULL DEFAULT 50",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS impact_tags JSONB DEFAULT '[]'",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS hours_spent DOUBLE PRECISION",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS completion_rating INTEGER",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS ngo_feedback TEXT",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS match_score DOUBLE PRECISION",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass
