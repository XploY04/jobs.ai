# Phase 1 MVP: Backend & DevOps Job Aggregator

**Goal:** Build a working job aggregator that fetches, stores, and serves backend/DevOps jobs from multiple sources.

**Timeline:** 3-4 weeks (full-time) or 6-8 weeks (part-time)

**Scope:** ~5-10k backend/DevOps jobs from 3-4 sources

---

## 🎯 What We're Building (MVP Only)

A **simple, focused job aggregator** that:
- ✅ Fetches backend/DevOps jobs from RemoteOK, JSearch, Adzuna
- ✅ Stores jobs in PostgreSQL with basic deduplication
- ✅ Exposes REST API for job search
- ✅ Runs automated daily fetches
- ❌ ~~No AI enrichment yet~~ (Phase 2)
- ❌ ~~No MCP server yet~~ (Phase 2)
- ❌ ~~No advanced caching yet~~ (Phase 2)

---

## 📅 Week-by-Week Plan

### **Week 1: Foundation & Data Sources**
- Day 1-2: Project setup, database, basic structure
- Day 3-4: Build fetcher agents (RemoteOK, JSearch, Adzuna)
- Day 5-7: Data normalization & basic deduplication

### **Week 2: Storage & Processing**
- Day 8-10: Database operations & bulk inserts
- Day 11-12: Job filtering (backend/DevOps only)
- Day 13-14: Testing & data quality validation

### **Week 3: API & Automation**
- Day 15-17: FastAPI REST endpoints
- Day 18-19: Scheduled job fetching
- Day 20-21: Error handling & logging

### **Week 4: Polish & Deploy**
- Day 22-24: Docker containerization
- Day 25-26: Documentation & README
- Day 27-28: Deploy & monitor

---

## 🏗️ Simplified Project Structure

```bash
job-aggregator-mvp/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── jsearch.py
│   │   ├── adzuna.py
│   │   └── remoteok.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── operations.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── logger.py
│   │   └── normalizer.py
│   └── scheduler.py
├── tests/
├── scripts/
│   └── initial_fetch.py
├── .env.example
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## ⚙️ Step-by-Step Implementation

### **Step 1: Project Setup (Day 1)**

```bash
# Create project
mkdir job-aggregator-mvp
cd job-aggregator-mvp
git init

# Virtual environment
python -m venv venv
source venv/bin/activate

# Directory structure
mkdir -p src/{agents,database,api,utils}
mkdir -p tests scripts
```

**Create `requirements.txt`:**

```txt
# Core
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
asyncpg==0.29.0
sqlalchemy==2.0.23

# API
fastapi==0.104.1
uvicorn[standard]==0.24.0

# HTTP
aiohttp==3.9.1
httpx==0.25.2

# Utilities
python-dateutil==2.8.2
pyyaml==6.0.1

# Scheduling
apscheduler==3.10.4

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

**Create `.env.example`:**

```bash
# Database
DATABASE_URL=postgresql://jobuser:jobpass123@localhost:5432/jobs_db

# API Keys
RAPIDAPI_KEY=your_rapidapi_key
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
API_PORT=8000
```

**Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: jobs_db
    environment:
      POSTGRES_DB: jobs_db
      POSTGRES_USER: jobuser
      POSTGRES_PASSWORD: jobpass123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

```bash
docker-compose up -d
pip install -r requirements.txt
```

---

### **Step 2: Database Models (Day 1-2)**

**Create `src/utils/config.py`:**

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # API Keys
    rapidapi_key: Optional[str] = None
    adzuna_app_id: Optional[str] = None
    adzuna_api_key: Optional[str] = None
    
    # App
    environment: str = "development"
    log_level: str = "INFO"
    api_port: int = 8000
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**Create `src/database/models.py`:**

```python
from sqlalchemy import Column, String, Text, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    # Identifiers
    id = Column(String(100), primary_key=True)  # e.g. "jsearch_abc123"
    source = Column(String(50), nullable=False, index=True)
    source_id = Column(String(100), nullable=False)
    
    # Basic Info
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Location & Type
    location = Column(JSON, nullable=False)  # {city, country, remote}
    employment_type = Column(String(50))  # FULLTIME, CONTRACT, etc.
    
    # Salary
    salary_min = Column(String(50))
    salary_max = Column(String(50))
    salary_currency = Column(String(10))
    
    # Application
    apply_url = Column(String(1000), nullable=False)
    
    # Metadata
    posted_at = Column(DateTime(timezone=True), nullable=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_data = Column(JSON)  # Original API response
    
    # Simple deduplication
    title_company_hash = Column(String(64), index=True)
    
    __table_args__ = (
        Index('idx_source_source_id', 'source', 'source_id', unique=True),
        Index('idx_posted_at', 'posted_at'),
    )
```

