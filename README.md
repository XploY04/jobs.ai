# Backend & DevOps Job Aggregator

> AI-powered job aggregation platform that collects, normalizes, and serves backend/DevOps job listings from multiple sources.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)

---

## 🎯 Features

- **Multi-Source Aggregation**: Fetches jobs from RemoteOK, JSearch (RapidAPI), and Adzuna
- **Smart Filtering**: Focuses on backend, DevOps, SRE, cloud, and platform engineering roles
- **Automatic Deduplication**: Removes duplicate postings based on title + company hash
- **REST API**: FastAPI-powered endpoints with OpenAPI documentation
- **Scheduled Fetching**: Automated job ingestion every 30 minutes (configurable)
- **PostgreSQL Storage**: Robust data persistence with indexes for fast queries
- **Docker Support**: One-command deployment with docker-compose

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- API Keys:
  - [RapidAPI Key](https://rapidapi.com/) (for JSearch)
  - [Adzuna API](https://developer.adzuna.com/) (App ID + API Key)

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd jobs.ai
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Start with Docker

```bash
docker-compose up -d
```

### 4. Access API

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/health

---

## 📦 Installation

### Option 1: Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL
docker-compose up -d postgres

# Run application
python -m src.main
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Database (for local dev)
DATABASE_URL=postgresql://jobuser:jobpass123@localhost:5432/jobs_db

# API Keys
RAPIDAPI_KEY=your_rapidapi_key_here
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
API_PORT=8000
INGESTION_INTERVAL_MINUTES=30
```

### Database Connection

For external databases (e.g., Aiven, AWS RDS):

```bash
DATABASE_URL=postgres://user:pass@host:port/db?sslmode=require&ssl_no_verify=true
```

---

## 💻 Usage

### Run One-Time Ingestion

```bash
python -m src.main --ingest-once
```

Output:

```json
{
  "sources": {
    "remoteok": 30,
    "jsearch": 68,
    "adzuna": 24
  },
  "db": {
    "new": 85,
    "skipped": 42
  },
  "total_jobs": 122,
  "ran_at": "2026-02-07T00:00:00+00:00"
}
```

### Start API Server

```bash
python -m src.main
```

The API will:

- Start on `http://0.0.0.0:8000`
- Run initial job fetch
- Schedule fetching every 30 minutes

---

## 📚 API Documentation

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Health Check

```bash
GET /api/health
```

**Response:**

```json
{ "status": "ok" }
```

#### 2. List Jobs

```bash
GET /api/jobs?limit=50&offset=0&search=devops&remote_only=true
```

**Query Parameters:**

- `limit` (int): Results per page (max 200, default 50)
- `offset` (int): Pagination offset (default 0)
- `search` (string): Search in title/description
- `source` (array): Filter by sources (remoteok, jsearch, adzuna)
- `employment_type` (string): FULLTIME, PARTTIME, CONTRACT, etc.
- `remote_only` (bool): Filter remote jobs only

**Response:**

```json
{
  "total": 68,
  "jobs": [
    {
      "id": "jsearch_abc123",
      "source": "jsearch",
      "title": "Senior Backend Engineer",
      "company": "TechCorp",
      "location": {
        "city": "San Francisco",
        "country": "US",
        "remote": true
      },
      "employment_type": "FULLTIME",
      "salary_min": "120000",
      "salary_max": "180000",
      "salary_currency": "USD",
      "apply_url": "https://...",
      "posted_at": "2026-02-06T10:30:00Z"
    }
  ]
}
```

#### 3. Get Job Details

```bash
GET /api/jobs/{job_id}
```

**Response:** Single job object (same schema as above)

#### 4. Trigger Manual Ingestion

```bash
POST /api/jobs/ingest
```

**Response:** Ingestion statistics (same as CLI output)

### Interactive API Docs

Visit `http://localhost:8000/docs` for Swagger UI with:

- Request/response schemas
- Try-it-out functionality
- Authentication examples

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Server                     │
│              (Port 8000, /api/jobs)                 │
└────────────────────┬────────────────────────────────┘
                     │
         ┌───────────▼──────────┐
         │  Ingestion Service   │
         │   (APScheduler)      │
         └───────────┬──────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
│ RemoteOK │  │  JSearch  │  │  Adzuna   │
│  Agent   │  │   Agent   │  │   Agent   │
└────┬─────┘  └─────┬─────┘  └─────┬─────┘
     │              │              │
     └──────────────┼──────────────┘
                    │
              ┌─────▼─────┐
              │ Database  │
              │ Operations│
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │PostgreSQL │
              │  (Docker) │
              └───────────┘
```

### Components

- **Agents** (`src/agents/`): Fetch jobs from external APIs
- **Services** (`src/services/`): Orchestration and scheduling
- **Database** (`src/database/`): Models and operations
- **API** (`src/api/`): FastAPI routes and schemas
- **Utils** (`src/utils/`): Configuration and logging

---

## 🛠️ Development

### Project Structure

```
jobs.ai/
├── src/
│   ├── agents/           # Job fetcher agents
│   │   ├── __init__.py   # Base fetcher with filtering
│   │   ├── remoteok.py
│   │   ├── jsearch.py
│   │   └── adzuna.py
│   ├── api/              # FastAPI application
│   │   ├── main.py       # App factory
│   │   ├── routes.py     # Endpoint definitions
│   │   └── schemas.py    # Pydantic models
│   ├── database/         # Data layer
│   │   ├── models.py     # SQLAlchemy models
│   │   └── operations.py # CRUD operations
│   ├── services/         # Business logic
│   │   └── ingestion.py  # Orchestrator + scheduler
│   ├── utils/            # Utilities
│   │   ├── config.py     # Settings management
│   │   └── logger.py     # Logging setup
│   └── main.py           # Application entrypoint
├── tests/                # Test suite
├── scripts/              # Utility scripts
├── logs/                 # Application logs
├── .env                  # Environment config (git-ignored)
├── .env.example          # Example configuration
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container definition
├── docker-compose.yml    # Multi-service orchestration
└── README.md             # This file
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/

# Lint
flake8 src/

# Type checking
mypy src/
```

### Adding a New Data Source

1. Create agent in `src/agents/`:

```python
from src.agents import BaseFetcher

class NewSourceAgent(BaseFetcher):
    def __init__(self):
        super().__init__("newsource")

    async def fetch_jobs(self):
        # Implement fetching logic
        jobs = []
        # ... fetch from API
        return jobs

    def _normalize(self, job):
        # Convert to standard format
        return {
            "source": self.source_name,
            "source_id": job["id"],
            "title": job["title"],
            # ... other fields
        }
```

2. Add to orchestrator in `src/services/ingestion.py`:

```python
from src.agents.newsource import NewSourceAgent

FETCHER_CLASSES = [
    RemoteOKFetcher,
    JSearchFetcher,
    AdzunaFetcher,
    NewSourceAgent,  # Add here
]
```

---

## 🐛 Troubleshooting

### Database Connection Issues

**Problem:** `asyncpg.exceptions.InvalidCatalogNameError`

**Solution:**

```bash
# Recreate database
docker-compose down -v
docker-compose up -d postgres
```

### SSL Certificate Errors

**Problem:** `ssl.SSLCertVerificationError`

**Solution:** Add `ssl_no_verify=true` to DATABASE_URL:

```bash
DATABASE_URL=postgres://user:pass@host:port/db?sslmode=require&ssl_no_verify=true
```

### API Key Rate Limits

**Problem:** `429 Too Many Requests` from JSearch/Adzuna

**Solution:**

- Reduce fetch frequency in `.env`: `INGESTION_INTERVAL_MINUTES=60`
- Implement exponential backoff (future enhancement)

### No Jobs Found

**Problem:** Ingestion returns 0 new jobs

**Solutions:**

1. Check API keys are valid
2. Verify network connectivity
3. Review logs: `tail -f logs/job_aggregator.log`
4. Test single source:

   ```python
   from src.agents.remoteok import RemoteOKFetcher
   import asyncio

   async def test():
       agent = RemoteOKFetcher()
       jobs = await agent.fetch_jobs()
       print(f"Found {len(jobs)} jobs")

   asyncio.run(test())
   ```

### Docker Build Fails

**Problem:** `pip install` errors

**Solution:**

```bash
# Clear Docker cache
docker-compose build --no-cache
```

---

## 📊 Current Stats

- **Sources**: 3 (RemoteOK, JSearch, Adzuna)
- **Job Categories**: Backend, DevOps, SRE, Cloud, Platform
- **Fetch Interval**: 30 minutes (configurable)
- **Database**: PostgreSQL 16 with GIN indexes
- **API Response Time**: <200ms (typical)
- **Deduplication Rate**: ~15-20%

---

## 🚧 Roadmap

### Phase 1: MVP (Current) ✅

- [x] Multi-source job aggregation
- [x] REST API with search
- [x] Automated scheduling
- [x] Docker deployment

### Phase 2: Enhancement (Planned)

- [ ] Redis caching layer
- [ ] AI-powered deadline extraction
- [ ] Tech stack parsing
- [ ] Advanced deduplication (fuzzy matching)
- [ ] More sources (LinkedIn, GitHub Jobs, HackerNews)

### Phase 3: Scale

- [ ] Expand to all tech jobs (frontend, data, ML)
- [ ] MCP server for Claude integration
- [ ] Prometheus monitoring
- [ ] Horizontal scaling

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

## 📧 Contact

For questions or issues, please open a GitHub issue.

---

**Built with ❤️ using Python, FastAPI, and PostgreSQL**
