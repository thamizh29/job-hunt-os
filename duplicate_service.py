"""Duplicate detection service.

Detects duplicates by `company` + `position`. Designed to be extended with
fuzzy matching in the future.
"""
from __future__ import annotations

from typing import Iterable, List

from models import Job


class DuplicateService:
    """Service to detect duplicates among jobs.

    Current strategy: exact match on (company, position) lower-cased.
    Future improvements: fuzzy matching, synonyms, alias lookup.
    """

    @staticmethod
    def unique_jobs(jobs: Iterable[Job]) -> List[Job]:
        """Return a deduplicated list preserving first occurrence order.

        Args:
            jobs: Iterable of `Job` objects.

        Returns:
            List of unique `Job` objects.
        """
        seen = set()
        unique = []
        for job in jobs:
            key = (job.company.strip().lower(), job.position.strip().lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(job)
        return unique


__all__ = ["DuplicateService"]
