"""Job provider implementations.

Network providers are read-only. Sending remains a separate, explicitly
authorized capability.
"""
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .core import (
    AuthorizedMockProvider,
    Job,
    JobProvider,
    MockProvider,
    ProviderCapabilities,
    ProviderRegistry,
)


class HttpJobProvider:
    """Fetch a JSON job feed using GET only.

    Feed format: a list of objects, or ``{"jobs": [...]}``, with ``title``,
    ``description`` and optional Job fields. Platform-specific authentication
    and terms remain the caller's responsibility.
    """

    capabilities = ProviderCapabilities(search=True, details=True, authorized_send=False)

    def __init__(self, endpoint: str, name: str = 'http', timeout: float = 15):
        parsed = urlparse(endpoint)
        if parsed.scheme != 'https' or not parsed.netloc:
            raise ValueError('job feed endpoint must be an absolute HTTPS URL')
        self.endpoint = endpoint
        self.name = name
        self.timeout = timeout

    def search(self) -> list[Job]:
        request = Request(self.endpoint, headers={'Accept': 'application/json', 'User-Agent': 'FreelaHunter/0.1'})
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
        rows = payload.get('jobs', []) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError('job feed must be a JSON list or object with jobs list')
        return [Job(platform=self.name, **self._job_fields(row)) for row in rows]

    @staticmethod
    def _job_fields(row: dict) -> dict:
        if not isinstance(row, dict) or not row.get('title') or not row.get('description'):
            raise ValueError('each job must include title and description')
        allowed = {'title', 'description', 'external_id', 'url', 'budget_min', 'budget_max', 'currency', 'skills', 'category', 'client', 'published_at'}
        return {key: row[key] for key in allowed if key in row}


__all__ = [
    'JobProvider', 'ProviderCapabilities', 'ProviderRegistry', 'MockProvider',
    'AuthorizedMockProvider', 'HttpJobProvider',
]
