"""Quality scoring for job postings"""

from typing import Dict, Any


class QualityScorer:
    """Score job quality based on completeness and information richness"""

    def score(self, job: Dict[str, Any]) -> int:
        """
        Calculate quality score (0-100) based on:
        - Description completeness
        - Salary information
        - Location details
        - Company information
        - Job details
        """
        
        score = 0
        
        # Description quality (0-25 points)
        description = job.get('description', '')
        if description:
            desc_length = len(description)
            if desc_length > 2000:
                score += 25
            elif desc_length > 1000:
                score += 20
            elif desc_length > 500:
                score += 15
            elif desc_length > 200:
                score += 10
            else:
                score += 5
        
        # Salary information (0-25 points)
        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')
        
        if salary_min and salary_max:
            score += 25
        elif salary_min or salary_max:
            score += 15
        
        # Location details (0-20 points)
        location = job.get('location', {})
        if isinstance(location, dict):
            loc_score = 0
            if location.get('city'):
                loc_score += 5
            if location.get('country'):
                loc_score += 5
            if 'remote' in location:
                loc_score += 10
            score += loc_score
        
        # Company information (0-15 points)
        company = job.get('company', '')
        if company and len(company) > 2:
            score += 15
        
        # Employment type (0-10 points)
        if job.get('employment_type'):
            score += 10
        
        # Apply URL (0-5 points)
        if job.get('apply_url'):
            score += 5
        
        return min(score, 100)

    def assess_completeness(self, job: Dict[str, Any]) -> Dict[str, bool]:
        """Check which fields are present"""
        
        return {
            'has_description': bool(job.get('description')),
            'has_salary': bool(job.get('salary_min') or job.get('salary_max')),
            'has_location': bool(job.get('location')),
            'has_company': bool(job.get('company')),
            'has_employment_type': bool(job.get('employment_type')),
            'has_apply_url': bool(job.get('apply_url'))
        }
