"""Domain models for Job Hunt OS."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Job:
    """Dataclass representing a job posting.

    Fields are intentionally simple and str-typed where appropriate to keep
    Notion mapping straightforward.
    """
    company: str
    position: str
    location: Optional[str] = None
    salary: Optional[str] = None
    website: Optional[str] = None
    job_url: Optional[str] = None
    application_date: Optional[date] = None
    status: Optional[str] = None
    contact: Optional[str] = None
    next_action: Optional[str] = None
    source: Optional[str] = None
