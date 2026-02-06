from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import JobResponse, JobsListResponse
from src.database.operations import db
from src.services.ingestion import run_ingestion_cycle

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/health")
async def health_check() -> dict:
    """Basic health endpoint for uptime monitoring."""

    return {"status": "ok"}


@router.get("/jobs", response_model=JobsListResponse)
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(default=None, min_length=2),
    source: Optional[List[str]] = Query(default=None, alias="source"),
    employment_type: Optional[str] = Query(default=None),
    remote_only: bool = Query(default=False),
) -> JobsListResponse:
    """Return paginated backend/devops jobs."""

    jobs = await db.list_jobs(
        limit=limit,
        offset=offset,
        search=search,
        sources=source,
        employment_type=employment_type,
        remote_only=remote_only,
    )

    return JobsListResponse(total=len(jobs), jobs=jobs)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Return a single job by identifier."""

    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/ingest")
async def trigger_ingestion() -> dict:
    """Fire off an ad-hoc ingestion cycle."""

    return await run_ingestion_cycle()
