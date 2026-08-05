"""Notion integration service.

Wraps `notion-client` usage behind a small service class. Keeps methods
modular and testable.
"""
from __future__ import annotations

from typing import Optional
import logging

from notion_client import Client

from models import Job


class NotionService:
    """A thin wrapper over Notion `Client` for job operations."""

    def __init__(self, token: str, database_id: str, logger: Optional[logging.Logger] = None) -> None:
        self._client = Client(auth=token)
        self.database_id = database_id
        self.logger = logger or logging.getLogger("notion_service")

    def job_exists(self, company: str, position: str) -> bool:
        """Return True if a page matching company+position exists in the DB.

        Uses Notion database query filters for equality. This is fast and
        predictable; future improvements could add fuzzy matching.
        """
        try:
            filter_payload = {
                "and": [
                    {"property": "Company", "rich_text": {"equals": company}},
                    {"property": "Position", "title": {"equals": position}},
                ]
            }
            result = self._client.databases.query(database_id=self.database_id, filter=filter_payload)
            return bool(result.get("results"))
        except Exception as exc:
            self.logger.exception("Failed to query Notion for existence check: %s", exc)
            # If the check cannot run, we signal False to avoid skipping insertions
            return False

    def insert_job(self, job: Job) -> Optional[str]:
        """Insert a `Job` into the Notion database.

        Returns the created page id on success; None on failure.
        """
        try:
            properties = {
                "Company": {"rich_text": [{"text": {"content": job.company}}]},
                "Position": {"title": [{"text": {"content": job.position}}]},
                "Location": {"rich_text": [{"text": {"content": job.location or ""}}]},
                "Website": {"url": job.website},
                "Job URL": {"url": job.job_url},
                "Source": {"rich_text": [{"text": {"content": job.source or ""}}]},
            }

            page = self._client.pages.create(parent={"database_id": self.database_id}, properties=properties)
            page_id = page.get("id")
            self.logger.info("Inserted job into Notion: %s @ %s", job.position, job.company)
            return page_id
        except Exception as exc:
            self.logger.exception("Failed to insert job into Notion: %s", exc)
            return None

    def update_job(self, page_id: str, job: Job) -> bool:
        """Update a job page. Minimal implementation to keep API stable.

        Returns True on success.
        """
        try:
            properties = {
                "Location": {"rich_text": [{"text": {"content": job.location or ""}}]},
                "Website": {"url": job.website},
            }
            self._client.pages.update(page_id=page_id, properties=properties)
            self.logger.info("Updated Notion page %s", page_id)
            return True
        except Exception as exc:
            self.logger.exception("Failed to update Notion page %s: %s", page_id, exc)
            return False

    def delete_job(self, page_id: str) -> bool:
        """Archive (delete) a page in Notion by setting `archived=True`.

        Returns True on success.
        """
        try:
            self._client.pages.update(page_id=page_id, archived=True)
            self.logger.info("Archived Notion page %s", page_id)
            return True
        except Exception as exc:
            self.logger.exception("Failed to archive Notion page %s: %s", page_id, exc)
            return False


__all__ = ["NotionService"]
