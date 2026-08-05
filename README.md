# Job Hunt OS

Small, production-ready Job Hunt OS to fetch, filter, deduplicate and store software engineering job postings into a Notion database.

Installation

1. Create a virtual environment and activate it.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and set `NOTION_TOKEN` and `DATABASE_ID`.

Environment variables

- `NOTION_TOKEN`: Notion integration token (store in GitHub Secrets too).
- `DATABASE_ID`: Notion database id for the job tracker.
- `LOG_FILE`: Path to log file (optional).

Running locally

```powershell
python app.py
```

GitHub Actions

See `.github/workflows/jobs.yml`. The workflow runs at 6:00 AM IST and 9:00 PM IST and supports `workflow_dispatch`.

Architecture

- `config.py` — environment loader and validation
- `models.py` — domain model (`Job` dataclass)
- `fetch_jobs.py` — provider-agnostic job fetcher (sample data for now)
- `duplicate_service.py` — duplicate detection logic
- `notion_service.py` — Notion integration wrapper
- `logger.py` — logging configuration
- `app.py` — orchestrates fetching, filtering and persisting

Extensibility

Add new providers in `fetch_jobs.py` or a providers package; extend `duplicate_service` for fuzzy matching.
