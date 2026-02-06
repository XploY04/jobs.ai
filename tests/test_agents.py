import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.agents.remoteok import RemoteOKFetcher
from src.agents.jsearch import JSearchFetcher
from src.agents.adzuna import AdzunaFetcher


@pytest.mark.asyncio
async def test_remoteok_fetcher_initialization():
    """Test RemoteOK agent initializes correctly"""
    fetcher = RemoteOKFetcher()
    
    assert fetcher.source_name == "remoteok"
    assert hasattr(fetcher, 'fetch_jobs')


@pytest.mark.asyncio
async def test_jsearch_fetcher_initialization():
    """Test JSearch agent initializes correctly"""
    fetcher = JSearchFetcher()
    
    assert fetcher.source_name == "jsearch"
    assert hasattr(fetcher, 'fetch_jobs')


@pytest.mark.asyncio
async def test_adzuna_fetcher_initialization():
    """Test Adzuna agent initializes correctly"""
    fetcher = AdzunaFetcher()
    
    assert fetcher.source_name == "adzuna"
    assert hasattr(fetcher, 'fetch_jobs')


@pytest.mark.asyncio
async def test_base_fetcher_keyword_filtering():
    """Test backend/DevOps keyword filtering"""
    from src.agents import BaseFetcher
    
    # Create a concrete implementation for testing
    class TestFetcher(BaseFetcher):
        async def fetch_jobs(self):
            return []
    
    fetcher = TestFetcher("test")
    
    # Test positive matches
    assert fetcher.is_backend_devops_job("Senior Backend Engineer", "")
    assert fetcher.is_backend_devops_job("DevOps Engineer", "")
    assert fetcher.is_backend_devops_job("", "Experience with kubernetes and docker")
    assert fetcher.is_backend_devops_job("SRE", "Site reliability engineering")
    assert fetcher.is_backend_devops_job("Cloud Engineer", "AWS and terraform")
    
    # Test negative matches
    assert not fetcher.is_backend_devops_job("Frontend Developer", "React and Vue.js")
    assert not fetcher.is_backend_devops_job("Marketing Manager", "")
    assert not fetcher.is_backend_devops_job("Data Analyst", "Excel and SQL")


@pytest.mark.asyncio
async def test_remoteok_normalization():
    """Test RemoteOK job normalization"""
    fetcher = RemoteOKFetcher()
    
    # Mock job data from RemoteOK API
    mock_job = {
        "id": "test123",
        "position": "Backend Engineer",
        "company": "TestCorp",
        "description": "Build scalable systems",
        "location": "Remote",
        "url": "https://example.com/apply",
        "epoch": 1707264000,  # Valid timestamp
        "date": "2026-02-07T00:00:00+00:00"
    }
    
    normalized = fetcher._normalize(mock_job)
    
    assert normalized is not None
    assert normalized["source"] == "remoteok"
    assert normalized["source_id"] == "test123"
    assert normalized["title"] == "Backend Engineer"
    assert normalized["company"] == "TestCorp"
    assert normalized["location"]["remote"] is True
    assert "apply_url" in normalized
    assert "posted_at" in normalized


@pytest.mark.asyncio
async def test_jsearch_normalization():
    """Test JSearch job normalization"""
    fetcher = JSearchFetcher()
    
    # Mock job data from JSearch API
    mock_job = {
        "job_id": "abc123",
        "job_title": "DevOps Engineer",
        "employer_name": "TechCompany",
        "job_description": "Manage infrastructure",
        "job_city": "San Francisco",
        "job_country": "US",
        "job_is_remote": True,
        "job_employment_type": "FULLTIME",
        "job_min_salary": 100000,
        "job_max_salary": 150000,
        "job_salary_currency": "USD",
        "job_apply_link": "https://example.com/apply",
        "job_posted_at_datetime_utc": "2026-02-06T10:30:00Z"
    }
    
    normalized = fetcher._normalize(mock_job)
    
    assert normalized is not None
    assert normalized["source"] == "jsearch"
    assert normalized["source_id"] == "abc123"
    assert normalized["title"] == "DevOps Engineer"
    assert normalized["company"] == "TechCompany"
    assert normalized["salary_min"] == 100000
    assert normalized["salary_max"] == 150000
    assert normalized["location"]["remote"] is True


@pytest.mark.asyncio
async def test_adzuna_normalization():
    """Test Adzuna job normalization"""
    fetcher = AdzunaFetcher()
    
    # Mock job data from Adzuna API
    mock_job = {
        "id": "xyz789",
        "title": "Cloud Engineer",
        "company": {"display_name": "CloudCorp"},
        "description": "Build cloud infrastructure",
        "location": {"display_name": "London"},
        "contract_type": "permanent",
        "salary_min": 60000,
        "salary_max": 80000,
        "redirect_url": "https://example.com/apply",
        "created": "2026-02-05T14:20:00Z"
    }
    
    normalized = fetcher._normalize(mock_job, "gb")
    
    assert normalized is not None
    assert normalized["source"] == "adzuna"
    assert normalized["source_id"] == "xyz789"
    assert normalized["title"] == "Cloud Engineer"
    assert normalized["company"] == "CloudCorp"
    assert normalized["salary_currency"] == "GBP"
    assert normalized["location"]["country"] == "GB"


def test_import_all_agents():
    """Test that all agent modules can be imported"""
    from src.agents.remoteok import RemoteOKFetcher
    from src.agents.jsearch import JSearchFetcher
    from src.agents.adzuna import AdzunaFetcher
    from src.agents import BaseFetcher
    
    assert RemoteOKFetcher is not None
    assert JSearchFetcher is not None
    assert AdzunaFetcher is not None
    assert BaseFetcher is not None
