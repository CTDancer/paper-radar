from __future__ import annotations

import http.client
import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any

from paper_radar.models import Paper

LOGGER = logging.getLogger(__name__)


class SourceFetcher(ABC):
    name = "base"

    def __init__(
        self,
        timeout: int = 30,
        max_results: int = 80,
        max_failures: int = 3,
        settings: dict[str, Any] | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_results = max_results
        self.max_failures = max_failures
        self.settings = settings or {}
        self.request_errors: list[str] = []

    @abstractmethod
    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        raise NotImplementedError

    def enrich(self, papers: list[Paper]) -> list[Paper]:
        return papers

    def get_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        request = urllib.request.Request(url, headers=headers or {"User-Agent": "paper-radar/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            self._record_error(f"HTTP {exc.code}")
            LOGGER.debug("%s request failed: HTTP %s for %s", self.name, exc.code, url)
            return ""
        except (urllib.error.URLError, TimeoutError, socket.timeout, http.client.RemoteDisconnected) as exc:
            label = classify_network_error(exc)
            self._record_error(label)
            LOGGER.debug("%s request failed: %s for %s", self.name, exc, url)
            return ""

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        text = self.get_text(url, headers=headers)
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            self._record_error("invalid JSON")
            LOGGER.debug("%s returned invalid JSON: %s", self.name, exc)
            return {}

    def _record_error(self, label: str) -> None:
        self.request_errors.append(label)

    def should_stop(self) -> bool:
        return len(self.request_errors) >= self.max_failures

    def saw_status(self, status: str) -> bool:
        return status in self.request_errors

    def error_summary(self) -> str:
        counts = Counter(self.request_errors)
        return ", ".join(f"{label} x{count}" for label, count in sorted(counts.items()))

    @staticmethod
    def quote(value: str) -> str:
        return urllib.parse.quote(value)


def classify_network_error(exc: BaseException) -> str:
    text = str(exc).lower()
    if "timed out" in text or "timeout" in text:
        return "timeout"
    if "nodename nor servname" in text or "name or service" in text:
        return "DNS failure"
    if "ssl" in text:
        return "SSL error"
    return exc.__class__.__name__
