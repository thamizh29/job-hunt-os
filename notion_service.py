"""Notion integration service.

Wraps `notion-client` usage behind a small service class. Keeps methods
modular and testable.
"""
from __future__ import annotations

from typing import Dict, Optional
import logging

from notion_client import Client

from models import Job


class NotionService:
    """A thin wrapper over Notion `Client` for job operations.

    This service inspects the database schema automatically and builds
    property payloads and filters dynamically to avoid hardcoding property
    types or names. It uses the official `notion-client` methods and
    handles missing properties gracefully.
    """

    # Supported properties we care about and their expected Notion types
    KNOWN_PROPERTIES = {
        "Company": "title",
        "Position": "rich_text",
        "Status": "multi_select",
        "Application Date": "date",
        "Salary": "number",
        "Next Action": "multi_select",
        "Website": "url",
        "Contact": "email",
        "Reference Link": "url",
    }

    def __init__(self, token: str, database_id: str, logger: Optional[logging.Logger] = None) -> None:
        self._client = Client(auth=token)
        self.database_id = database_id
        self.logger = logger or logging.getLogger("notion_service")
        self._properties: Optional[Dict] = None

    def _ensure_properties(self) -> Dict:
        """Retrieve and cache database properties (schema) from Notion.

        Returns the properties dict from the Notion database object.
        """
        if self._properties is None:
            try:
                db = self._client.databases.retrieve(database_id=self.database_id)
                props = db.get("properties", {})
                self._properties = props
            except Exception as exc:
                self.logger.exception("Failed to retrieve database schema: %s", exc)
                self._properties = {}
        return self._properties

    def _property_exists(self, name: str) -> bool:
        props = self._ensure_properties()
        return name in props

    def job_exists(self, company: str, position: str) -> bool:
        """Return True if a page matching company+position exists in the DB.

        Builds a type-aware filter using the inspected database schema and
        queries the database. Returns False on errors to allow inserts to
        continue rather than silently skipping them.
        """
        props = self._ensure_properties()

        # Build filter clauses only if the properties exist and we know a
        # compatible filter operator for their type.
        clauses = []

        # Company filter (expecting a title property)
        if "Company" in props:
            prop_type = props["Company"].get("type")
            if prop_type == "title":
                clauses.append({"property": "Company", "title": {"equals": company}})
            else:
                self.logger.warning("Property 'Company' exists but is type '%s' (expected 'title')", prop_type)
        else:
            self.logger.warning("Property 'Company' not found in database schema")

        # Position filter (expecting rich_text)
        if "Position" in props:
            prop_type = props["Position"].get("type")
            if prop_type == "rich_text":
                clauses.append({"property": "Position", "rich_text": {"equals": position}})
            else:
                self.logger.warning("Property 'Position' exists but is type '%s' (expected 'rich_text')", prop_type)
        else:
            self.logger.warning("Property 'Position' not found in database schema")

        if not clauses:
            self.logger.warning("Insufficient properties to perform existence check; skipping Notion query")
            return False

        filter_payload = {"and": clauses}
        try:
            result = self._client.databases.query(database_id=self.database_id, filter=filter_payload)
            return bool(result.get("results"))
        except Exception as exc:
            self.logger.exception("Failed to query Notion for existence check: %s", exc)
            return False

    def insert_job(self, job: Job) -> Optional[str]:
        """Insert a `Job` into the Notion database.

        Builds the properties payload dynamically based on the database schema.
        Skips properties that do not exist in the database and logs missing
        properties. Returns created page id on success, or None on failure.
        """
        props_schema = self._ensure_properties()

        properties = {}

        # Company -> Title
        if "Company" in props_schema and props_schema["Company"].get("type") == "title":
            properties["Company"] = {"title": [{"text": {"content": job.company}}]}
        else:
            self.logger.warning("Skipping 'Company' property: not present or not title in DB")

        # Position -> Rich Text
        if "Position" in props_schema and props_schema["Position"].get("type") == "rich_text":
            properties["Position"] = {"rich_text": [{"text": {"content": job.position}}]}
        else:
            self.logger.warning("Skipping 'Position' property: not present or not rich_text in DB")

        # Optional properties
        optional_mappings = [
            ("Status", "multi_select", lambda v: [{"name": v}] if v else []),
            ("Application Date", "date", lambda v: {"start": v.isoformat()} if v else None),
            ("Salary", "number", lambda v: float(v) if v is not None and str(v).strip() != "" else None),
            ("Next Action", "multi_select", lambda v: [{"name": v}] if v else []),
            ("Website", "url", lambda v: v if v else None),
            ("Contact", "email", lambda v: v if v else None),
            ("Reference Link", "url", lambda v: v if v else None),
        ]

        for name, expected_type, transform in optional_mappings:
            if name not in props_schema:
                # Not all databases will have every field; skip gracefully.
                continue
            actual_type = props_schema[name].get("type")
            if actual_type != expected_type:
                self.logger.warning("Property '%s' has type '%s' but expected '%s'", name, actual_type, expected_type)
                continue

            try:
                value = None
                if name == "Status":
                    value = transform(job.status)
                    if value:
                        properties[name] = {"multi_select": value}
                elif name == "Application Date":
                    if job.application_date:
                        properties[name] = {"date": transform(job.application_date)}
                elif name == "Salary":
                    if job.salary is not None:
                        # salary may be a range string; only attempt numeric conversion
                        try:
                            properties[name] = {"number": transform(job.salary)}
                        except Exception:
                            self.logger.warning("Could not convert Salary '%s' to number; skipping", job.salary)
                elif name == "Next Action":
                    value = transform(job.next_action)
                    if value:
                        properties[name] = {"multi_select": value}
                elif name == "Website":
                    if job.website:
                        properties[name] = {"url": transform(job.website)}
                elif name == "Contact":
                    if job.contact:
                        properties[name] = {"email": transform(job.contact)}
                elif name == "Reference Link":
                    if job.job_url:
                        properties[name] = {"url": transform(job.job_url)}
            except Exception as exc:
                self.logger.exception("Failed to map property '%s': %s", name, exc)

        if not properties:
            self.logger.error("No valid properties to insert for job: %s @ %s", job.position, job.company)
            return None

        try:
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
        props_schema = self._ensure_properties()
        properties = {}

        if "Website" in props_schema and props_schema["Website"].get("type") == "url" and job.website:
            properties["Website"] = {"url": job.website}

        if not properties:
            self.logger.info("Nothing to update for page %s", page_id)
            return True

        try:
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
