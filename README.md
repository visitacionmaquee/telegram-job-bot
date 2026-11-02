# MakieJob — AI Telegram Job Matcher & Scraper Bot

Personalized, AI-tailored Telegram bot that automatically searches **LinkedIn**, **Indeed**, and **Glassdoor**, analyzes job postings against your resume, and sends formatted alerts with match scores, tailored elevator pitches, and direct application links.

---

## 🎯 Bot Message Appearance
```text
🟢 [85% Match] Applications Developer
🏢 Company: inspiro
📍 Location: Makati, National Capital Region, Philippines | 🌐 Source: Glassdoor
🕒 Posted: 2026-10-31 | 🎓 Level: Entry Level / 0-1 yr (Unspecified)

🛠 Stack Match: Python, REST APIs, Git, PostgreSQL
🏆 Highlight Project: Velocity Engine — Hardware Telemetry & Observability Platform
💡 Quick Pitch: "Highlight your backend telemetry pipelines with Python, REST APIs, and Dockerized microservices built in your Velocity Engine project to prove immediate engineering value as an Applications Developer."

[ 🚀 Apply Now ↗ ]
[ 📝 Recruiter DM ] [ ⭐ Save ] [ ✅ Applied ]
```

---

## ⚙️ Features
- **Scrapes Real Listings**: Queries **LinkedIn, Indeed, and Glassdoor** without requiring paid accounts or API keys.
- **Personalized to Your Resume**:
  - Highlights your Computer Engineering background.
  - Matches against **Velocity Engine** (telemetry/backend/Docker), **E-Commerce QA Suite** (testing/Selenium/Postman), and **Milky Way Intern** experience.
- **Deduplication Engine**: Backed by SQLite so you never get notified of the same listing twice.
- **Scheduled Alerts**: Automatically scans in the background every few hours.
- **On-Demand Search**: Query any role or location instantly via Telegram commands.

---

## 🚀 How to Run the Bot

### Option 1: Quick Launcher (Windows)
Double-click:
```
run_bot.bat
```

### Option 2: Command Line
Open terminal in this directory:
```bash
.venv\Scripts\python.exe bot.py
```

---

## 📱 Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Show welcome message and status |
| `/scan` | Run an immediate scan of all default target roles on LinkedIn & Indeed |
| `/search <role> [in <loc>]` | Search on demand (e.g. `/search QA Engineer in Makati` or `/search Python Developer Remote`) |
| `/saved` | View your bookmarked jobs with application links |
| `/applied` | View all jobs you have submitted applications to |
| `/pipeline` | View your full job application tracker summary |
| `/profile` | View your parsed skills and showcase projects |
| `/stats` | View total jobs tracked and high-match count |
| `/auto <on/off>` | Turn automatic background alerts on or off |

---

## ⚡ Interactive Buttons Under Each Job
Under every job alert, you now have:
* **`[ 🚀 Apply Now ↗ ]`** — Opens the direct application page on LinkedIn or Indeed.
* **`[ 📝 Recruiter DM ]`** — Generates a tailored, ready-to-copy LinkedIn Connection note (<300 chars) and a direct InMail/Email pitch citing your showcase projects.
* **`[ ⭐ Save ]`** — Bookmarks the job to your `/saved` list.
* **`[ ✅ Applied ]`** — Moves the job to your `/applied` pipeline.

---

## 🔧 Customization
Edit `.env` to adjust:
- `DEFAULT_LOCATION`: default city or country (e.g. `Philippines` or `Makati`)
- `MIN_MATCH_PERCENT`: minimum match score to send a message (default `65`)
- `SCAN_INTERVAL_SECONDS`: interval between automatic scans (default `10800` = 3 hours)
- `GEMINI_API_KEY`: *(Optional)* Add a Google Gemini API key if you want generative AI pitches; otherwise the built-in smart pitch engine runs completely free.
