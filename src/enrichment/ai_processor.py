"""Gemini AI processor — the ONLY data transformation layer.

Takes raw API data from any source and outputs the final structured job schema.
No normalizer needed. Gemini handles schema mapping for ALL sources."""

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# The one true schema — every job ends up in this shape
OUTPUT_SCHEMA = {
    "title": "string — job title",
    "company": "string — company/employer name",
    "company_logo": "string|null — URL to company logo image",
    "company_website": "string|null — company website URL",
    "short_description": "string — 2-3 sentence summary of the role",
    "country": "string|null — ISO 3166-1 country code (US, GB, DE, etc.) or full name",
    "city": "string|null — city name",
    "state": "string|null — state/region/province",
    "is_remote": "boolean — true if remote work is available",
    "work_arrangement": "remote|hybrid|onsite",
    "employment_type": "FULLTIME|PARTTIME|CONTRACT|INTERN|TEMPORARY",
    "seniority_level": "intern|junior|mid|senior|staff|principal|lead|manager",
    "department": "string|null — e.g. Engineering, Marketing, Data",
    "category": "backend|frontend|fullstack|mobile|devops|sre|data|ml|security|qa|design|product|general",
    "salary_min": "number|null — minimum salary (numeric only)",
    "salary_max": "number|null — maximum salary (numeric only)",
    "salary_currency": "string|null — ISO currency code (USD, EUR, GBP, etc.)",
    "salary_period": "year|month|week|hour|null",
    "skills": ["string — technical skills and technologies mentioned"],
    "required_experience_years": "integer|null — minimum years of experience required",
    "required_education": "string|null — degree level if mentioned (Bachelor's, Master's, PhD, etc.)",
    "key_responsibilities": ["string — top 5-8 responsibilities"],
    "nice_to_have_skills": ["string — bonus/preferred skills"],
    "benefits": ["string — benefits and perks mentioned"],
    "visa_sponsorship": "yes|no|unknown",
    "application_deadline": "YYYY-MM-DD|null — explicit deadline/closing date if mentioned",
    "tags": ["string — relevant tags/categories from the source data"],
}


class AIProcessor:
    """Use Gemini AI to transform raw job data into structured schema.
    
    This replaces both the old normalizer AND enrichment step.
    Raw API data goes in → fully structured job comes out.
    """

    def __init__(self):
        """Initialize Gemini AI"""
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.enabled = True
            logger.info("Gemini AI processor initialized")
        else:
            self.enabled = False
            logger.warning("Gemini API key not set - AI processing disabled")

    def process_raw_job(self, source: str, raw_job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a single raw job from any source into the final structured schema.
        
        This is the ONLY transformation layer. No normalizer needed.
        Gemini sees ALL the raw data and extracts everything intelligently.
        """
        if not self.enabled:
            return None

        try:
            prompt = self._build_transform_prompt(source, raw_job)
            response = self.model.generate_content(prompt)

            response_text = response.text.strip()
            logger.debug(f"Raw AI response: {response_text[:200]}")

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)
            logger.info(f"AI processed job: {result.get('title', 'unknown')[:60]} @ {result.get('company', 'unknown')}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Response was: {response_text if 'response_text' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            return None

    def _build_transform_prompt(self, source: str, raw_job: Dict[str, Any]) -> str:
        """Build the mega-prompt that transforms raw data into structured schema."""

        # Truncate very long descriptions to stay within token limits
        raw_str = json.dumps(raw_job, default=str, ensure_ascii=False)
        if len(raw_str) > 6000:
            raw_str = raw_str[:6000] + "... [truncated]"

        return f"""You are a job data extraction engine. Given raw job data from the source "{source}", extract ALL available information into the exact JSON schema below.

RAW JOB DATA (source: {source}):
{raw_str}

OUTPUT SCHEMA — return ONLY valid JSON matching this structure:
{{
  "title": "string",
  "company": "string",
  "company_logo": "string or null",
  "company_website": "string or null",
  "short_description": "2-3 sentence summary of the role",
  "country": "ISO country code or full name, or null",
  "city": "city name or null",
  "state": "state/region or null",
  "is_remote": true/false,
  "work_arrangement": "remote|hybrid|onsite",
  "employment_type": "FULLTIME|PARTTIME|CONTRACT|INTERN|TEMPORARY",
  "seniority_level": "intern|junior|mid|senior|staff|principal|lead|manager",
  "department": "department name or null",
  "category": "backend|frontend|fullstack|mobile|devops|sre|data|ml|security|qa|design|product|general",
  "salary_min": number or null,
  "salary_max": number or null,
  "salary_currency": "USD|EUR|GBP|etc or null",
  "salary_period": "year|month|week|hour|null",
  "skills": ["skill1", "skill2", ...],
  "required_experience_years": number or null,
  "required_education": "Bachelor's|Master's|PhD|etc or null",
  "key_responsibilities": ["resp1", "resp2", ...],
  "nice_to_have_skills": ["skill1", "skill2", ...],
  "benefits": ["benefit1", "benefit2", ...],
  "visa_sponsorship": "yes|no|unknown",
  "application_deadline": "YYYY-MM-DD or null",
  "tags": ["tag1", "tag2", ...]
}}

RULES:
1. Extract EVERYTHING available from the raw data. Do NOT leave fields null if the data is present.
2. For "title": Use the actual job title. Clean up any formatting artifacts.
3. For "company": Extract company/employer name. Use "Unknown" only if truly absent.
4. For "company_logo": Look for logo/image URLs in the raw data (e.g. employer_logo, company_logo, logo fields).
5. For "company_website": Look for employer/company website URLs.
6. For "short_description": Generate a concise 2-3 sentence summary from the full description.
7. For location fields: Parse location strings intelligently. "San Francisco, CA" → city="San Francisco", state="CA", country="US". "Remote" → is_remote=true.
8. For "is_remote": true if the job mentions remote work, OR if the source is "remoteok" (all RemoteOK jobs are remote), OR if job_is_remote=true.
9. For "work_arrangement": Determine from description context. Default to "onsite" if unclear, "remote" for remoteok source.
10. For "category": Classify based on ACTUAL role responsibilities, not just keywords. Sales/marketing/HR roles = "general". Only use tech categories for actual tech roles.
11. For "salary_min"/"salary_max": Extract NUMERIC values only (no currency symbols). If a single salary is mentioned, use it for both min and max.
12. For "salary_period": Critical — is the salary per year, month, week, or hour? Look for clues like "/yr", "annual", "per hour", "p.a.", salary range size (>$30k likely annual, <$100 likely hourly).
13. For "skills": Extract ALL technical skills, programming languages, frameworks, tools, platforms mentioned. Max 20.
14. For "required_experience_years": Extract from patterns like "3+ years", "5-7 years experience". Use the MINIMUM mentioned.
15. For "application_deadline": ONLY extract explicit deadlines ("Apply by March 15", "Closing date: 2026-03-01"). null if not mentioned.
16. For "tags": Include any categories, tags, or labels from the source data (e.g. RemoteOK tags, RSS categories).
17. For "benefits": Extract benefits like "health insurance", "401k", "unlimited PTO", "equity", etc.
18. For "visa_sponsorship": "yes" ONLY if explicitly mentioned. "unknown" if not discussed.
19. Keep arrays concise — max 20 skills, max 8 responsibilities, max 10 benefits.
20. Return ONLY the JSON object, no other text or markdown."""

    def process_batch(self, source: str, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of raw jobs from a single source."""
        results = []
        for raw_job in raw_jobs:
            result = self.process_raw_job(source, raw_job)
            if result:
                results.append(result)
        return results
