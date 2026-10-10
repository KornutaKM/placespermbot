"""Validate non-secret source revisions embedded into Docker images."""

from __future__ import annotations

import re

_SHA = re.compile(r"[0-9a-f]{40}", flags=re.ASCII)


def public_build_sha(value: str) -> str:
    """Never echo arbitrary env content through public diagnostics."""
    return value if _SHA.fullmatch(value) else "unverified"


def require_build_revision(expected_sha: str, image_sha: str) -> str:
    """Fail closed unless an operator-approved commit matches the image."""
    if _SHA.fullmatch(expected_sha) is None:
        raise ValueError("expected_sha must be a lowercase 40-character Git SHA")
    if public_build_sha(image_sha) != expected_sha:
        raise RuntimeError("Built image revision does not match expected Git SHA")
    return expected_sha
