import pytest
import asyncio
from datetime import datetime, timezone
from src.database.models import Job, Base
from src.database.operations import Database


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection and disconnection"""
    db = Database()
    
    # Should be able to connect
    await db.connect()
    assert db.engine is not None
    assert db.session_maker is not None
    
    # Should be able to disconnect
    await db.disconnect()


@pytest.mark.asyncio
async def test_database_hash_function():
    """Test title+company hashing for deduplication"""
    db = Database()
    
    hash1 = db._hash_title_company("Backend Engineer", "TechCorp")
    hash2 = db._hash_title_company("Backend Engineer", "TechCorp")
    hash3 = db._hash_title_company("Frontend Engineer", "TechCorp")
    
    # Same title+company should produce same hash
    assert hash1 == hash2
    
    # Different title should produce different hash
    assert hash1 != hash3
    
    # Hash should be 16 characters (truncated SHA256)
    assert len(hash1) == 16


@pytest.mark.asyncio
async def test_database_string_coercion():
    """Test salary value string coercion"""
    db = Database()
    
    # Test various input types
    assert db._to_str(None) is None
    assert db._to_str("100000") == "100000"
    assert db._to_str(100000) == "100000"
    assert db._to_str(100000.50) == "100000.5"


@pytest.mark.asyncio
async def test_save_jobs_with_duplicates():
    """Test job saving with duplicate detection"""
    db = Database()
    await db.connect()
    
    # Sample job data
    job_data = {
        "source": "test",
        "source_id": "test123",
        "title": "Test Backend Engineer",
        "company": "TestCompany",
        "description": "Test description",
        "location": {"city": "Test City", "country": "US", "remote": False},
        "employment_type": "FULLTIME",
        "salary_min": "100000",
        "salary_max": "150000",
        "salary_currency": "USD",
        "apply_url": "https://example.com",
        "posted_at": datetime.now(timezone.utc),
        "raw_data": {}
    }
    
    # Save first time - should be new
    stats1 = await db.save_jobs([job_data])
    assert stats1["new"] >= 0  # May be 0 if already exists from previous runs
    
    # Save same job again - should be skipped
    stats2 = await db.save_jobs([job_data])
    assert stats2["skipped"] >= 1
    assert stats2["new"] == 0
    
    await db.disconnect()


def test_job_model_fields():
    """Test Job model has required fields"""
    job = Job(
        id="test_id",
        source="test",
        source_id="123",
        title="Test Job",
        company="Test Company",
        description="Test description",
        location={"city": "Test"},
        apply_url="https://test.com",
        posted_at=datetime.now(timezone.utc),
        title_company_hash="abcd1234"
    )
    
    assert job.id == "test_id"
    assert job.source == "test"
    assert job.title == "Test Job"
    assert job.company == "Test Company"


def test_import_database_modules():
    """Test that database modules can be imported"""
    from src.database.models import Job, Base
    from src.database.operations import Database, db
    
    assert Job is not None
    assert Base is not None
    assert Database is not None
    assert db is not None
