# jobs.ai

> AI-powered tech job aggregation platform. Collects jobs from 6 sources, enriches them with Gemini AI into a 40-field schema, and serves them via a fast REST API with full-text search.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Gemini AI](https://img.shields.io/badge/Gemini-2.5--flash--lite-4285F4.svg)](https://ai.google.dev/)

---

## 🎯 Features

- **6 Data Sources**: RemoteOK, JSearch, Adzuna (7 countries), HackerNews "Who is Hiring?", RSS feeds (WeWorkRemotely + RemoteOK), ATS scraper (Greenhouse, Lever, Ashby, Workable, SmartRecruiters)
- **AI Enrichment**: Gemini 2.5 Flash-Lite processes raw jobs into a structured 40-field schema (batch of 5, 10 concurrent)
- **Full-Text Search**: PostgreSQL tsvector + GIN index with weighted fields and relevance ranking (~35ms)
- **Save-Per-Batch**: Each batch of 5 jobs is saved to DB immediately after AI processing
- **Automatic Deduplication**: Title + company hash prevents duplicates
- **Age Filtering**: Jobs older than 15 days are dropped during ingestion
- **Company Discovery**: SerpAPI-powered discovery of companies on ATS platforms
- **REST API**: FastAPI with filtering, pagination, and full-text search
- **Scheduled Fetching**: APScheduler runs ingestion every 30 minutes (configurable)
- **Docker Support**: One-command deployment with docker-compose

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Data Schema](#data-schema)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- API Keys:
  - [Gemini API Key](https://aistudio.google.com/apikey) (AI enrichment)
  - [Adzuna API](https://developer.adzuna.com/) (App ID + API Key)
  - [RapidAPI Key](https://rapidapi.com/) (for JSearch)
  - [SerpAPI Key](https://serpapi.com/) (for ATS company discovery)

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd jobs.ai
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start with Docker

```bash
docker-compose up -d
```

### 3. Access API

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/health

---

## 📦 Installation

### Option 1: Docker (Recommended)

```bash
docker-compose up -d        # Start all services
docker-compose logs -f      # View logs
docker-compose down         # Stop services
```

### Option 2: Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server (with scheduler)
python -m src.main

# Start API only (no auto-ingestion)
DISABLE_SCHEDULER=1 python -m src.main
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Database
DATABASE_URL=postgres://user:pass@host:port/db?sslmode=require&ssl_no_verify=true

# API Keys
RAPIDAPI_KEY=your_rapidapi_key
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key
GEMINI_API_KEY=your_gemini_api_key
SERPAPI_KEY=your_serpapi_key

# AI Enrichment
ENABLE_AI_ENRICHMENT=true

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
API_PORT=8000
INGESTION_INTERVAL_MINUTES=30
```

### Runtime Flags

| Flag | Purpose |
|------|---------|
| `DISABLE_SCHEDULER=1` | Start API only, no auto-ingestion |
| `ENABLE_AI_ENRICHMENT=false` | Use rule-based fallback instead of Gemini |

---

## 💻 Usage

### Start API Server with Scheduler

```bash
python -m src.main
```

The server will start on `http://0.0.0.0:8000`, run an initial ingestion, and schedule fetching every 30 minutes.

### Start API Only (No Ingestion)

```bash
DISABLE_SCHEDULER=1 python -m src.main
```

### Trigger Manual Ingestion

```bash
curl -X POST http://localhost:8000/api/jobs/ingest
```

---

## 📚 API Documentation

### Endpoints

#### 1. Health Check

```
GET /api/health
```

#### 2. List Jobs (with full-text search)

```
GET /api/jobs?limit=50&offset=0&search=kubernetes&remote_only=true&category=devops
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Results per page (1-200, default 50) |
| `offset` | int | Pagination offset (default 0) |
| `search` | string | Full-text search across title, company, skills, description (min 2 chars) |
| `source` | string[] | Filter by source: `remoteok`, `jsearch`, `adzuna`, `hackernews`, `rss_feed`, `ats_scraper` |
| `employment_type` | string | `FULLTIME`, `PARTTIME`, `CONTRACT`, `INTERN` |
| `remote_only` | bool | Filter remote jobs only |
| `seniority` | string[] | `junior`, `mid`, `senior`, `staff`, `principal` |
| `category` | string[] | `backend`, `frontend`, `fullstack`, `devops`, `data`, `ml`, `mobile`, `security`, `qa`, `general` |

**Response:**

```json
{
  "total": 313,
  "jobs": [
    {
      "id": "adzuna_5609947686",
      "source": "adzuna",
      "source_id": "5609947686",
      "source_url": "https://...",
      "title": "Senior Backend Engineer",
      "company": "TechCorp",
      "company_logo": null,
      "company_website": "https://techcorp.com",
      "description": "Full HTML description...",
      "short_description": "AI-generated 2-3 sentence summary.",
      "location": { "city": "Berlin", "country": "de", "remote": true },
      "country": "de",
      "city": "Berlin",
      "state": null,
      "is_remote": true,
      "work_arrangement": "remote",
      "employment_type": "FULLTIME",
      "seniority_level": "senior",
      "department": "Engineering",
      "category": "backend",
      "salary_min": "90000",
      "salary_max": "130000",
      "salary_currency": "EUR",
      "salary_period": "year",
      "skills": ["Python", "Kubernetes", "PostgreSQL"],
      "required_experience_years": 5,
      "required_education": "Bachelor's",
      "key_responsibilities": ["Design microservices", "..."],
      "nice_to_have_skills": ["Go", "Terraform"],
      "benefits": ["Remote work", "Stock options"],
      "visa_sponsorship": "yes",
      "posted_at": "2026-02-07T10:30:00Z",
      "application_deadline": null,
      "fetched_at": "2026-02-07T12:00:00Z",
      "apply_url": "https://...",
      "apply_options": null,
      "tags": ["IT Jobs"],
      "quality_score": 85
    }
  ]
}
```

#### 3. Get Job Details

```
GET /api/jobs/{job_id}
```

#### 4. Get Filter Options

```
GET /api/filters
```

Returns available values with counts for source, category, seniority, employment type, etc.

#### 5. Trigger Ingestion

```
POST /api/jobs/ingest
```

### Interactive Docs

Visit `http://localhost:8000/docs` for Swagger UI.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Server (:8000)                    │
│              /api/jobs  /api/filters  /api/health             │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Ingestion Service     │
              │    (APScheduler)        │
              └────────────┬────────────┘
                           │ asyncio.gather (parallel)
     ┌─────────┬───────────┼───────────┬──────────┬────────────┐
     │         │           │           │          │            │
┌────▼───┐ ┌──▼────┐ ┌────▼───┐ ┌─────▼────┐ ┌──▼───┐ ┌──────▼──────┐
│RemoteOK│ │JSearch│ │ Adzuna │ │HackerNews│ │ RSS  │ │ ATS Scraper │
│  API   │ │RapidAPI│ │7 ctries│ │  Thread  │ │Feeds │ │ 5 platforms │
└────┬───┘ └──┬────┘ └────┬───┘ └─────┬────┘ └──┬───┘ └──────┬──────┘
     │        │           │           │          │            │
     └────────┴───────────┴─────┬─────┴──────────┴────────────┘
                                │ raw jobs
                   ┌────────────▼────────────┐
                   │   Enrichment Pipeline   │
                   │  Gemini 2.5 Flash-Lite  │
                   │  (5/batch, 10 concurrent)│
                   └────────────┬────────────┘
                                │ structured 40-field jobs
                   ┌────────────▼────────────┐
                   │   Save Per Batch (DB)   │
                   │  dedup → insert/skip    │
                   └────────────┬────────────┘
                                │
                   ┌────────────▼────────────┐
                   │      PostgreSQL         │
                   │  tsvector + GIN index   │
                   │  full-text search       │
                   └─────────────────────────┘
```

### Components

| Directory | Purpose |
|-----------|---------|
| `src/agents/` | 6 fetcher agents — each pulls raw jobs from an external source |
| `src/enrichment/` | AI pipeline — Gemini processes raw data into 40-field schema |
| `src/services/` | Ingestion orchestration, company discovery, scheduling |
| `src/api/` | FastAPI routes, Pydantic schemas |
| `src/database/` | SQLAlchemy models, CRUD operations, full-text search |
| `src/utils/` | Config, logging |
| `scripts/` | Migration & utility scripts |

### AI Pipeline Flow

```
Raw API data → Gemini 2.5 Flash-Lite (JSON mode, temperature=0)
             → 40-field structured extraction
             → quality scoring
             → title_company_hash dedup
             → save to PostgreSQL
```

- **Batch size**: 5 jobs per Gemini API call
- **Concurrency**: 10 parallel batch calls
- **Fallback**: Rule-based extraction if AI is disabled or fails
- **Age filter**: Jobs older than 15 days are dropped

---

## 📊 Data Schema

Each job has **41 API fields** (42 DB columns including internal `search_vector`):

| Group | Fields |
|-------|--------|
| **Identity** | `id`, `source`, `source_id`, `source_url` |
| **Core** | `title`, `company`, `company_logo`, `company_website`, `description`, `short_description` |
| **Location** | `location`, `country`, `city`, `state`, `is_remote`, `work_arrangement`, `latitude`, `longitude` |
| **Employment** | `employment_type`, `seniority_level`, `department`, `category` |
| **Compensation** | `salary_min`, `salary_max`, `salary_currency`, `salary_period` |
| **Skills** | `skills`, `required_experience_years`, `required_education`, `key_responsibilities`, `nice_to_have_skills` |
| **Benefits** | `benefits`, `visa_sponsorship` |
| **Dates** | `posted_at`, `application_deadline`, `fetched_at` |
| **Apply** | `apply_url`, `apply_options` |
| **Meta** | `tags`, `quality_score` |

### Database Indexes

- `source + source_id` (unique) — deduplication
- `posted_at` — sort by recency
- `category`, `is_remote`, `seniority_level` — filter queries
- `skills` (GIN) — array containment queries
- `search_vector` (GIN) — full-text search
- `title`, `company` — direct lookups

---

## 🛠️ Development

### Project Structure

```
jobs.ai/
├── src/
│   ├── agents/              # Job fetcher agents
│   │   ├── __init__.py      # BaseFetcher ABC
│   │   ├── remoteok.py      # RemoteOK API
│   │   ├── jsearch.py       # JSearch via RapidAPI
│   │   ├── adzuna.py        # Adzuna API (7 countries)
│   │   ├── hackernews.py    # HN "Who is Hiring?" scraper
│   │   ├── rss_feed.py      # RSS feeds (WWR, RemoteOK)
│   │   └── ats_scraper.py   # ATS platforms (5 APIs)
│   ├── enrichment/          # AI processing layer
│   │   ├── ai_processor.py  # Gemini integration
│   │   ├── enrichment_pipeline.py  # Batch processing + fallback
│   │   ├── skills_extractor.py     # Rule-based skill extraction
│   │   └── quality_scorer.py       # Job quality scoring
│   ├── api/                 # FastAPI application
│   │   ├── main.py          # App factory + CORS
│   │   ├── routes.py        # Endpoint definitions
│   │   └── schemas.py       # Pydantic response models
│   ├── database/            # Data layer
│   │   ├── models.py        # SQLAlchemy models (42 columns)
│   │   └── operations.py    # CRUD + full-text search
│   ├── services/            # Business logic
│   │   ├── ingestion.py     # Orchestrator + scheduler
│   │   └── company_discovery.py  # SerpAPI company finder
│   ├── utils/               # Utilities
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   └── logger.py        # Logging setup
│   └── main.py              # Application entrypoint
├── scripts/                 # Migration & test scripts
├── tests/                   # Test suite
├── .env.example             # Example configuration
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container definition
├── docker-compose.yml       # Multi-service orchestration
└── README.md
```

### Adding a New Data Source

1. Create a fetcher in `src/agents/`:

```python
from src.agents import BaseFetcher

class NewSourceFetcher(BaseFetcher):
    def __init__(self):
        super().__init__("newsource")

    async def fetch_jobs(self):
        # Return list of raw dicts — no normalization needed
        # The AI pipeline handles all field extraction
        return [{"title": "...", "description": "...", ...}]
```

2. Register in `src/services/ingestion.py`:

```python
from src.agents.newsource import NewSourceFetcher

FETCHER_CLASSES = [
    ...,
    NewSourceFetcher,  # Add here
]
```

That's it — the enrichment pipeline and DB layer handle everything else.

---

## 🐛 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| `asyncpg.exceptions.InvalidCatalogNameError` | `docker-compose down -v && docker-compose up -d postgres` |
| `ssl.SSLCertVerificationError` | Add `ssl_no_verify=true` to DATABASE_URL |
| `429 Too Many Requests` | Increase `INGESTION_INTERVAL_MINUTES` in `.env` |
| `FutureWarning: google.generativeai` | Non-blocking — migration to `google.genai` planned |
| Server returns `500` on search | Check for malformed `location` data in DB |

### Test a Single Source

```python
from src.agents.remoteok import RemoteOKFetcher
import asyncio

async def test():
    fetcher = RemoteOKFetcher()
    jobs = await fetcher.fetch_jobs()
    print(f"Found {len(jobs)} jobs")

asyncio.run(test())
```

---

## 📊 Current Stats

- **Sources**: 6 (RemoteOK, JSearch, Adzuna, HackerNews, RSS, ATS Scraper)
- **ATS Platforms**: 5 (Greenhouse, Lever, Ashby, Workable, SmartRecruiters)
- **Adzuna Countries**: 7 (US, GB, CA, AU, DE, FR, NL)
- **Jobs per Run**: ~10,000+
- **Job Schema**: 41 API fields, AI-extracted
- **Search Speed**: ~35ms (PostgreSQL full-text, GIN indexed)
- **Processing**: 100% success rate (12,182/12,182 in last full run)
- **Fetch Interval**: 30 minutes (configurable)

---

## 📝 License

MIT License — see LICENSE file for details.

---

**Built with Python, FastAPI, PostgreSQL, and Gemini AI**
