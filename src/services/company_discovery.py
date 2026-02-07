"""
Company Discovery Service — uses SerpAPI to discover company slugs
on ATS platforms (Greenhouse, Lever, Ashby, Workable, SmartRecruiters)
and stores them in the discovered_companies DB table.

Design:
  - Each run spends ≤30 SerpAPI queries (100/month free tier)
  - Slugs accumulate over time → more companies discovered each day
  - ATS scraper reads slugs from DB and hits live APIs
"""

import re
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

import aiohttp
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.database.models import DiscoveredCompany
from src.database.operations import db
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Platform definitions  (slug regex + google site: filter)
# ---------------------------------------------------------------------------
PLATFORM_CONFIG = {
    "greenhouse": {
        "site_filter": "site:boards.greenhouse.io",
        "slug_pattern": re.compile(r"boards\.greenhouse\.io/([a-zA-Z0-9_-]+)"),
    },
    "lever": {
        "site_filter": "site:jobs.lever.co",
        "slug_pattern": re.compile(r"jobs\.lever\.co/([a-zA-Z0-9_-]+)"),
    },
    "ashby": {
        "site_filter": "site:jobs.ashbyhq.com",
        "slug_pattern": re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)"),
    },
    "workable": {
        "site_filter": "site:apply.workable.com",
        "slug_pattern": re.compile(r"apply\.workable\.com/([a-zA-Z0-9_-]+)"),
    },
    "smartrecruiters": {
        "site_filter": "site:jobs.smartrecruiters.com",
        "slug_pattern": re.compile(r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_-]+)"),
    },
}

# Search terms to discover companies hiring for tech roles
DISCOVERY_QUERIES = [
    "software engineer",
    "backend engineer",
    "devops engineer",
    "frontend engineer",
    "data engineer",
    "SRE",
    "platform engineer",
    "python developer",
    "golang developer",
    "kubernetes",
    "machine learning engineer",
    "cloud engineer",
    "fullstack developer",
    "infrastructure engineer",
    "engineering manager",
]

# Manual seed list — known working slugs to bootstrap the system
SEED_COMPANIES: Dict[str, List[Tuple[str, str]]] = {
    "greenhouse": [
        ("gitlab", "GitLab"),
        ("grammarly", "Grammarly"),
        ("airtable", "Airtable"),
        ("twilio", "Twilio"),
        ("postman", "Postman"),
        ("hubspot", "HubSpot"),
        ("hashicorp", "HashiCorp"),
        ("datadog", "Datadog"),
        ("cloudflare", "Cloudflare"),
        ("squareup", "Square"),
        ("dropbox", "Dropbox"),
        ("benchling", "Benchling"),
        ("affirm", "Affirm"),
        ("compass", "Compass"),
        ("stripe", "Stripe"),
        ("coinbase", "Coinbase"),
        ("doordash", "DoorDash"),
        ("figma", "Figma"),
        ("discord", "Discord"),
        ("notion", "Notion"),
        ("linear", "Linear"),
        ("plaid", "Plaid"),
        ("brex", "Brex"),
        ("snyk", "Snyk"),
        ("gusto", "Gusto"),
        ("flexport", "Flexport"),
        ("verkada", "Verkada"),
        ("faire", "Faire"),
        ("canva", "Canva"),
        ("mongodb", "MongoDB"),
        ("databricks", "Databricks"),
        ("elastic", "Elastic"),
        ("confluent", "Confluent"),
        ("supabase", "Supabase"),
        ("vercel", "Vercel"),
        ("netlify", "Netlify"),
        ("render", "Render"),
        ("neon", "Neon"),
        ("ramp", "Ramp"),
        ("mercury", "Mercury"),
        ("deel", "Deel"),
        ("miro", "Miro"),
        ("amplitude", "Amplitude"),
        ("pagerduty", "PagerDuty"),
        ("algolia", "Algolia"),
    ],
    "lever": [
        ("spotify", "Spotify"),
        ("labelbox", "Labelbox"),
    ],
    "ashby": [
        ("anthropic", "Anthropic"),
        ("perplexity-ai", "Perplexity"),
        ("modal", "Modal"),
        ("watershed", "Watershed"),
        ("ramp", "Ramp"),
        ("assembled", "Assembled"),
        ("cohere", "Cohere"),
        ("huggingface", "Hugging Face"),
        ("weights-and-biases", "Weights & Biases"),
    ],
    "workable": [
        ("sentry", "Sentry"),
        ("mux", "Mux"),
        ("permit-io", "Permit.io"),
    ],
    "smartrecruiters": [
        ("Visa", "Visa"),
        ("BOSCH", "Bosch"),
    ],
}