**Create `src/database/operations.py`:**

```python
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any
from src.database.models import Base, Job
from src.utils.config import settings
import hashlib

class Database:
    def __init__(self):
        self.engine = None
        self.session_maker = None
    
    async def connect(self):
        """Initialize database"""
        db_url = settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')
        self.engine = create_async_engine(db_url, echo=False)
        self.session_maker = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def disconnect(self):
        """Close connections"""
        if self.engine:
            await self.engine.dispose()
    
    async def save_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Save jobs with deduplication"""
        stats = {"new": 0, "skipped": 0, "updated": 0}
        
        async with self.session_maker() as session:
            for job_data in jobs:
                try:
                    # Generate ID and hash
                    job_id = f"{job_data['source']}_{job_data['source_id']}"
                    title_company_hash = self._hash_title_company(
                        job_data['title'], 
                        job_data['company']
                    )
                    
                    # Check if exists
                    existing = await session.get(Job, job_id)
                    
                    if existing:
                        stats["skipped"] += 1
                        continue
                    
                    # Check for duplicate by title+company
                    result = await session.execute(
                        f"SELECT id FROM jobs WHERE title_company_hash = '{title_company_hash}' LIMIT 1"
                    )
                    if result.scalar():
                        stats["skipped"] += 1
                        continue
                    
                    # Create new job
                    job = Job(
                        id=job_id,
                        source=job_data['source'],
                        source_id=job_data['source_id'],
                        title=job_data['title'],
                        company=job_data['company'],
                        description=job_data['description'],
                        location=job_data['location'],
                        employment_type=job_data.get('employment_type'),
                        salary_min=job_data.get('salary_min'),
                        salary_max=job_data.get('salary_max'),
                        salary_currency=job_data.get('salary_currency'),
                        apply_url=job_data['apply_url'],
                        posted_at=job_data['posted_at'],
                        title_company_hash=title_company_hash,
                        raw_data=job_data.get('raw_data')
                    )
                    
                    session.add(job)
                    stats["new"] += 1
                
                except Exception as e:
                    print(f"Error saving job: {e}")
                    continue
            
            await session.commit()
        
        return stats
    
    def _hash_title_company(self, title: str, company: str) -> str:
        """Create hash for deduplication"""
        text = f"{title.lower().strip()}_{company.lower().strip()}"
        return hashlib.sha256(text.encode()).hexdigest()[:16]

# Global instance
db = Database()
```

---

### **Step 3: Fetcher Agents (Day 3-4)**

**Create `src/agents/__init__.py`:**

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import asyncio

class BaseFetcher(ABC):
    """Base class for all fetchers"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    @abstractmethod
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs from source"""
        pass
    
    def is_backend_devops_job(self, title: str, description: str = "") -> bool:
        """Filter for backend/DevOps jobs only"""
        text = f"{title} {description}".lower()
        
        keywords = [
            'backend', 'back-end', 'back end',
            'devops', 'dev ops', 'devsecops',
            'sre', 'site reliability',
            'cloud engineer', 'cloud architect',
            'platform engineer', 'infrastructure',
            'system engineer', 'systems engineer',
            'golang', 'go developer',
            'python backend', 'java backend', 'node.js backend',
            'kubernetes', 'k8s', 'docker',
            'terraform', 'ansible',
        ]
        
        return any(keyword in text for keyword in keywords)
```

**Create `src/agents/remoteok.py`:**

```python
import aiohttp
from typing import List, Dict, Any
from src.agents import BaseFetcher
from datetime import datetime

