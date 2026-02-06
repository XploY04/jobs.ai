"""Gemini AI processor for advanced job enrichment"""

import json
from typing import Dict, Any, Optional
import google.generativeai as genai
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AIProcessor:
    """Use Gemini AI for advanced job analysis"""

    def __init__(self):
        """Initialize Gemini AI"""
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.enabled = True
            logger.info("Gemini AI processor initialized")
        else:
            self.enabled = False
            logger.warning("Gemini API key not set - AI enrichment disabled")

    def enrich_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Gemini to extract additional insights from job posting
        
        Returns dict with:
        - extracted_skills: List of technical skills
        - seniority_level: junior, mid, senior, staff, principal
        - work_arrangement: remote, hybrid, onsite
        - visa_sponsorship: yes, no, unknown
        - required_years: estimated years of experience
        """
        
        if not self.enabled:
            return {}
        
        try:
            prompt = self._build_enrichment_prompt(job)
            response = self.model.generate_content(prompt)
            
            # Log the raw response for debugging
            response_text = response.text.strip()
            logger.debug(f"Raw AI response: {response_text[:200]}")
            
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            logger.info(f"AI enriched job {job.get('id', 'unknown')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Response was: {response_text if 'response_text' in locals() else 'N/A'}")
            return {}
        except Exception as e:
            logger.error(f"AI enrichment failed: {e}")
            return {}

    def _build_enrichment_prompt(self, job: Dict[str, Any]) -> str:
        """Build prompt for Gemini"""
        
        title = job.get('title', '')
        description = job.get('description', '')[:2000]  # Truncate for token limits
        company = job.get('company', '')
        
        return f"""Analyze this job posting and extract structured information. Return ONLY valid JSON.

Job Title: {title}
Company: {company}
Description: {description}

Extract and return in this exact JSON format:
{{
  "extracted_skills": ["skill1", "skill2", ...],
  "seniority_level": "junior|mid|senior|staff|principal",
  "work_arrangement": "remote|hybrid|onsite",
  "visa_sponsorship": "yes|no|unknown",
  "required_years": 0,
  "key_responsibilities": ["resp1", "resp2", ...],
  "nice_to_have": ["skill1", "skill2", ...],
  "benefits_mentioned": ["benefit1", "benefit2", ...]
}}

Rules:
- extracted_skills: Top 10 technical skills/technologies mentioned
- seniority_level: Based on title and requirements
- work_arrangement: Look for remote/hybrid/office keywords
- visa_sponsorship: Only "yes" if explicitly mentioned
- required_years: Estimate from "X+ years experience" or seniority
- Keep arrays concise (max 5-10 items each)
- Return ONLY the JSON, no other text"""

    def extract_insights_batch(self, jobs: list[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Process multiple jobs efficiently
        Returns dict mapping job_id -> insights
        """
        
        if not self.enabled:
            return {}
        
        results = {}
        
        for job in jobs:
            job_id = job.get('id')
            if job_id:
                insights = self.enrich_job(job)
                if insights:
                    results[job_id] = insights
        
        return results

    def categorize_job_role(self, title: str, description: str) -> str:
        """
        Use AI to categorize job into specific role type
        More nuanced than rule-based categorization
        """
        
        if not self.enabled:
            return 'general'
        
        try:
            prompt = f"""Categorize this job role into ONE of these categories:
- frontend
- backend
- fullstack
- mobile
- devops
- sre
- data_engineer
- data_scientist
- ml_engineer
- security
- qa
- architect
- manager
- general

Title: {title}
Description: {description[:500]}

Return ONLY the category name, nothing else."""

            response = self.model.generate_content(prompt)
            category = response.text.strip().lower()
            
            valid_categories = [
                'frontend', 'backend', 'fullstack', 'mobile', 'devops', 'sre',
                'data_engineer', 'data_scientist', 'ml_engineer', 'security',
                'qa', 'architect', 'manager', 'general'
            ]
            
            return category if category in valid_categories else 'general'
            
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            return 'general'
