from __future__ import annotations

import re


CODE_PATTERNS = [
    re.compile(r"https?://github\.com/[^\s)>\]]+", re.I),
    re.compile(r"https?://gitlab\.com/[^\s)>\]]+", re.I),
    re.compile(r"https?://bitbucket\.org/[^\s)>\]]+", re.I),
]


def find_code_url(text: str) -> str:
    for pattern in CODE_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return match.group(0).rstrip(".,")
    return ""
