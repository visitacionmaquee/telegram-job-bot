# JobRadar AI — Multi-Tenant AI Job Scraping & Career Intelligence SaaS

A cloud-native SaaS and automation platform built for software engineers, fresh graduates, and tech job seekers. Features automated scrapers for **LinkedIn, Indeed, and Glassdoor**, an AI-powered resume matching engine, a full **FastAPI** backend, and an interactive **Telegram Bot**.

---

## 🏗 System Architecture

```
                                  [ Web Dashboard / Users ]
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │   FastAPI Backend   │
                                  │   (RESTful API)     │
                                  └──────────┬──────────┘
                                             │
                      ┌──────────────────────┼──────────────────────┐
                      ▼                      ▼                      ▼
            ┌──────────────────┐   ┌───────────────────┐  ┌──────────────────┐
            │ PostgreSQL DB    │   │ Multi-Board       │  │ Telegram Bot &   │
            │ (Users, Profile, │   │ Scraper Engine    │  │ Async Notifier   │
            │  Jobs, Kanban)   │   │ (LinkedIn/Indeed) │  │ (Instant Alerts) │
            └──────────────────┘   └───────────────────┘  └──────────────────┘
```

---

## 🚀 Key Modules & Capabilities

1. **Multi-Tenant RESTful API (`api/`)**:
   * **FastAPI Backend**: Structured under modern clean architecture (`routes`, `models`, `schemas`, `services`).
   * **PostgreSQL / SQLAlchemy ORM**: Multi-user models with automatic SQLite fallback for local development.
   * **Interactive Swagger UI**: Explore and test live API endpoints at `http://localhost:8000/docs`.

2. **Asynchronous Task Queue (Celery + Redis)**:
   * **Decoupled Job Scraping**: Offloads long-running web scraping across LinkedIn, Indeed & Glassdoor to background Celery workers.
   * `POST /api/v1/jobs/scan-async` — Enqueues background scraping task, returns immediate task ID.
   * `GET /api/v1/tasks/{task_id}` — Polls task progress, execution state (`PENDING`, `PROGRESS`, `SUCCESS`), and result payload.

3. **Core Endpoints**:
   * `GET /health` — Real-time API & database connectivity check.
   * `POST /api/v1/users` — User onboarding and subscription tiering.
   * `PUT /api/v1/users/{id}/profile` — Candidate resume skills & target roles configuration.
   * `GET /api/v1/jobs` & `POST /api/v1/jobs/scan` — Job catalog querying & scraper trigger.
   * `POST /api/v1/jobs/scan-async` — Asynchronous background scan trigger.
   * `GET /api/v1/tasks/{task_id}` — Asynchronous task status poller.
   * `GET /api/v1/applications/pipeline-stats` — Kanban tracker summary (`saved`, `applied`, `interview`, `offer`).

4. **IaaS & Containerization Ready**:
   * **Docker Compose**: Single-command startup of PostgreSQL 16 + Redis 7 + Celery Worker + FastAPI Backend + Bot Worker (`docker compose up --build`).
   * **Oracle Cloud (OCI) Ready**: Configured for deployment on Oracle Cloud Always-Free Compute instances.

5. **Automated CI/CD Pipeline (`.github/workflows/ci.yml`)**:
   * Automated syntax validation, code integrity, and 11-test `pytest` test suite on every git push.
   * Automated Docker container build validation.

---

## 💻 Quickstart (Local Development)

### 1. Run the FastAPI Backend
```bash
uvicorn api.main:app --reload --port 8000
```
Open your browser and navigate to:
* **Interactive API Docs**: `http://127.0.0.1:8000/docs`
* **Health Check**: `http://127.0.0.1:8000/health`

### 2. Run the Full Stack with Docker Compose
```bash
docker compose up -d --build
```

### 3. Run Automated Tests
```bash
pytest -v
```

---

## 📱 Bot Commands (Telegram)

| Command | Description |
| :--- | :--- |
| `/start` | Show welcome message and status |
| `/scan` | Run an immediate scan across LinkedIn, Indeed & Glassdoor |
| `/search <role> [in <loc>]` | Search on demand (e.g. `/search QA Engineer in Makati`) |
| `/saved` | View your bookmarked jobs with application links |
| `/applied` | View all jobs you have submitted applications to |
| `/pipeline` | View your full job application tracker summary |
| `/profile` | View your parsed skills and showcase projects |
| `/stats` | View total jobs tracked and high-match count |

---

## ⚡ Interactive Buttons Under Each Job
Under every job alert, you now have:
* **`[ Apply Now ]`** — Opens the direct application page on LinkedIn, Indeed, or Glassdoor.
* **`[ Outreach Pitch ]`** — Generates a tailored, ready-to-copy LinkedIn Connection note (<300 chars) and a direct InMail/Email pitch citing your showcase projects.
* **`[ Save Job ]`** — Bookmarks the job to your `/saved` list.
* **`[ Mark Applied ]`** — Moves the job to your `/applied` pipeline.

---

## ⏰ Automated Scanning Schedule
The bot automatically scans for new entry-level listings **once a day** at **8:00 AM Philippines Time (PHT / UTC+8)**:
* **08:00 AM PHT** (Daily morning scan across LinkedIn, Indeed & Glassdoor)

---

## 🔧 Customization
Edit `.env` to adjust:
- `DEFAULT_LOCATION`: default city or country (e.g. `Philippines` or `Makati`)
- `MIN_MATCH_PERCENT`: minimum match score to send a message (default `65`)
- `SCAN_INTERVAL_SECONDS`: interval between automatic scans (default `10800` = 3 hours)
- `GEMINI_API_KEY`: *(Optional)* Add a Google Gemini API key if you want generative AI pitches; otherwise the built-in smart pitch engine runs completely free.