# Budget: max SerpAPI queries per discovery run
# Free tier = 100/month, so ~3/day is sustainable
QUERIES_PER_RUN = 10


class CompanyDiscoveryService:
    """
    Discovers company slugs on ATS platforms using SerpAPI.
    Stores results in discovered_companies DB table for the ATS scraper.
    """

    SERPAPI_URL = "https://serpapi.com/search.json"

    def __init__(self) -> None:
        self.serpapi_key = settings.serpapi_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_discovery(self) -> Dict[str, int]:
        """
        Main entry point.  Seeds known companies, then runs SerpAPI
        discovery.  Returns {platform: count_new_slugs}.
        """
        stats: Dict[str, int] = {}

        # 1. Seed known companies (first run only; upsert = no-op later)
        seeded = await self._seed_known_companies()
        logger.info("Seeded %d known companies", seeded)

        # 2. SerpAPI discovery (if key configured)
        if self.serpapi_key:
            discovered = await self._serpapi_discovery()
            for platform, count in discovered.items():
                stats[platform] = stats.get(platform, 0) + count
            logger.info("SerpAPI discovery found: %s", discovered)
        else:
            logger.warning("SERPAPI_KEY not configured — using seed list only")

        total = await self._count_active_companies()
        logger.info("Total active companies in DB: %d", total)
        return stats

    async def get_companies_for_platform(self, platform: str) -> List[Dict[str, Any]]:
        """Return all active company slugs for a given ATS platform."""
        if not db.session_maker:
            return []
        async with db.session_maker() as session:
            stmt = (
                select(DiscoveredCompany)
                .where(DiscoveredCompany.platform == platform)
                .where(DiscoveredCompany.is_active == True)  # noqa: E712
                .order_by(DiscoveredCompany.job_count.desc())
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {"slug": r.slug, "company_name": r.company_name, "platform": r.platform}
                for r in rows
            ]

    async def mark_company_fetched(
        self, platform: str, slug: str, job_count: int
    ) -> None:
        """Update last_fetched_at and job_count after scraping."""
        if not db.session_maker:
            return
        async with db.session_maker() as session:
            stmt = (
                select(DiscoveredCompany)
                .where(DiscoveredCompany.platform == platform)
                .where(DiscoveredCompany.slug == slug)
            )
            result = await session.execute(stmt)
            company = result.scalar_one_or_none()
            if company:
                company.last_fetched_at = datetime.now(timezone.utc)
                company.job_count = job_count
                await session.commit()

    async def mark_company_inactive(self, platform: str, slug: str) -> None:
        """Mark a company as inactive (404, dead board)."""
        if not db.session_maker:
            return
        async with db.session_maker() as session:
            stmt = (
                select(DiscoveredCompany)
                .where(DiscoveredCompany.platform == platform)
                .where(DiscoveredCompany.slug == slug)
            )
            result = await session.execute(stmt)
            company = result.scalar_one_or_none()
            if company:
                company.is_active = False
                await session.commit()

    # ------------------------------------------------------------------
    # Seed known companies
    # ------------------------------------------------------------------

    async def _seed_known_companies(self) -> int:
        """Insert seed companies into DB (upsert to avoid duplicates)."""
        if not db.session_maker:
            return 0

        count = 0
        async with db.session_maker() as session:
            for platform, companies in SEED_COMPANIES.items():
                for slug, name in companies:
                    stmt = (
                        pg_insert(DiscoveredCompany)
                        .values(
                            slug=slug,
                            platform=platform,
                            company_name=name,
                            discovered_via="seed",
                            is_active=True,
                        )
                        .on_conflict_do_nothing(
                            index_elements=["platform", "slug"]
                        )
                    )
                    result = await session.execute(stmt)
                    if result.rowcount:
                        count += 1
            await session.commit()
        return count

    # ------------------------------------------------------------------
    # SerpAPI discovery
    # ------------------------------------------------------------------

    async def _serpapi_discovery(self) -> Dict[str, int]:
        """Use SerpAPI to find new company slugs on ATS platforms."""
        stats: Dict[str, int] = {p: 0 for p in PLATFORM_CONFIG}
        queries_used = 0

        async with aiohttp.ClientSession() as session:
            for platform, cfg in PLATFORM_CONFIG.items():
                if queries_used >= QUERIES_PER_RUN:
                    break

                # Use a subset of discovery queries per platform
                platform_budget = max(1, QUERIES_PER_RUN // len(PLATFORM_CONFIG))
                queries_for_platform = DISCOVERY_QUERIES[:platform_budget]

                for query_term in queries_for_platform:
                    if queries_used >= QUERIES_PER_RUN:
                        break

                    full_query = f"{query_term} {cfg['site_filter']}"
                    results = await self._execute_serpapi_search(session, full_query)
                    queries_used += 1

                    # Extract slugs from results
                    new_slugs = self._extract_slugs(results, cfg["slug_pattern"])

                    # Save new slugs to DB
                    for slug in new_slugs:
                        saved = await self._save_slug(platform, slug)
                        if saved:
                            stats[platform] += 1
                            logger.info("Discovered new %s company: %s", platform, slug)

                    # Rate limit
                    await asyncio.sleep(0.5)

        logger.info("SerpAPI discovery used %d/%d queries", queries_used, QUERIES_PER_RUN)
        return stats

    async def _execute_serpapi_search(
        self, session: aiohttp.ClientSession, query: str
    ) -> List[Dict[str, Any]]:
        """Execute a single SerpAPI Google search query."""
        params = {
            "api_key": self.serpapi_key,
            "engine": "google",
            "q": query,
            "num": 10,
        }

        try:
            async with session.get(
                self.SERPAPI_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 429:
                    logger.warning("SerpAPI rate limit hit")
                    return []
                if resp.status == 401:
                    logger.error("SerpAPI invalid API key")
                    return []
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("SerpAPI HTTP %s: %s", resp.status, body[:200])
                    return []
                data = await resp.json()
                return data.get("organic_results", [])
        except Exception as exc:
            logger.error("SerpAPI error for '%s': %s", query[:60], exc)
            return []

    def _extract_slugs(
        self, results: List[Dict[str, Any]], pattern: re.Pattern
    ) -> Set[str]:
        """Extract unique company slugs from search results."""
        slugs: Set[str] = set()
        for item in results:
            url = item.get("link", "")
            match = pattern.search(url)
            if match:
                slug = match.group(1).lower()
                # Filter out obvious non-company slugs
                if slug not in {
                    "api", "www", "docs", "help", "support", "blog", "embed",
                    "jobs", "careers", "about", "login", "signup", "register",
                }:
                    slugs.add(slug)
        return slugs

    async def _save_slug(self, platform: str, slug: str) -> bool:
        """Save a discovered slug to DB. Returns True if new."""
        if not db.session_maker:
            return False

        async with db.session_maker() as session:
            stmt = (
                pg_insert(DiscoveredCompany)
                .values(
                    slug=slug,
                    platform=platform,
                    company_name=slug.replace("-", " ").title(),
                    discovered_via="serpapi",
                    is_active=True,
                )
                .on_conflict_do_nothing(index_elements=["platform", "slug"])
            )
            result = await session.execute(stmt)
            await session.commit()
            return bool(result.rowcount)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _count_active_companies(self) -> int:
        """Count total active companies across all platforms."""
        if not db.session_maker:
            return 0
        async with db.session_maker() as session:
            from sqlalchemy import func as sqlfunc

            stmt = select(sqlfunc.count()).select_from(DiscoveredCompany).where(
                DiscoveredCompany.is_active == True  # noqa: E712
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
