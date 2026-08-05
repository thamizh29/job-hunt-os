"""Main entry point for Job Hunt OS.

Fetches jobs, deduplicates, and inserts new entries into Notion.
"""
from __future__ import annotations

import sys
from typing import List

from config import load_settings
from duplicate_service import DuplicateService
from fetch_jobs import FetchJobs
from logger import setup_logger
from models import Job
from notion_service import NotionService


def main() -> int:
    """Run the job hunt flow and return an exit code.

    Returns 0 on success, non-zero on failure.
    """
    try:
        settings = load_settings()
    except Exception as exc:
        print(f"Configuration error: {exc}")
        return 2

    logger = setup_logger(log_file=settings.log_file)

    notion = NotionService(token=settings.notion_token, database_id=settings.database_id, logger=logger)
    fetcher = FetchJobs()

    try:
        jobs: List[Job] = fetcher.fetch()
        logger.info("Fetched %d jobs from providers", len(jobs))

        jobs = DuplicateService.unique_jobs(jobs)
        logger.info("After deduplication %d jobs remain", len(jobs))

        inserted = 0
        for job in jobs:
            try:
                if notion.job_exists(job.company, job.position):
                    logger.info("Skipping existing job: %s @ %s", job.position, job.company)
                    continue

                page_id = notion.insert_job(job)
                if page_id:
                    inserted += 1
            except Exception as inner:
                logger.exception("Failed to handle job %s @ %s: %s", job.position, job.company, inner)

        logger.info("Insertion complete. New jobs inserted: %d", inserted)
        return 0
    except Exception as exc:
        logger.exception("Unhandled error in main flow: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
import os
from datetime import datetime

from dotenv import load_dotenv
from notion_client import Client

# Load .env
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

notion = Client(auth=NOTION_TOKEN)

today = datetime.today().strftime("%Y-%m-%d")

response = notion.pages.create(
    parent={
        "database_id": DATABASE_ID
    },
    properties={
        "Company": {
            "title": [
                {
                    "text": {
                        "content": "Microsoft"
                    }
                }
            ]
        },

        "Position": {
            "rich_text": [
                {
                    "text": {
                        "content": "Software Engineer"
                    }
                }
            ]
        },

        "Status": {
    "multi_select": [
        {
            "name": "Applied"
        }
    ]
},

        "Application Date": {
            "date": {
                "start": today
            }
        },

        "Salary": {
            "number": 1200000
        },

        "Website": {
            "url": "https://careers.microsoft.com"
        },

        "Contact": {
    "email": "hr@microsoft.com"
},

        "Reference Link": {
            "url": "https://careers.microsoft.com"
        }
    }
)

print("✅ Job inserted successfully!")
print(response["url"])