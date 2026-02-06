# Complete Implementation Plan: AI-Powered Job Aggregation Platform

Let me give you a **comprehensive, step-by-step implementation plan** with full details, code, and timelines.

---

## 🎯 Project Overview

**What we're building:**
- AI-powered job aggregation system with **phased expansion strategy**
- Intelligent agents for orchestration, normalization, and enhancement  
- FastAPI REST API + MCP server for natural language job search via Claude
- PostgreSQL + Redis for storage and caching
- Smart deduplication and AI enrichment

**📈 Expansion Phases:**

**Phase 1 (MVP):** Backend + DevOps Jobs (~5-10k jobs)
- Focus: Backend Engineer, DevOps, SRE, Cloud Engineer, Platform Engineer
- Why: Smaller dataset, faster iteration, lower costs
- Timeline: 3-4 weeks

**Phase 2 (Growth):** All Tech Jobs (~30k+ jobs)  
- Add: Frontend, Mobile, Data Science, ML, Security, etc.
- Timeline: 1-2 weeks to expand (just config change!)

**Phase 3 (Scale):** All Jobs (~100k+ jobs)
- Add: Non-tech roles, expand categories
- Timeline: 1-2 weeks to scale infrastructure

**Current Focus:** Phase 1 - Backend + DevOps Jobs

---

## 📋 Phase 1: Foundation Setup (Week 1)

### **1.1 Project Structure**

```bash
job-aggregator/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── jobs.py          # Job search endpoints
│   │   │   └── health.py        # Health checks
│   │   └── schemas.py           # Pydantic models
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── fetchers/
│   │   │   ├── __init__.py
│   │   │   ├── jsearch_agent.py
│   │   │   ├── adzuna_agent.py
│   │   │   ├── remoteok_agent.py
│   │   │   ├── hackernews_agent.py
│   │   │   └── rss_agent.py
│   │   ├── normalizer.py
│   │   ├── deduplicator.py
│   │   └── processor.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── connection.py
│   │   └── migrations/
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis_client.py      # Redis cache layer
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   └── job_search_server.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── config.py
│   │   └── metrics.py           # Prometheus metrics
│   └── main.py
├── tests/
│   ├── test_agents.py
│   ├── test_database.py
│   └── test_mcp.py
├── config/
│   ├── .env.example
│   └── settings.yaml
├── scripts/
│   ├── setup_db.py
│   └── initial_fetch.py
├── requirements.txt
├── docker-compose.yml
├── README.md
└── .gitignore
```

### **1.2 Initialize Repository**

```bash
# Create project
mkdir job-aggregator
cd job-aggregator

# Initialize git
git init
echo "# AI-Powered Job Aggregator" > README.md

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
.env
.venv/
venv/
*.log
.DS_Store
.idea/
.vscode/
*.db
*.sqlite
node_modules/
EOF

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Create directory structure
mkdir -p src/{api/routes,agents/fetchers,database/migrations,cache,mcp_server,utils}
mkdir -p tests config scripts
```

### **1.3 Dependencies**

Create `requirements.txt`:

```txt
# Core
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dateutil==2.8.2

# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database
asyncpg==0.29.0
sqlalchemy==2.0.23
alembic==1.13.0

# Cache
redis==5.0.1

# HTTP & API
aiohttp==3.9.1
httpx==0.25.2
requests==2.31.0

# AI
anthropic==0.8.0

# MCP
mcp==0.1.0

# Monitoring
prometheus-client==0.19.0

# Job Fetching
feedparser==6.0.10  # For RSS feeds
beautifulsoup4==4.12.2  # For parsing
lxml==4.9.3

# Scheduling
schedule==1.2.0
apscheduler==3.10.4

# Utilities
pyyaml==6.0.1
click==8.1.7

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Development
black==23.12.1
flake8==6.1.0
mypy==1.7.1
```

Install:
```bash
pip install -r requirements.txt
```

### **1.4 Configuration Setup**

Create `config/.env.example`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/jobs_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jobs_db
DB_USER=your_user
DB_PASSWORD=your_password

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # optional
CACHE_TTL=21600  # 6 hours

# API Keys
RAPIDAPI_KEY=your_rapidapi_key_here
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# App Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
MAX_WORKERS=10
FETCH_INTERVAL_HOURS=24

# Job Filtering (Phase 1: Backend/DevOps only)
JOB_CATEGORIES=backend,devops,sre,cloud,platform
EXPAND_TO_ALL_TECH=false  # Set to true for Phase 2

