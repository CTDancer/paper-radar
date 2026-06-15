from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"


def load_config(name: str, config_dir: Path | None = None) -> dict[str, Any]:
    path = (config_dir or CONFIG_DIR) / name
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return json.loads(strip_json_trailing_commas(text))
        except json.JSONDecodeError:
            try:
                return parse_simple_yaml(text)
            except ValueError as simple_yaml_error:
                try:
                    import yaml  # type: ignore
                except ModuleNotFoundError as exc:
                    raise ValueError(
                        f"{path} is not JSON-compatible YAML and PyYAML is not installed. "
                        f"Simple parser error: {simple_yaml_error}"
                    ) from exc
                loaded = yaml.safe_load(text)
                return loaded or {}


def load_all_configs(config_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    return {
        "topics": load_config("topics.yaml", config_dir),
        "sources": load_config("sources.yaml", config_dir),
        "ranking": load_config("ranking.yaml", config_dir),
        "summary_style": load_config("summary_style.yaml", config_dir),
        "seed_papers": load_config("seed_papers.yaml", config_dir),
    }


def strip_json_trailing_commas(text: str) -> str:
    """Allow JSON-compatible config files to contain YAML-style trailing commas."""
    return re.sub(r",(\s*[}\]])", r"\1", text)


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by Paper Radar config files.

    This keeps automation runs self-contained when PyYAML is not installed. It
    intentionally supports only nested mappings, scalar values, and scalar
    lists, which is enough for the repo's hand-edited config files.
    """
    lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        raw_line = raw_line.rstrip()
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        line = raw_line.split(" #", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if "\t" in line[:indent]:
            raise ValueError("Tabs are not supported in simple YAML config.")
        lines.append((indent, line.strip()))

    if not lines:
        return {}
    parsed, index = _parse_yaml_block(lines, 0, lines[0][0])
    if index != len(lines) or not isinstance(parsed, dict):
        raise ValueError("Unsupported YAML structure.")
    return parsed


def _parse_yaml_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    current_indent, current_text = lines[index]
    if current_indent != indent:
        raise ValueError("Inconsistent YAML indentation.")
    if current_text.startswith("- "):
        return _parse_yaml_list(lines, index, indent)
    return _parse_yaml_dict(lines, index, indent)


def _parse_yaml_dict(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError("Unexpected nested YAML value.")
        if text.startswith("- ") or ":" not in text:
            break

        key, raw_value = text.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise ValueError("YAML mapping key cannot be empty.")
        index += 1

        if raw_value:
            result[key] = _parse_yaml_scalar(raw_value)
            continue
        if index >= len(lines) or lines[index][0] <= current_indent:
            result[key] = {}
            continue
        result[key], index = _parse_yaml_block(lines, index, lines[index][0])
    return result, index


def _parse_yaml_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent or not text.startswith("- "):
            raise ValueError("Unsupported nested YAML list item.")
        item = text[2:].strip()
        if not item:
            raise ValueError("Nested list items are not supported in simple YAML config.")
        result.append(_parse_yaml_scalar(item))
        index += 1
    return result, index


def _parse_yaml_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value



def reports_dir(repo_root: Path = REPO_ROOT) -> Path:
    """Return the directory where daily Markdown reports should be written."""
    override = os.getenv("PAPER_RADAR_REPORTS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return repo_root.parent / "Daily_Papers"
