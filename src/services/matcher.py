"""Job-user matching orchestrator.

Two-stage pipeline:
  Stage 1+2: Pre-filter with MongoDB, then score with structured signals (Python, no AI cost)
  Stage 3: AI refinement via OpenAI on the top matches (costs API credits)

Runs as:
  - Weekly batch: all users with job_matching_enabled=true
  - Single user: after resume parse or on-demand
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.database.operations import db
from src.services.match_scorer import (
    WEIGHTS,
    compute_idf,
    compute_total,
    experience_fit_score,
    is_stretch_match,
    location_match_score,
    salary_fit_score,
    seniority_fit_score,
    skills_match_score,
    title_similarity_score,
)
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

MATCH_CREDIT_COST = 50
TOP_N_STRUCTURED = 50  # Keep top 50 from Stage 1+2
TOP_N_AI = 20  # Send top 20 to AI


async def run_matching_for_all() -> Dict[str, Any]:
    """Weekly batch: match jobs for all users with job_matching_enabled=true."""

    users = await _get_matching_users()
    logger.info("Found %d users with job_matching_enabled=true", len(users))

    if not users:
        return {"users_processed": 0, "total_matches": 0}

    jobs = await _get_active_jobs()
    if not jobs:
        logger.warning("No jobs in database, skipping matching")
        return {"users_processed": 0, "total_matches": 0}

    idf = compute_idf(jobs)
    total_matches = 0
    users_processed = 0
    users_skipped = 0

    for user in users:
        credits = user.get("credits", 0)
        if credits < MATCH_CREDIT_COST:
            logger.info("Skipping user %s: insufficient credits (%d)", user["_id"], credits)
            users_skipped += 1
            continue

        deducted = await _deduct_credits(user["_id"], user.get("email", ""))
        if not deducted:
            users_skipped += 1
            continue

        matches = await _compute_matches(user, jobs, idf, run_ai=True)
        await _save_matches(user["_id"], matches)

        total_matches += len(matches)
        users_processed += 1
        logger.info("User %s: %d matches (credits deducted)", user["_id"], len(matches))

    summary = {
        "users_processed": users_processed,
        "users_skipped": users_skipped,
        "total_matches": total_matches,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Matching complete: %s", summary)
    return summary


async def run_matching_for_user(user_id: str, run_ai: bool = True) -> Dict[str, Any]:
    """Single user matching (on-demand or after resume parse)."""

    user = await db.db["users"].find_one({"_id": user_id})
    if not user:
        logger.error("User %s not found", user_id)
        return {"error": "user not found"}

    jobs = await _get_active_jobs()
    if not jobs:
        return {"matches": 0}

    idf = compute_idf(jobs)
    matches = await _compute_matches(user, jobs, idf, run_ai=run_ai)
    await _save_matches(user_id, matches)

    logger.info("User %s: %d matches computed", user_id, len(matches))
    return {"matches": len(matches), "user_id": user_id}


async def _compute_matches(
    user: dict, jobs: List[dict], idf: Dict[str, float], run_ai: bool = False
) -> List[dict]:
    """Stage 1+2: pre-filter and score, then optionally Stage 3: AI refine."""

    user_skills = [s.lower().strip() for s in (user.get("skills") or []) if s]
    user_titles = _collect_user_titles(user)
    user_level = user.get("seniority_level")
    user_location = user.get("location")
    user_years = user.get("years_of_experience")

    # Get resume for additional signals
    resume_doc = await db.db["resumes"].find_one({"user_id": user["_id"]})
    user_education = None
    if resume_doc:
        profile = resume_doc.get("editable_profile") or {}
        education = profile.get("education") or []
        if education:
            user_education = education[0].get("degree")
        # Add technologies from experiences to skills
        for exp in (profile.get("experiences") or []):
            for tech in (exp.get("technologies") or []):
                skill = tech.lower().strip()
                if skill and skill not in user_skills:
                    user_skills.append(skill)

    # Stage 1: Pre-filter with MongoDB
    prefilter = {"posted_at": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}}
    if user_skills:
        prefilter["skills"] = {"$in": user_skills[:20]}

    candidate_jobs = await db.jobs.find(
        prefilter,
        {"raw_data": 0, "description": 0},
    ).to_list(length=1000)

    if not candidate_jobs:
        candidate_jobs = jobs[:500]

    logger.info("User %s: %d candidate jobs after pre-filter", user["_id"], len(candidate_jobs))

    # Stage 2: Score each candidate
    scored = []
    for job in candidate_jobs:
        signals = {
            "skills_match": skills_match_score(user_skills, job.get("skills") or [], idf),
            "title_similarity": title_similarity_score(user_titles, job.get("title", "")),
            "seniority_fit": seniority_fit_score(user_level, job.get("seniority_level")),
            "location_match": location_match_score(user_location, job.get("country"), job.get("is_remote")),
            "experience_fit": experience_fit_score(user_years, job.get("required_experience_years")),
            "salary_fit": salary_fit_score(None, job.get("salary_min"), job.get("salary_max")),
        }

        score = compute_total(signals)
        if score < 25:
            continue

        stretch = is_stretch_match(
            user_years, job.get("required_experience_years"),
            user_education, job.get("required_education"),
        )
        if stretch:
            score = min(score, 40)

        scored.append({
            "_id": f"{user['_id']}_{job['_id']}",
            "user_id": user["_id"],
            "job_id": job["_id"],
            "score": score,
            "is_stretch": stretch,
            "signals": signals,
            "computed_at": datetime.now(timezone.utc),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top_matches = scored[:TOP_N_STRUCTURED]

    # Stage 3: AI refinement on top 20
    if run_ai and top_matches:
        ai_results = await _ai_refine(user, candidate_jobs, top_matches[:TOP_N_AI])
        for match in top_matches:
            ai = ai_results.get(match["job_id"])
            if ai:
                match["ai_score"] = ai.get("ai_score")
                match["ai_reason"] = ai.get("reason")
                match["skills_gap"] = ai.get("skills_gap", [])
                match["strengths"] = ai.get("strengths", [])

        # Re-sort by AI score where available, fall back to structured score
        top_matches.sort(key=lambda x: x.get("ai_score") or x["score"], reverse=True)

    return top_matches


def _collect_user_titles(user: dict) -> List[str]:
    """Collect role_focus + any other title signals."""
    titles = []
    if user.get("role_focus"):
        titles.append(user["role_focus"])
    return titles


async def _ai_refine(
    user: dict, all_jobs: List[dict], top_matches: List[dict]
) -> Dict[str, dict]:
    """Stage 3: Send top matches to OpenAI for scoring + reasoning."""

    if not settings.openai_api_key and not settings.gemini_api_key:
        return {}

    job_lookup = {j["_id"]: j for j in all_jobs}

    user_summary = (
        f"Role: {user.get('role_focus', 'Unknown')}. "
        f"Skills: {', '.join((user.get('skills') or [])[:15])}. "
        f"Experience: {user.get('years_of_experience', '?')} years. "
        f"Seniority: {user.get('seniority_level', 'Unknown')}. "
        f"Location: {user.get('location', 'Unknown')}."
    )

    jobs_block = []
    for match in top_matches:
        job = job_lookup.get(match["job_id"])
        if not job:
            continue
        jobs_block.append({
            "job_id": match["job_id"],
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "skills": (job.get("skills") or [])[:10],
            "seniority": job.get("seniority_level", ""),
            "country": job.get("country", ""),
            "is_remote": job.get("is_remote", False),
            "required_years": job.get("required_experience_years"),
        })

    if not jobs_block:
        return {}

    prompt = (
        f"Candidate profile: {user_summary}\n\n"
        f"Jobs to evaluate:\n{json.dumps(jobs_block, default=str)}\n\n"
        "For each job, return a JSON array with objects containing:\n"
        '- "job_id": the job_id\n'
        '- "ai_score": 0-100 match score\n'
        '- "reason": one sentence explaining the match\n'
        '- "skills_gap": list of skills the candidate is missing\n'
        '- "strengths": list of candidate skills that are relevant\n'
        "Return ONLY the JSON array."
    )

    try:
        result = _call_ai(prompt)
        if isinstance(result, list):
            return {item["job_id"]: item for item in result if "job_id" in item}
    except Exception as e:
        logger.error("AI refinement failed: %s", e)

    return {}


def _call_ai(prompt: str) -> Any:
    """Call whichever AI provider is configured."""
    if settings.openai_api_key:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a job matching assistant. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )
        parsed = json.loads(response.choices[0].message.content)
        if isinstance(parsed, dict) and "matches" in parsed:
            return parsed["matches"]
        if isinstance(parsed, list):
            return parsed
        return []
    elif settings.gemini_api_key:
        import google.generativeai as genai
        from google.generativeai.types import GenerationConfig
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            generation_config=GenerationConfig(response_mime_type="application/json", temperature=0),
        )
        response = model.generate_content(prompt)
        return json.loads(response.text)
    return []


async def _get_matching_users() -> List[dict]:
    """Fetch all users with job_matching_enabled=true."""
    cursor = db.db["users"].find(
        {"job_matching_enabled": True, "skills": {"$exists": True, "$ne": []}},
        {"skills": 1, "role_focus": 1, "seniority_level": 1, "location": 1,
         "years_of_experience": 1, "email": 1, "credits": 1},
    )
    return await cursor.to_list(length=None)


async def _get_active_jobs() -> List[dict]:
    """Fetch all jobs from the last 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    cursor = db.jobs.find(
        {"posted_at": {"$gte": cutoff}},
        {"raw_data": 0, "description": 0},
    )
    return await cursor.to_list(length=None)


async def _deduct_credits(user_id: str, email: str) -> bool:
    """Deduct matching credits from user. Returns False if insufficient."""
    user = await db.db["users"].find_one({"_id": user_id})
    if not user or user.get("credits", 0) < MATCH_CREDIT_COST:
        return False

    new_balance = user["credits"] - MATCH_CREDIT_COST
    result = await db.db["users"].update_one(
        {"_id": user_id, "credits": {"$gte": MATCH_CREDIT_COST}},
        {"$inc": {"credits": -MATCH_CREDIT_COST}},
    )
    if result.modified_count == 0:
        return False

    await db.db["ledger"].insert_one({
        "user_id": user_id,
        "email": email,
        "spent_for": "job_matching",
        "credit_spent": -MATCH_CREDIT_COST,
        "running_balance": new_balance,
        "created_at": datetime.now(timezone.utc),
    })
    return True


async def _save_matches(user_id: str, matches: List[dict]) -> None:
    """Delete old matches and insert new ones for a user."""
    await db.db["job_matches"].delete_many({"user_id": user_id})
    if matches:
        await db.db["job_matches"].insert_many(matches)