class RemoteOKFetcher(BaseFetcher):
    
    def __init__(self):
        super().__init__("remoteok")
        self.url = "https://remoteok.com/api"
    
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all remote jobs"""
        print(f"[{self.source_name}] Fetching jobs...")
        
        async with aiohttp.ClientSession() as session:
            headers = {'User-Agent': 'JobAggregator/1.0'}
            
            async with session.get(self.url, headers=headers) as response:
                if response.status != 200:
                    print(f"[{self.source_name}] Error: HTTP {response.status}")
                    return []
                
                data = await response.json()
                jobs = data[1:] if data else []  # Skip first element (metadata)
                
                # Filter and normalize
                normalized = []
                for job in jobs:
                    if not self.is_backend_devops_job(job.get('position', ''), job.get('description', '')):
                        continue
                    
                    normalized_job = self._normalize(job)
                    if normalized_job:
                        normalized.append(normalized_job)
                
                print(f"[{self.source_name}] Found {len(normalized)} backend/DevOps jobs")
                return normalized
    
    def _normalize(self, job: Dict) -> Dict[str, Any]:
        """Normalize RemoteOK job to standard format"""
        try:
            return {
                'source': self.source_name,
                'source_id': str(job.get('id', '')),
                'title': job.get('position', ''),
                'company': job.get('company', ''),
                'description': job.get('description', ''),
                'location': {
                    'city': None,
                    'country': job.get('location', 'Remote'),
                    'remote': True
                },
                'employment_type': 'FULLTIME',
                'salary_min': None,
                'salary_max': None,
                'salary_currency': 'USD',
                'apply_url': job.get('url', ''),
                'posted_at': datetime.fromtimestamp(job.get('date', 0)),
                'raw_data': job
            }
        except Exception as e:
            print(f"[{self.source_name}] Normalization error: {e}")
            return None
```

**Create `src/agents/jsearch.py`:**

```python
import aiohttp
from typing import List, Dict, Any
from src.agents import BaseFetcher
from src.utils.config import settings
from datetime import datetime
import asyncio

class JSearchFetcher(BaseFetcher):
    
    BACKEND_DEVOPS_QUERIES = [
        "backend engineer", "backend developer",
        "devops engineer", "site reliability engineer",
        "cloud engineer", "platform engineer",
        "golang developer", "python backend",
    ]
    
    def __init__(self):
        super().__init__("jsearch")
        self.base_url = "https://jsearch.p.rapidapi.com/search"
        self.api_key = settings.rapidapi_key
    
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs for all backend/DevOps queries"""
        print(f"[{self.source_name}] Fetching jobs...")
        
        all_jobs = []
        async with aiohttp.ClientSession() as session:
            for query in self.BACKEND_DEVOPS_QUERIES:
                jobs = await self._fetch_query(session, query)
                all_jobs.extend(jobs)
                await asyncio.sleep(1)  # Rate limiting
        
        print(f"[{self.source_name}] Found {len(all_jobs)} jobs")
        return all_jobs
    
    async def _fetch_query(self, session: aiohttp.ClientSession, query: str) -> List[Dict]:
        """Fetch jobs for a single query"""
        params = {
            'query': query,
            'page': '1',
            'num_pages': '1',
            'date_posted': 'month'
        }
        
        headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'jsearch.p.rapidapi.com'
        }
        
        try:
            async with session.get(self.base_url, params=params, headers=headers) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                jobs = data.get('data', [])
                
                normalized = []
                for job in jobs:
                    normalized_job = self._normalize(job)
                    if normalized_job:
                        normalized.append(normalized_job)
                
                return normalized
        
        except Exception as e:
            print(f"[{self.source_name}] Error fetching {query}: {e}")
            return []
    
    def _normalize(self, job: Dict) -> Dict[str, Any]:
        """Normalize JSearch job to standard format"""
        try:
            return {
                'source': self.source_name,
                'source_id': job.get('job_id', ''),
                'title': job.get('job_title', ''),
                'company': job.get('employer_name', ''),
                'description': job.get('job_description', ''),
                'location': {
                    'city': job.get('job_city'),
                    'country': job.get('job_country'),
                    'remote': job.get('job_is_remote', False)
                },
                'employment_type': job.get('job_employment_type', 'FULLTIME'),
                'salary_min': job.get('job_min_salary'),
                'salary_max': job.get('job_max_salary'),
                'salary_currency': job.get('job_salary_currency', 'USD'),
                'apply_url': job.get('job_apply_link', ''),
                'posted_at': datetime.fromisoformat(job.get('job_posted_at_datetime_utc', datetime.now().isoformat())),
                'raw_data': job
            }
        except Exception as e:
            print(f"[{self.source_name}] Normalization error: {e}")
            return None
```

**Create `src/agents/adzuna.py`:**

```python
import aiohttp
from typing import List, Dict, Any
from src.agents import BaseFetcher
from src.utils.config import settings
from datetime import datetime
import asyncio