# Rate Limiting
JSEARCH_RATE_LIMIT=100  # requests per day
ADZUNA_RATE_LIMIT=1000
REMOTEOK_RATE_LIMIT=100

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
```

Create `src/utils/config.py`:

```python
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Database
    database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "jobs_db"
    db_user: str
    db_password: str
    
    # Redis Cache
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    cache_ttl: int = 21600  # 6 hours
    
    # API Keys
    rapidapi_key: Optional[str] = None
    adzuna_app_id: Optional[str] = None
    adzuna_api_key: Optional[str] = None
    anthropic_api_key: str
    
    # App Settings
    log_level: str = "INFO"
    environment: str = "development"
    max_workers: int = 10
    fetch_interval_hours: int = 24
    
    # Job Filtering (Phased Expansion)
    job_categories: str = "backend,devops,sre,cloud,platform"  # CSV
    expand_to_all_tech: bool = False
    
    @property
    def enabled_categories(self) -> List[str]:
        """Get list of enabled job categories"""
        if self.expand_to_all_tech:
            return ["all"]  # Fetch all tech jobs
        return [cat.strip() for cat in self.job_categories.split(",")]
    
    # Rate Limiting
    jsearch_rate_limit: int = 100
    adzuna_rate_limit: int = 1000
    remoteok_rate_limit: int = 100
    
    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

Create `src/utils/logger.py`:

```python
import logging
import sys
from pathlib import Path

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with consistent formatting"""
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "job_aggregator.log")
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
```

### **1.5 Database Setup**

Create `docker-compose.yml`:

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
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jobuser"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: jobs_cache
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@jobs.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

Start database:
```bash
docker-compose up -d
```

Create `src/database/models.py`:

```python
from sqlalchemy import (
    Column, String, Integer, DateTime, JSON, 
    Boolean, Text, ARRAY, Index, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()

class JobStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    FILLED = "filled"
    DELETED = "deleted"

class EmploymentType(str, enum.Enum):
    FULLTIME = "FULLTIME"
    PARTTIME = "PARTTIME"
    CONTRACT = "CONTRACT"
    INTERN = "INTERN"
    TEMPORARY = "TEMPORARY"

class Job(Base):
    __tablename__ = "jobs"
    
    # Primary identification
    id = Column(String(100), primary_key=True)  # e.g., "jsearch_abc123"
    source = Column(String(50), nullable=False, index=True)  # jsearch, adzuna, etc.
    source_id = Column(String(100), nullable=False)  # Original ID from source
    
    # Basic info
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    company_logo = Column(String(500))
    description = Column(Text, nullable=False)
    
    # Location (JSON: {city, state, country, remote})
    location = Column(JSON, nullable=False)
    
    # Job details
    employment_type = Column(SQLEnum(EmploymentType), index=True)
    
    # Salary (JSON: {min, max, currency, period})
    salary = Column(JSON)
    
    # Skills and requirements
    skills = Column(ARRAY(String), default=list)  # Tech stack
    
    # Application
    apply_url = Column(String(1000), nullable=False)
    
    # Dates
    posted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), index=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Status
    status = Column(SQLEnum(JobStatus), default=JobStatus.ACTIVE, index=True)
    
    # AI-enhanced fields
    ai_extracted_deadline = Column(DateTime(timezone=True))
    ai_deadline_confidence = Column(String(20))  # high, medium, low
    ai_urgency = Column(String(20))  # urgent, normal, low
    ai_quality_score = Column(Integer)  # 0-100
    ai_category = Column(String(50))  # frontend, backend, etc.
    
    # Deduplication
    content_hash = Column(String(64), index=True)  # For finding duplicates
    duplicate_of = Column(String(100))  # Points to canonical job ID
    
    # Metadata
    raw_data = Column(JSON)  # Store original API response
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_title_company', 'title', 'company'),
        Index('idx_location_gin', 'location', postgresql_using='gin'),
        Index('idx_skills_gin', 'skills', postgresql_using='gin'),
        Index('idx_posted_status', 'posted_at', 'status'),
        Index('idx_source_source_id', 'source', 'source_id', unique=True),
    )

class FetchLog(Base):
    __tablename__ = "fetch_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    fetch_started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    fetch_completed_at = Column(DateTime(timezone=True))
    
    # Results
    jobs_fetched = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    jobs_failed = Column(Integer, default=0)
    
    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Metadata
    search_params = Column(JSON)
    
    __table_args__ = (
        Index('idx_source_started', 'source', 'fetch_started_at'),
    )

class UserSearch(Base):
    """For MCP server - track user searches"""
    __tablename__ = "user_searches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), index=True)
    query = Column(Text, nullable=False)
    filters = Column(JSON)
    results_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

Create `scripts/init.sql`:

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS btree_gin;  -- For GIN indexes on multiple columns

-- Create indexes after data is loaded (put in migration)
-- This file is just for initial extensions
```

