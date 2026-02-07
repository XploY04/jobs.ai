from sqlalchemy import Column, String, Text, DateTime, JSON, Index, Integer, ARRAY, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class DiscoveredCompany(Base):
    """Companies discovered via Google Custom Search for ATS scraping."""
    __tablename__ = "discovered_companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=False)  # greenhouse, lever, ashby, workable, smartrecruiters
    company_name = Column(String(255))  # human-readable name if known
    discovered_via = Column(String(100))  # google_search, manual, etc.
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_fetched_at = Column(DateTime(timezone=True))  # when we last scraped their jobs
    is_active = Column(Boolean, default=True)  # set False if 404s consistently
    job_count = Column(Integer, default=0)  # jobs found last fetch

    __table_args__ = (
        Index("idx_platform_slug", "platform", "slug", unique=True),
        Index("idx_is_active", "is_active"),
    )


class Job(Base):
    __tablename__ = "jobs"

    # ── Identity ──
    id = Column(String(100), primary_key=True)  # e.g., "jsearch_abc123"
    source = Column(String(50), nullable=False, index=True)
    source_id = Column(String(200), nullable=False)
    source_url = Column(String(1000))  # link back to source listing

    # ── Core Job Info ──
    title = Column(String(500), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    company_logo = Column(String(1000))  # logo URL
    company_website = Column(String(1000))  # employer website
    description = Column(Text, nullable=False)  # full description (HTML preserved)
    short_description = Column(Text)  # AI-generated 2-3 sentence summary

    # ── Location ──
    location = Column(JSON)  # legacy {city, country, remote} blob
    country = Column(String(100))
    city = Column(String(200))
    state = Column(String(200))
    is_remote = Column(Boolean)
    work_arrangement = Column(String(30))  # remote / hybrid / onsite
    latitude = Column(Float)
    longitude = Column(Float)

    # ── Employment Details ──
    employment_type = Column(String(50))  # FULLTIME / PARTTIME / CONTRACT / INTERN
    seniority_level = Column(String(30))  # junior / mid / senior / staff / principal
    department = Column(String(200))  # engineering, marketing, etc.
    category = Column(String(50), index=True)  # backend / frontend / fullstack / devops / data / ml / mobile / security / qa / general

    # ── Compensation ──
    salary_min = Column(String(50))
    salary_max = Column(String(50))
    salary_currency = Column(String(10))
    salary_period = Column(String(20))  # year / month / week / hour

    # ── Skills & Requirements ──
    skills = Column(ARRAY(String), default=[])
    required_experience_years = Column(Integer)
    required_education = Column(String(100))  # e.g., "Bachelor's", "Master's"
    key_responsibilities = Column(JSON)  # JSON array of strings
    nice_to_have_skills = Column(JSON)  # JSON array of strings

    # ── Benefits & Perks ──
    benefits = Column(JSON)  # JSON array of strings
    visa_sponsorship = Column(String(20))  # yes / no / unknown

    # ── Dates ──
    posted_at = Column(DateTime(timezone=True))
    application_deadline = Column(DateTime(timezone=True))
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Apply ──
    apply_url = Column(String(1000))
    apply_options = Column(JSON)  # JSON array of {url, publisher} for multiple apply links

    # ── Quality / Meta ──
    tags = Column(JSON)  # JSON array of source tags
    quality_score = Column(Integer)  # 0-100
    raw_data = Column(JSON)  # full original API response (backup)
    title_company_hash = Column(String(64), index=True)

    __table_args__ = (
        Index("idx_source_source_id", "source", "source_id", unique=True),
        Index("idx_posted_at", "posted_at"),
        Index("idx_category", "category"),
        Index("idx_skills_gin", "skills", postgresql_using="gin"),
        Index("idx_is_remote", "is_remote"),
        Index("idx_seniority", "seniority_level"),
    )