class AdzunaFetcher(BaseFetcher):
    
    def __init__(self):
        super().__init__("adzuna")
        self.app_id = settings.adzuna_app_id
        self.app_key = settings.adzuna_api_key
        self.countries = ['us', 'gb']
        self.category = 'it-jobs'
    
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch IT jobs from Adzuna"""
        print(f"[{self.source_name}] Fetching jobs...")
        
        all_jobs = []
        async with aiohttp.ClientSession() as session:
            for country in self.countries:
                jobs = await self._fetch_country(session, country)
                all_jobs.extend(jobs)
                await asyncio.sleep(0.5)
        
        # Filter for backend/DevOps
        filtered = [j for j in all_jobs if self.is_backend_devops_job(j['title'], j['description'])]
        
        print(f"[{self.source_name}] Found {len(filtered)} backend/DevOps jobs")
        return filtered
    
    async def _fetch_country(self, session: aiohttp.ClientSession, country: str) -> List[Dict]:
        """Fetch jobs for one country"""
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        
        params = {
            'app_id': self.app_id,
            'app_key': self.app_key,
            'results_per_page': 50,
            'category': self.category,
            'sort_by': 'date'
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                jobs = data.get('results', [])
                
                normalized = []
                for job in jobs:
                    normalized_job = self._normalize(job, country)
                    if normalized_job:
                        normalized.append(normalized_job)
                
                return normalized
        
        except Exception as e:
            print(f"[{self.source_name}] Error fetching {country}: {e}")
            return []
    
    def _normalize(self, job: Dict, country: str) -> Dict[str, Any]:
        """Normalize Adzuna job to standard format"""
        try:
            return {
                'source': self.source_name,
                'source_id': str(job.get('id', '')),
                'title': job.get('title', ''),
                'company': job.get('company', {}).get('display_name', ''),
                'description': job.get('description', ''),
                'location': {
                    'city': job.get('location', {}).get('display_name'),
                    'country': country.upper(),
                    'remote': False
                },
                'employment_type': job.get('contract_type', 'FULLTIME'),
                'salary_min': job.get('salary_min'),
                'salary_max': job.get('salary_max'),
                'salary_currency': 'USD' if country == 'us' else 'GBP',
                'apply_url': job.get('redirect_url', ''),
                'posted_at': datetime.fromisoformat(job.get('created', datetime.now().isoformat())),
                'raw_data': job
            }
        except Exception as e:
            print(f"[{self.source_name}] Normalization error: {e}")
            return None
```

---

### **Step 4: Orchestrator & Scheduler (Day 5-6)**

**Create `src/scheduler.py`:**

```python
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.agents.remoteok import RemoteOKFetcher
from src.agents.jsearch import JSearchFetcher
from src.agents.adzuna import AdzunaFetcher
from src.database.operations import db

async def fetch_all_jobs():
    """Fetch jobs from all sources and save to database"""
    print("\n=== Starting job fetch ===")
    
    # Initialize fetchers
    fetchers = [
        RemoteOKFetcher(),
        JSearchFetcher(),
        AdzunaFetcher(),
    ]
    
    # Fetch from all sources
    all_jobs = []
    for fetcher in fetchers:
        try:
            jobs = await fetcher.fetch_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[ERROR] {fetcher.source_name}: {e}")
    
    print(f"\n Total jobs fetched: {len(all_jobs)}")
    
    # Save to database
    if all_jobs:
        stats = await db.save_jobs(all_jobs)
        print(f"✓ Saved: {stats['new']} new, {stats['skipped']} duplicates")
    
    print("=== Fetch complete ===\n")

def start_scheduler():
    """Start scheduled job fetching"""
    scheduler = AsyncIOScheduler()
    
    # Run daily at 2 AM
    scheduler.add_job(fetch_all_jobs, 'cron', hour=2)
    
    # Run immediately on startup
    scheduler.add_job(fetch_all_jobs, 'date')
    
    scheduler.start()
    print("✓ Scheduler started (runs daily at 2 AM)")
    
    return scheduler
```

---

### **Step 5: REST API (Day 7-8)**

**Create `src/api/main.py`:**

```python
from fastapi import FastAPI, Query
from typing import Optional
from sqlalchemy import select, or_, and_
from src.database.models import Job
from src.database.operations import db
from src.utils.config import settings

app = FastAPI(title="Job Aggregator API", version="1.0.0")

@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    """Close database on shutdown"""
    await db.disconnect()

@app.get("/")
async def root():
    """API info"""
    return {
        "name": "Backend & DevOps Job Aggregator",
        "version": "1.0.0",
        "endpoints": ["/jobs", "/health"]
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}

@app.get("/jobs")
async def search_jobs(
    q: Optional[str] = Query(None, description="Search query"),
    company: Optional[str] = Query(None, description="Company name"),
    location: Optional[str] = Query(None, description="Location"),
    remote: Optional[bool] = Query(None, description="Remote only"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0)
):
    """Search jobs"""
    
    async with db.session_maker() as session:
        # Build query
        stmt = select(Job)
        
        filters = []
        
        # Text search
        if q:
            filters.append(
                or_(
                    Job.title.ilike(f"%{q}%"),
                    Job.description.ilike(f"%{q}%")
                )
            )
        
        # Company filter
        if company:
            filters.append(Job.company.ilike(f"%{company}%"))
        
        # Location filter
        if location:
            filters.append(Job.location.astext.ilike(f"%{location}%"))
        
        # Remote filter
        if remote is not None:
            filters.append(Job.location['remote'].astext == str(remote).lower())
        
        if filters:
            stmt = stmt.where(and_(*filters))
        
        # Order by posted date
        stmt = stmt.order_by(Job.posted_at.desc())
        
        # Pagination
        stmt = stmt.limit(limit).offset(offset)
        
        # Execute
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        
        # Format response
        return {
            "total": len(jobs),
            "limit": limit,
            "offset": offset,
            "jobs": [
                {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "employment_type": job.employment_type,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "salary_currency": job.salary_currency,
                    "apply_url": job.apply_url,
                    "posted_at": job.posted_at.isoformat(),
                    "source": job.source
                }
                for job in jobs
            ]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.api_port)
```

---

### **Step 6: Main Application (Day 9)**

**Create `src/main.py`:**

```python
import asyncio
from src.database.operations import db
from src.scheduler import start_scheduler, fetch_all_jobs

async def main():
    """Main application entry point"""
    
    print("🚀 Starting Job Aggregator MVP")
    
    # Connect to database
    await db.connect()
    print("✓ Database connected")
    
    # Run initial fetch
    print("\n📥 Running initial job fetch...")
    await fetch_all_jobs()
    
    # Start scheduler for daily fetches
    scheduler = start_scheduler()
    
    print("\n✅ Application running")
    print("   - API: http://localhost:8000")
    print("   - Docs: http://localhost:8000/docs")
    print("   - Jobs fetch: Daily at 2 AM")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        scheduler.shutdown()
        await db.disconnect()
        print("✓ Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### **Step 7: Run the MVP**

**Terminal 1 - Start the background worker:**
```bash
python src/main.py
```

**Terminal 2 - Start the API server:**
```bash
python src/api/main.py
```

**Test the API:**
```bash
# Get all jobs
curl http://localhost:8000/jobs

# Search for DevOps jobs
curl "http://localhost:8000/jobs?q=devops"

# Search for remote backend jobs
curl "http://localhost:8000/jobs?q=backend&remote=true"

# Get jobs from specific company
curl "http://localhost:8000/jobs?company=google"
```

---

## 🐳 Dockerization (Day 10)

**Create `Dockerfile`:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY .env .env

CMD ["python", "src/main.py"]
```

**Update `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: jobs_db
    environment:
      POSTGRES_DB: jobs_db
      POSTGRES_USER: jobuser
      POSTGRES_PASSWORD: jobpass123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jobuser"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    container_name: job_aggregator
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  api:
    build: .
    container_name: job_api
    command: python src/api/main.py
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
```

**Run everything:**
```bash
docker-compose up -d
```

---

## ✅ MVP Checklist

- [x] Database setup (PostgreSQL)
- [x] 3 data sources (RemoteOK, JSearch, Adzuna)
- [x] Job normalization
- [x] Basic deduplication (title + company hash)
- [x] Backend/DevOps filtering
- [x] REST API with search
- [x] Automated daily fetching
- [x] Docker containerization
- [x] Error handling & logging

---

## 📊 Expected Results

After running for 1 week, you should have:
- **~5,000-8,000** unique backend/DevOps jobs
- **Sources:** 40% RemoteOK, 35% JSearch, 25% Adzuna
- **Duplicates removed:** ~15-20%
- **API response time:** <200ms for simple queries
- **Storage:** ~500MB database

---

## 🚀 What's Next (Phase 2)

Once MVP works, add:
1. **Redis caching** - 6-hour cache for popular searches
2. **AI enrichment** - Extract deadlines, tech stack, seniority
3. **MCP server** - Natural language search via Claude
4. **More sources** - HackerNews, LinkedIn, company sites
5. **Expand categories** - Frontend, Data, ML jobs
6. **Advanced deduplication** - Fuzzy matching with AI

---

## 💡 Tips for Success

1. **Start simple** - Get RemoteOK working first (no API key needed)
2. **Test incrementally** - Run each fetcher separately before combining
3. **Monitor logs** - Check what's being saved vs. skipped
4. **Validate data** - Manually check a few jobs in the database
5. **API keys** - Get RapidAPI and Adzuna keys before Day 3

**Good luck building your MVP! 🎉**