Create `src/database/connection.py`:

```python
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class Database:
    def __init__(self):
        self.engine = None
        self.session_maker = None
        self.pool = None
    
    async def connect(self):
        """Initialize database connections"""
        
        # SQLAlchemy engine for ORM operations
        database_url = settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')
        self.engine = create_async_engine(
            database_url,
            echo=settings.environment == "development",
            pool_size=20,
            max_overflow=40
        )
        
        self.session_maker = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # asyncpg pool for raw queries (faster for bulk operations)
        self.pool = await asyncpg.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            min_size=10,
            max_size=50
        )
        
        logger.info("Database connections established")
    
    async def disconnect(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        if self.engine:
            await self.engine.dispose()
        logger.info("Database connections closed")
    
    @asynccontextmanager
    async def session(self):
        """Get SQLAlchemy session"""
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def execute_raw(self, query: str, *args):
        """Execute raw SQL query"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

# Global database instance
db = Database()
```

Create database migration script `scripts/setup_db.py`:

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.database.models import Base
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def create_tables():
    """Create all database tables"""
    
    database_url = settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(database_url)
    
    async with engine.begin() as conn:
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
```

Run database setup:
```bash
python scripts/setup_db.py
```

---

## 📋 Phase 2: Build Fetcher Agents (Week 2)

### **2.1 Base Agent Class**

Create `src/agents/fetchers/__init__.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.utils.logger import setup_logger
import asyncio

class BaseFetcherAgent(ABC):
    """Base class for all fetcher agents"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = setup_logger(f"agent.{source_name}")
        self.rate_limit_delay = 0.5  # seconds between requests
    
    @abstractmethod
    async def fetch_all_tech_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all available tech jobs from this source"""
        pass
    
    async def _rate_limit(self):
        """Apply rate limiting"""
        await asyncio.sleep(self.rate_limit_delay)
    
    def _tag_with_metadata(self, jobs: List[Dict]) -> List[Dict]:
        """Add source metadata to jobs"""
        from datetime import datetime
        
        for job in jobs:
            job['_source'] = self.source_name
            job['_fetched_at'] = datetime.utcnow().isoformat()
        
        return jobs
```

### **2.2 JSearch Agent**

Create `src/agents/fetchers/jsearch_agent.py`:

```python
import aiohttp
from typing import List, Dict, Any
from src.agents.fetchers import BaseFetcherAgent
from src.utils.config import settings

