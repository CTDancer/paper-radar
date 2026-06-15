from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from paper_radar.config import REPO_ROOT


class LLMClient:
    def __init__(self, model: str | None = None) -> None:
        load_dotenv(REPO_ROOT / ".env")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.5-high")
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, prompt: str) -> str:
        if not self.available:
            return ""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a careful research-paper summarization assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "paper-radar/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception:
            return ""



def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE pairs without requiring python-dotenv."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
