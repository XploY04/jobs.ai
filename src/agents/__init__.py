from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseFetcher(ABC):
    """Base class providing shared helpers for all fetcher agents."""

    BACKEND_KEYWORDS = [
        "backend",
        "back-end",
        "back end",
        "devops",
        "dev ops",
        "devsecops",
        "sre",
        "site reliability",
        "cloud engineer",
        "cloud architect",
        "platform engineer",
        "infrastructure",
        "systems engineer",
        "golang",
        "python backend",
        "java backend",
        "node.js backend",
        "kubernetes",
        "k8s",
        "docker",
        "terraform",
        "ansible",
    ]

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    @abstractmethod
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch and normalize jobs for the specific source."""

    def is_backend_devops_job(self, title: str, description: str = "") -> bool:
        """Return True if text appears to describe a backend/devops role."""

        haystack = f"{title} {description}".lower()
        return any(keyword in haystack for keyword in self.BACKEND_KEYWORDS)
