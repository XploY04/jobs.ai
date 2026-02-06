from sqlalchemy import Column, String, Text, DateTime, JSON, Index, Integer, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(100), primary_key=True)  # e.g., "jsearch_abc123"
    source = Column(String(50), nullable=False, index=True)
    source_id = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    location = Column(JSON, nullable=False)
    employment_type = Column(String(50))
    salary_min = Column(String(50))
    salary_max = Column(String(50))
    salary_currency = Column(String(10))
    apply_url = Column(String(1000), nullable=False)
    posted_at = Column(DateTime(timezone=True), nullable=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_data = Column(JSON)
    title_company_hash = Column(String(64), index=True)

    # AI Enrichment fields
    skills = Column(ARRAY(String), default=[])  # Extracted tech skills
    ai_category = Column(String(50), index=True)  # frontend, backend, devops, etc.
    ai_quality_score = Column(Integer)  # 0-100
    ai_urgency = Column(String(20))  # urgent, normal, low
    ai_extracted_deadline = Column(DateTime(timezone=True))  # Parsed deadline
    ai_deadline_confidence = Column(String(20))  # high, medium, low, none
    ai_seniority = Column(String(20))  # junior, mid, senior, staff, principal
    ai_work_arrangement = Column(String(20))  # remote, hybrid, onsite
    ai_visa_sponsorship = Column(String(20))  # yes, no, unknown
    ai_required_years = Column(Integer)  # Estimated years of experience

    __table_args__ = (
        Index("idx_source_source_id", "source", "source_id", unique=True),
        Index("idx_posted_at", "posted_at"),
        Index("idx_ai_category", "ai_category"),
        Index("idx_skills_gin", "skills", postgresql_using="gin"),
    )
