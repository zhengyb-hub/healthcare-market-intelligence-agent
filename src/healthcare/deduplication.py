"""Transparent, non-embedding duplicate detection for Healthcare Evidence."""

from __future__ import annotations

from difflib import SequenceMatcher
import hashlib
import re
from typing import Iterable


def clean_text(value: object, limit: int = 20_000) -> str:
    """Generalise the legacy collector's whitespace cleaning behavior."""
    return " ".join(str(value or "").split())[:limit]


def content_fingerprint(value: object) -> str:
    """Return a stable SHA-256 content hash for exact duplicate detection."""
    normalized = clean_text(value).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalized_title(value: object) -> str:
    text = clean_text(value).casefold()
    return re.sub(r"[^\w\s]", "", text)


def find_near_duplicate_title(
    title: str,
    candidates: Iterable[tuple[str, str]],
    threshold: float = 0.92,
) -> tuple[str, float] | None:
    """Find the closest same-vendor title above a transparent threshold."""
    normalized = normalized_title(title)
    if not normalized:
        return None
    best_id = ""
    best_ratio = 0.0
    for evidence_id, candidate in candidates:
        ratio = SequenceMatcher(
            None,
            normalized,
            normalized_title(candidate),
        ).ratio()
        if ratio > best_ratio:
            best_id = evidence_id
            best_ratio = ratio
    if best_id and best_ratio >= threshold:
        return best_id, best_ratio
    return None
