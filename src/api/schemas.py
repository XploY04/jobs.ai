from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict


class JobLocation(BaseModel):
    """Normalized location payload included with each job."""

    city: Optional[str] = None
    country: Optional[str] = None
    remote: Optional[bool] = None


class JobResponse(BaseModel):
    """Job representation returned via the public API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    source_id: str
    title: str
    company: str
    description: str
    location: Union[JobLocation, Dict[str, Optional[Union[str, bool]]]]
    employment_type: Optional[str] = None
    salary_min: Optional[str] = None
    salary_max: Optional[str] = None
    salary_currency: Optional[str] = None
    apply_url: str
    posted_at: datetime


class JobsListResponse(BaseModel):
    """Paginated response wrapper for job listings."""

    total: int
    jobs: List[JobResponse]
