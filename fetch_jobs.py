"""FetchJobs provider-agnostic fetcher.

Currently returns sample data; structured to add new providers later.
"""
from __future__ import annotations

from datetime import date
from typing import List

from models import Job


class FetchJobs:
    """Fetch jobs from configured providers.

    For now this returns sample data. Extend by adding provider classes and
    composing them here.
    """

    def fetch(self) -> List[Job]:
        """Return a list of `Job` objects (sample data presently).

        In production this would orchestrate providers like Greenhouse, Lever,
        Wellfound (AngelList), etc.
        """
        sample = [
            Job(
                company="ACME Corp",
                position="Software Engineer",
                location="Remote",
                salary="80k-110k",
                website="https://acme.example.com",
                job_url="https://acme.example.com/jobs/123",
                application_date=date.today(),
                status="new",
                contact=None,
                next_action="apply",
                source="sample",
            ),
            Job(
                company="Beta Systems",
                position="Backend Engineer",
                location="Bengaluru, India",
                salary=None,
                website="https://beta.example.com",
                job_url="https://beta.example.com/jobs/789",
                application_date=date.today(),
                status="new",
                contact=None,
                next_action="review",
                source="sample",
            ),
        ]
        return sample


__all__ = ["FetchJobs"]
