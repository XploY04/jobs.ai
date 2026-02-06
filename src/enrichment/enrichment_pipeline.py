"""Complete enrichment pipeline combining rule-based and AI approaches"""

from typing import Dict, Any, List
from src.enrichment.skills_extractor import SkillsExtractor
from src.enrichment.quality_scorer import QualityScorer
from src.enrichment.urgency_detector import UrgencyDetector
from src.enrichment.ai_processor import AIProcessor
from src.utils.logger import setup_logger
from src.utils.config import settings

logger = setup_logger(__name__)


class EnrichmentPipeline:
    """
    Complete job enrichment pipeline
    
    Phase A: Rule-based (fast, free)
    - Extract tech skills
    - Calculate quality score
    - Detect urgency
    - Basic categorization
    
    Phase B: AI-powered (optional, uses Gemini)
    - Advanced skill extraction
    - Seniority detection
    - Work arrangement parsing
    - Visa sponsorship detection
    """

    def __init__(self, use_ai: bool = None):
        """
        Initialize enrichment pipeline
        
        Args:
            use_ai: Enable AI enrichment (uses Gemini API). 
                   If None, uses ENABLE_AI_ENRICHMENT from config
        """
        self.skills_extractor = SkillsExtractor()
        self.quality_scorer = QualityScorer()
        self.urgency_detector = UrgencyDetector()
        
        # AI processor (optional)
        self.use_ai = use_ai if use_ai is not None else settings.enable_ai_enrichment
        self.ai_processor = AIProcessor() if self.use_ai else None
        
        logger.info(f"Enrichment pipeline initialized (AI: {'enabled' if self.use_ai else 'disabled'})")

    def enrich(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single job with all available insights
        
        Returns enriched job data with additional fields:
        - skills: List[str]
        - ai_category: str
        - ai_quality_score: int
        - ai_urgency: str
        - ai_extracted_deadline: datetime (optional)
        - ai_deadline_confidence: str
        - Plus AI-powered fields if enabled
        """
        
        enriched = job.copy()
        
        # Phase A: Rule-based enrichment (always runs)
        title = job.get('title', '')
        description = job.get('description', '')
        
        # Extract skills
        skills = self.skills_extractor.extract(title, description)
        enriched['skills'] = skills
        
        # Categorize role
        category = self.skills_extractor.categorize_role(title, description, skills)
        enriched['ai_category'] = category
        
        # Calculate quality score
        quality_score = self.quality_scorer.score(job)
        enriched['ai_quality_score'] = quality_score
        
        # Detect urgency
        urgency = self.urgency_detector.detect_urgency(title, description)
        enriched['ai_urgency'] = urgency
        
        # Extract deadline
        deadline, confidence = self.urgency_detector.extract_deadline(description)
        if deadline:
            enriched['ai_extracted_deadline'] = deadline
            enriched['ai_deadline_confidence'] = confidence
        
        # Phase B: AI enrichment (optional)
        if self.use_ai and self.ai_processor and self.ai_processor.enabled:
            try:
                ai_insights = self.ai_processor.enrich_job(job)
                
                if ai_insights:
                    # Merge AI insights (prefixed with ai_)
                    for key, value in ai_insights.items():
                        enriched[f'ai_{key}'] = value
                    
                    # Override category with AI if available
                    if ai_insights.get('seniority_level'):
                        enriched['ai_seniority'] = ai_insights['seniority_level']
                        
            except Exception as e:
                logger.error(f"AI enrichment failed for job {job.get('id')}: {e}")
        
        return enriched

    def enrich_batch(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich multiple jobs efficiently
        
        For rule-based: Processes each job
        For AI: Can batch process for efficiency
        """
        
        enriched_jobs = []
        
        logger.info(f"Enriching {len(jobs)} jobs...")
        
        for i, job in enumerate(jobs):
            try:
                enriched = self.enrich(job)
                enriched_jobs.append(enriched)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Enriched {i + 1}/{len(jobs)} jobs")
                    
            except Exception as e:
                logger.error(f"Failed to enrich job {job.get('id', 'unknown')}: {e}")
                enriched_jobs.append(job)  # Add original if enrichment fails
        
        logger.info(f"Enrichment complete: {len(enriched_jobs)}/{len(jobs)} successful")
        
        return enriched_jobs

    def get_enrichment_stats(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about enrichment quality"""
        
        if not jobs:
            return {}
        
        total = len(jobs)
        
        with_skills = sum(1 for j in jobs if j.get('skills'))
        with_category = sum(1 for j in jobs if j.get('ai_category'))
        with_quality = sum(1 for j in jobs if j.get('ai_quality_score'))
        with_urgency = sum(1 for j in jobs if j.get('ai_urgency'))
        with_deadline = sum(1 for j in jobs if j.get('ai_extracted_deadline'))
        
        avg_quality = sum(j.get('ai_quality_score', 0) for j in jobs) / total if total > 0 else 0
        avg_skills = sum(len(j.get('skills', [])) for j in jobs) / total if total > 0 else 0
        
        return {
            'total_jobs': total,
            'enrichment_coverage': {
                'skills': f"{with_skills}/{total} ({with_skills/total*100:.1f}%)",
                'category': f"{with_category}/{total} ({with_category/total*100:.1f}%)",
                'quality_score': f"{with_quality}/{total} ({with_quality/total*100:.1f}%)",
                'urgency': f"{with_urgency}/{total} ({with_urgency/total*100:.1f}%)",
                'deadline': f"{with_deadline}/{total} ({with_deadline/total*100:.1f}%)"
            },
            'averages': {
                'quality_score': round(avg_quality, 1),
                'skills_per_job': round(avg_skills, 1)
            }
        }