class JSearchAgent(BaseFetcherAgent):
    
    # Phase 1: Backend & DevOps focused searches
    BACKEND_DEVOPS_SEARCHES = [
        "backend engineer", "backend developer",
        "devops engineer", "devops",
        "site reliability engineer", "sre",
        "cloud engineer", "cloud architect",
        "platform engineer", "infrastructure engineer",
        "system engineer", "systems administrator",
        "golang developer", "python backend",
        "java backend", "node.js backend",
        "kubernetes engineer", "docker",
    ]
    
    # Phase 2: Expand to all tech (uncomment when ready)
    ALL_TECH_SEARCHES = [
        "software engineer", "developer", "programmer",
        "frontend", "backend", "full stack",
        "mobile developer", "devops", "sre",
        "data engineer", "data scientist",
        "machine learning", "AI engineer",
        "security engineer", "cloud engineer",
        "react developer", "python developer",
        "java developer", "javascript developer",
    ]
    
    @property
    def active_searches(self) -> List[str]:
        """Get active search terms based on expansion phase"""
        if settings.expand_to_all_tech:
            return self.ALL_TECH_SEARCHES
        return self.BACKEND_DEVOPS_SEARCHES
    
    def __init__(self):
        super().__init__("jsearch")
        self.api_key = settings.rapidapi_key
        self.base_url = 'https://jsearch.p.rapidapi.com/search'
        self.rate_limit_delay = 1.0  # Be conservative
    
    async def fetch_all_tech_jobs(self) -> List[Dict[str, Any]]:
        """Fetch backend/devops jobs (Phase 1) or all tech jobs (Phase 2)"""
        
        all_jobs = []
        search_terms = self.active_searches
        
        self.logger.info(f"Fetching {len(search_terms)} job categories (Phase {'2' if settings.expand_to_all_tech else '1'})")
        
        async with aiohttp.ClientSession() as session:
            for search_term in search_terms:
                self.logger.info(f"Fetching: {search_term}")
                
                # Fetch 3 pages per search for good coverage
                for page in range(1, 4):
                    try:
                        jobs = await self._fetch_page(session, search_term, page)
                        all_jobs.extend(jobs)
                        
                        self.logger.info(f"  Page {page}: {len(jobs)} jobs")
                        
                        await self._rate_limit()
                    
                    except Exception as e:
                        self.logger.error(f"Error fetching {search_term} page {page}: {e}")
                        continue
        
        self.logger.info(f"Total fetched: {len(all_jobs)} jobs")
        return self._tag_with_metadata(all_jobs)
    
    async def _fetch_page(
        self, 
        session: aiohttp.ClientSession,
        query: str,
        page: int
    ) -> List[Dict]:
        """Fetch a single page of results"""
        
        params = {
            'query': query,
            'page': str(page),
            'num_pages': '1',
            'date_posted': 'month',
        }
        
        headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'jsearch.p.rapidapi.com'
        }
        
        async with session.get(
            self.base_url,
            params=params,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('data', [])
            else:
                self.logger.error(f"HTTP {response.status}: {await response.text()}")
                return []
```

### **2.3 Adzuna Agent**

Create `src/agents/fetchers/adzuna_agent.py`:

```python
import aiohttp
from typing import List, Dict, Any
from src.agents.fetchers import BaseFetcherAgent
from src.utils.config import settings

class AdzunaAgent(BaseFetcherAgent):
    
    TECH_CATEGORIES = ['it-jobs', 'engineering-jobs']
    COUNTRIES = ['us', 'gb', 'ca', 'au']
    
    def __init__(self):
        super().__init__("adzuna")
        self.app_id = settings.adzuna_app_id
        self.app_key = settings.adzuna_api_key
        self.rate_limit_delay = 0.3
    
    async def fetch_all_tech_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all tech jobs from Adzuna"""
        
        all_jobs = []
        
        async with aiohttp.ClientSession() as session:
            for country in self.COUNTRIES:
                for category in self.TECH_CATEGORIES:
                    self.logger.info(f"Fetching {country}/{category}")
                    
                    page = 1
                    while page <= 20:  # Cap at 20 pages (1000 jobs) per category
                        try:
                            jobs = await self._fetch_page(session, country, category, page)
                            
                            if not jobs:
                                break  # No more results
                            
                            all_jobs.extend(jobs)
                            self.logger.info(f"  Page {page}: {len(jobs)} jobs")
                            
                            page += 1
                            await self._rate_limit()
                        
                        except Exception as e:
                            self.logger.error(f"Error fetching {country}/{category} page {page}: {e}")
                            break
        
        self.logger.info(f"Total fetched: {len(all_jobs)} jobs")
        return self._tag_with_metadata(all_jobs)
    
    async def _fetch_page(
        self,
        session: aiohttp.ClientSession,
        country: str,
        category: str,
        page: int
    ) -> List[Dict]:
        """Fetch a category page"""
        
        url = f'https://api.adzuna.com/v1/api/jobs/{country}/search/{page}'
        
        params = {
            'app_id': self.app_id,
            'app_key': self.app_key,
            'results_per_page': 50,
            'category': category,
            'sort_by': 'date'
        }
        
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('results', [])
            else:
                return []
```

### **2.4 RemoteOK Agent**

Create `src/agents/fetchers/remoteok_agent.py`:

```python
import aiohttp
from typing import List, Dict, Any
from src.agents.fetchers import BaseFetcherAgent

class RemoteOKAgent(BaseFetcherAgent):
    
    TECH_TAGS = {
        'dev', 'developer', 'engineer', 'engineering', 'software',
        'frontend', 'backend', 'fullstack', 'mobile', 'ios', 'android',
        'react', 'python', 'javascript', 'java', 'golang', 'rust',
        'devops', 'sre', 'cloud', 'aws', 'data', 'ml', 'ai', 'security'
    }
    
    def __init__(self):
        super().__init__("remoteok")
        self.url = 'https://remoteok.com/api'
        self.rate_limit_delay = 2.0  # Be respectful
    
    async def fetch_all_tech_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all remote tech jobs"""
        
        self.logger.info("Fetching all remote jobs")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'JobAggregator/1.0 (Educational Project)'
            }
            
            async with session.get(
                self.url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    all_jobs = await response.json()
                    
                    # First element is metadata, skip it
                    jobs = all_jobs[1:] if all_jobs else []
                    
                    # Filter for tech jobs
                    tech_jobs = self._filter_tech_jobs(jobs)
                    
                    self.logger.info(f"Total fetched: {len(tech_jobs)} tech jobs")
                    return self._tag_with_metadata(tech_jobs)
                else:
                    self.logger.error(f"HTTP {response.status}")
                    return []
    
    def _filter_tech_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Filter for tech-related jobs"""
        
        tech_jobs = []
        
        for job in jobs:
            tags = set(job.get('tags', []))
            if tags.intersection(self.TECH_TAGS):
                tech_jobs.append(job)
        
        return tech_jobs
```

### **2.5 HackerNews Agent**

Create `src/agents/fetchers/hackernews_agent.py`:

```python
import aiohttp
from typing import List, Dict, Any
from datetime import datetime
from src.agents.fetchers import BaseFetcherAgent

class HackerNewsAgent(BaseFetcherAgent):
    
    def __init__(self):
        super().__init__("hackernews")
        self.search_url = 'https://hn.algolia.com/api/v1/search'
        self.item_url = 'https://hn.algolia.com/api/v1/items'
    
    async def fetch_all_tech_jobs(self) -> List[Dict[str, Any]]:
        """Fetch from HN Who is Hiring thread"""
        
        # Only fetch during first week of month
        if datetime.now().day > 7:
            self.logger.info("Skipping (not first week of month)")
            return []
        
        self.logger.info("Fetching HN Who is Hiring thread")
        
        async with aiohttp.ClientSession() as session:
            # Find latest thread
            thread_id = await self._find_latest_thread(session)
            
            if not thread_id:
                self.logger.warning("No 'Who is Hiring' thread found")
                return []
            
            # Fetch all comments
            jobs = await self._fetch_thread_comments(session, thread_id)
            
            self.logger.info(f"Total fetched: {len(jobs)} job postings")
            return self._tag_with_metadata(jobs)
    
    async def _find_latest_thread(self, session: aiohttp.ClientSession) -> str:
        """Find the most recent 'Who is Hiring' thread"""
        
        params = {
            'query': 'Ask HN: Who is hiring?',
            'tags': 'story'
        }
        
        async with session.get(self.search_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data['hits']:
                    return data['hits'][0]['objectID']
        
        return None
    
    async def _fetch_thread_comments(
        self,
        session: aiohttp.ClientSession,
        thread_id: str
    ) -> List[Dict]:
        """Fetch all comments from the thread"""
        
        url = f"{self.item_url}/{thread_id}"
        
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('children', [])
        
        return []
```

### **2.6 Test Fetchers**

Create `tests/test_agents.py`:

```python
import pytest
import asyncio
from src.agents.fetchers.jsearch_agent import JSearchAgent
from src.agents.fetchers.adzuna_agent import AdzunaAgent
from src.agents.fetchers.remoteok_agent import RemoteOKAgent

@pytest.mark.asyncio
async def test_jsearch_agent():
    agent = JSearchAgent()
    
    # Mock a single search to avoid API costs
    agent.COMPREHENSIVE_SEARCHES = ["software engineer"]
    
    jobs = await agent.fetch_all_tech_jobs()
    
    assert len(jobs) > 0
    assert all(job['_source'] == 'jsearch' for job in jobs)
    assert all('_fetched_at' in job for job in jobs)

@pytest.mark.asyncio
async def test_remoteok_agent():
    agent = RemoteOKAgent()
    jobs = await agent.fetch_all_tech_jobs()
    
    assert len(jobs) > 0
    assert all(job['_source'] == 'remoteok' for job in jobs)
```

Run tests:
```bash
pytest tests/test_agents.py -v
```

---

**This is Part 1 of the implementation plan. Should I continue with:**

1. ✅ **Phase 3: Normalizer Agent** (converting all formats to standard schema)
2. ✅ **Phase 4: Deduplicator Agent** (finding and merging duplicates with AI)
3. ✅ **Phase 5: Processor Pipeline** (deadline extraction, tech stack parsing, etc.)
4. ✅ **Phase 6: Orchestrator Agent** (intelligent decision-making)
5. ✅ **Phase 7: MCP Server** (natural language search interface)
6. ✅ **Phase 8: Deployment & Monitoring**

Let me know and I'll continue with the next phase!