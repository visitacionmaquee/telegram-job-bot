# JobRadar AI — Multi-Tenant AI Job Scraping & Career Intelligence SaaS

A cloud-native SaaS and automation platform built for software engineers, fresh graduates, and tech job seekers. Features automated scrapers for **LinkedIn, Indeed, and Glassdoor**, an AI-powered resume matching engine, a full **FastAPI** backend, and an interactive **Telegram Bot**.

---

## 🏗 System Architecture

```
                                  ┌────────────────────────────────┐
                                  │   Web Dashboard & Kanban UI    │
                                  │   (Tailwind CSS / Glassmorphism│
                                  │      at /dashboard)            │
                                  └───────────────┬────────────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │   FastAPI Backend   │
                                       │   (RESTful API)     │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                      ┌───────────────────────┐
                                      │ Celery + Redis Broker │
                                      │ (Async Task Queue)    │
                                      └──────────┬────────────┘
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

1. **Interactive Web Dashboard (`/dashboard`)**:
   * **Modern Dark-Mode Kanban Board**: 5 interactive application stages (`Matched / Saved`, `Applied`, `Interviewing`, `Offer Received`, `Archived`).
   * **Real-Time Asynchronous Job Radar**: Triggers Celery worker tasks via `POST /api/v1/jobs/scan-async` and polls execution state with a live animated progress bar.
   * **Candidate Profile & Resume Management**: In-browser skills tag editor, headline customizer, and target role adjuster synced with `PUT /api/v1/users/{id}/profile`.
   * **1-Click AI Outreach Copier**: Instantly copies personalized 300-character LinkedIn connection requests and customized cold email pitches.

2. **Multi-Tenant RESTful API (`api/`)**:
   * **FastAPI Backend**: Structured under modern clean architecture (`routes`, `models`, `schemas`, `services`).
   * **PostgreSQL / SQLAlchemy ORM**: Multi-user models with automatic SQLite fallback for local development.
   * **Interactive Swagger UI**: Explore and test live API endpoints at `http://localhost:8000/docs`.

3. **Asynchronous Task Queue (Celery + Redis)**:
   * **Decoupled Job Scraping**: Offloads long-running web scraping across LinkedIn, Indeed & Glassdoor to background Celery workers.
   * `POST /api/v1/jobs/scan-async` — Enqueues background scraping task, returns immediate task ID.
   * `GET /api/v1/tasks/{task_id}` — Polls task progress, execution state (`PENDING`, `PROGRESS`, `SUCCESS`), and result payload.

4. **Core Endpoints**:
   * `GET /dashboard` — Interactive Web Dashboard & Kanban Tracker.
   * `GET /health` — Real-time API & database connectivity check.
   * `GET /api/v1/users/default` — Automatic provisioning of candidate profile & telemetry state.
   * `POST /api/v1/users` — User onboarding and subscription tiering.
   * `PUT /api/v1/users/{id}/profile` — Candidate resume skills & target roles configuration.
   * `GET /api/v1/jobs` & `POST /api/v1/jobs/scan` — Job catalog querying & scraper trigger.
   * `POST /api/v1/jobs/scan-async` — Asynchronous background scan trigger.
   * `GET /api/v1/tasks/{task_id}` — Asynchronous task status poller.
   * `GET /api/v1/applications/pipeline-stats` — Kanban tracker summary (`saved`, `applied`, `interview`, `offer`).

5. **Enterprise Observability & Telemetry Suite (`monitoring/`)**:
   * **Prometheus Metrics Exporter (`/metrics`)**: Real-time instrumentation capturing HTTP latency histograms (`jobradar_http_request_duration_seconds`), scraper throughput (`jobradar_jobs_scraped_total`), AI match rate by quality tier, and Celery task execution states.
   * **Pre-Provisioned Grafana Dashboard (`http://localhost:3000`)**: Automated data source provisioning and dark-mode monitoring dashboard (`JobRadar AI — SaaS Telemetry & AI Observability`).

6. **IaaS & Oracle Cloud (OCI) Production Stack (`deploy/`, `docker-compose.prod.yml`)**:
   * **Nginx Reverse Proxy**: Production reverse proxy with Gzip compression, rate limiting (`limit_req_zone`), and hardened security headers (HSTS, CSP, X-Frame-Options).
   * **Automated Let's Encrypt SSL**: Certbot container with automated 12-hour certificate renewals.
   * **OCI Bootstrap Automation**: `deploy/setup_oci_vm.sh` configures Ubuntu/Oracle Linux VM, opens restrictive OCI iptables rules, installs Docker, and enables `systemd` auto-start.
   * **Zero-Trust Network Isolation**: Database and Redis are isolated within a private Docker bridge network (`jobradar_internal`), never exposed directly to the public internet.
   * **Full Deployment Guide**: Step-by-step instructions in [OCI Deployment Guide](file:///C:/Users/visit/.gemini/antigravity/scratch/telegram-job-bot/deploy/OCI_DEPLOYMENT_GUIDE.md).

7. **Automated CI/CD Pipeline (`.github/workflows/ci.yml`)**:
   * Automated syntax validation, code integrity, and 21-test `pytest` test suite on every git push.
   * Automated Docker container build validation.

---

## 💻 Quickstart (Local Development)

### 1. Run the FastAPI Backend
```bash
uvicorn api.main:app --reload --port 8000
```
Open your browser and navigate to:
* **Web Dashboard & Kanban Pipeline**: `http://127.0.0.1:8000/dashboard`
* **Prometheus Scrape Endpoint**: `http://127.0.0.1:8000/metrics`
* **Interactive API Docs**: `http://127.0.0.1:8000/docs`
* **Health Check**: `http://127.0.0.1:8000/health`

### 2. Run the Full Stack with Docker Compose (including Prometheus & Grafana)
```bash
docker compose up -d --build
```
* **Web Dashboard**: `http://localhost:8000/dashboard`
* **Grafana Telemetry**: `http://localhost:3000` (User: `admin`, Password: `admin`)
* **Prometheus Targets**: `http://localhost:9090`

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
