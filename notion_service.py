"""Notion integration service.

Wraps `notion-client` usage behind a small service class. Keeps methods
modular and testable.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Any

from notion_client import Client
from models import Job


class NotionService:
    """A thin wrapper over Notion `Client` for job operations.

    This service inspects the database schema automatically and builds
    property payloads and filters dynamically based on a strict mapping.
    It uses the official `notion-client` methods and handles missing properties gracefully.
    """

    # Static property mapping as requested
    EXPECTED_MAPPING = {
        "Company": "title",
        "Position": "rich_text",
        "Status": "multi_select",
        "Application Date": "date",
        "Salary": "number",
        "Next Action": "multi_select",
        "Website": "url",
        "Contact": "email",
        "Reference Link": "url"
    }

    def __init__(self, token: str, database_id: str, logger: Optional[logging.Logger] = None) -> None:
        self._client = Client(auth=token)
        self.database_id = database_id
        self.logger = logger or logging.getLogger("notion_service")
        self._properties: Optional[Dict] = None

    def _query_database(self, payload: dict) -> dict:
        """Helper to safely call the databases query endpoint.
        Uses _client.request directly because notion-client 3.x removed databases.query()
        """
        return self._client.request(
            path=f"databases/{self.database_id}/query",
            method="POST",
            body=payload
        )

    def _ensure_properties(self) -> Dict:
        """Retrieve and cache database properties (schema) from Notion."""
        if self._properties is None:
            try:
                db = self._client.databases.retrieve(database_id=self.database_id)
                self.logger.debug("Retrieved schema (raw DB object): %s", db)
                
                props = db.get("properties")
                
                # If properties are missing from the DB object (e.g. linked views), infer from a single page query
                if not props:
                    self.logger.debug("Properties not found in DB object, querying a single page to infer schema.")
                    try:
                        result = self._query_database({"page_size": 1})
                        pages = result.get("results", [])
                        if pages:
                            props = pages[0].get("properties", {})
                    except Exception as exc:
                        self.logger.warning("Could not query DB to infer schema (linked views cannot be queried directly): %s", exc)
                
                if props:
                    print("\nDatabase Properties:")
                    for p_name in props.keys():
                        print(p_name)
                    self.logger.debug("Database property names: %s", list(props.keys()))
                    self._properties = props
                else:
                    self._properties = {}
            except Exception as exc:
                self.logger.exception("Failed to retrieve database schema: %s", exc)
                self._properties = {}
        return self._properties

    def _build_payload_value(self, prop_type: str, value: Any) -> Optional[Dict]:
        """Build the property payload dynamically based on the expected type."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
            
        if prop_type == "title":
            return {"title": [{"text": {"content": str(value)}}]}
        elif prop_type == "rich_text":
            return {"rich_text": [{"text": {"content": str(value)}}]}
        elif prop_type == "multi_select":
            return {"multi_select": [{"name": str(value)}]}
        elif prop_type == "date":
            if hasattr(value, "isoformat"):
                return {"date": {"start": value.isoformat()}}
            return {"date": {"start": str(value)}}
        elif prop_type == "number":
            try:
                return {"number": float(value)}
            except Exception:
                return None
        elif prop_type == "url":
            return {"url": str(value)}
        elif prop_type == "email":
            return {"email": str(value)}
        return None

    def job_exists(self, company: str, position: str) -> bool:
        """Return True if a page matching company+position exists in the DB.
        Provides duplicate detection.
        """
        props = self._ensure_properties()
        clauses = []
        has_schema = bool(props)
        
        if not has_schema or ("Company" in props and props["Company"].get("type") == "title"):
            clauses.append({"property": "Company", "title": {"equals": company}})
        else:
            self.logger.warning("Cannot check duplicates: 'Company' property missing or not title type.")
            
        if not has_schema or ("Position" in props and props["Position"].get("type") == "rich_text"):
            clauses.append({"property": "Position", "rich_text": {"equals": position}})
        else:
            self.logger.warning("Cannot check duplicates: 'Position' property missing or not rich_text type.")
            
        if not clauses:
            self.logger.warning("Insufficient properties to perform existence check; skipping Notion query")
            return False

        filter_payload = {"and": clauses}
        try:
            result = self._query_database(filter_payload)
            return bool(result.get("results"))
        except Exception as exc:
            self.logger.warning("Duplicate check skipped. (Querying this ID is likely unsupported by Notion API): %s", exc)
            return False

    def insert_job(self, job: Job) -> Optional[str]:
        """Insert a `Job` into the Notion database using strict mapping."""
        props = self._ensure_properties()
        has_schema = bool(props)
        
        print("\nMapped Property Types:")
        for name, expected_type in self.EXPECTED_MAPPING.items():
            if has_schema:
                if name in props:
                    print(f"{name} -> {expected_type}")
            else:
                print(f"{name} -> {expected_type} (assumed, schema unavailable)")
            
        job_values = {
            "Company": job.company,
            "Position": job.position,
            "Status": job.status,
            "Application Date": job.application_date,
            "Salary": job.salary,
            "Next Action": job.next_action,
            "Website": job.website,
            "Contact": job.contact,
            "Reference Link": job.job_url,
        }
        
        properties = {}
        for logical_name, expected_type in self.EXPECTED_MAPPING.items():
            if has_schema:
                if logical_name not in props:
                    print(f"WHY property missing: '{logical_name}' is not defined in the database schema.")
                    continue
                    
                actual_type = props[logical_name].get("type")
                if actual_type != expected_type:
                    print(f"WHY property missing: '{logical_name}' has actual type '{actual_type}' but expected '{expected_type}'.")
                    continue
                
            val = job_values.get(logical_name)
            payload_value = self._build_payload_value(expected_type, val)
            if payload_value:
                properties[logical_name] = payload_value

        self.logger.debug("Generated payload: %s", properties)
        
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
        """Update a job page. Minimal implementation to keep API stable."""
        props = self._ensure_properties()
        has_schema = bool(props)
        properties = {}
        
        if not has_schema or ("Website" in props and props["Website"].get("type") == "url"):
            val = self._build_payload_value("url", job.website)
            if val:
                properties["Website"] = val
                
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
        """Archive (delete) a page in Notion by setting `archived=True`."""
        try:
            self._client.pages.update(page_id=page_id, archived=True)
            self.logger.info("Archived Notion page %s", page_id)
            return True
        except Exception as exc:
            self.logger.exception("Failed to archive Notion page %s: %s", page_id, exc)
            return False


__all__ = ["NotionService"]
