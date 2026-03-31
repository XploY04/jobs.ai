"""MongoDB index definitions and document helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo import ASCENDING, DESCENDING, TEXT


async def ensure_indexes(db) -> None:
    """Create indexes on jobs and discovered_companies collections."""

    jobs = db["jobs"]
    await jobs.create_index(
        [("source", ASCENDING), ("source_id", ASCENDING)],
        unique=True,
        name="idx_source_source_id",
    )
    await jobs.create_index(
        [("title_company_hash", ASCENDING)],
        unique=True,
        sparse=True,
        name="idx_title_company_hash",
    )
    await jobs.create_index(
        [("title", TEXT), ("company", TEXT), ("description", TEXT)],
        weights={"title": 10, "company": 5, "description": 1},
        name="idx_text_search",
    )
    await jobs.create_index([("posted_at", DESCENDING)], name="idx_posted_at")
    await jobs.create_index([("category", ASCENDING)], name="idx_category")
    await jobs.create_index([("is_remote", ASCENDING)], name="idx_is_remote")
    await jobs.create_index([("seniority_level", ASCENDING)], name="idx_seniority")
    await jobs.create_index([("application_deadline", ASCENDING)], name="idx_application_deadline")

    companies = db["discovered_companies"]
    await companies.create_index(
        [("platform", ASCENDING), ("slug", ASCENDING)],
        unique=True,
        name="idx_platform_slug",
    )
    await companies.create_index([("is_active", ASCENDING)], name="idx_is_active")


def normalize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Remap MongoDB _id to id for API compatibility."""
    if doc is None:
        return None
    doc["id"] = doc.pop("_id")
    return doc
