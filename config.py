"""Configuration loader using environment variables and dotenv.

Validates required variables and exposes a simple `Settings` object.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    notion_token: str
    database_id: str
    log_file: str
    timezone: str = "Asia/Kolkata"


def load_settings() -> Settings:
    """Load and validate environment settings.

    Raises:
        EnvironmentError: when a required variable is missing.
    """
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("DATABASE_ID")
    log_file = os.getenv("LOG_FILE", "logs/jobhunt.log")
    timezone = os.getenv("TIMEZONE", "Asia/Kolkata")

    missing = []
    if not notion_token:
        missing.append("NOTION_TOKEN")
    if not database_id:
        missing.append("DATABASE_ID")

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return Settings(notion_token=notion_token, database_id=database_id, log_file=log_file, timezone=timezone)


__all__ = ["load_settings", "Settings"]
