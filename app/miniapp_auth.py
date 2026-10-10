"""Verify Telegram Mini App initData before accessing or mutating user data."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from urllib.parse import parse_qsl

MAX_INIT_DATA_BYTES = 8192
DEFAULT_MAX_AGE_SECONDS = 3600
FUTURE_CLOCK_SKEW_SECONDS = 30
_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class InvalidTelegramInitData(ValueError):
    """Missing, forged, malformed or expired Telegram Mini App credentials."""


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    now: int | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> int:
    """Return a verified Telegram user ID; never use initDataUnsafe as identity."""
    if (
        not isinstance(init_data, str)
        or not init_data
        or len(init_data.encode("utf-8")) > MAX_INIT_DATA_BYTES
        or not bot_token
        or max_age_seconds <= 0
    ):
        raise InvalidTelegramInitData("Invalid Mini App credentials")

    try:
        pairs = parse_qsl(
            init_data, keep_blank_values=True, strict_parsing=True,
            errors="strict", max_num_fields=50,
        )
        values = dict(pairs)
        if len(values) != len(pairs):
            raise ValueError("Duplicate initData fields")
        supplied_hash = values.pop("hash")
        if not _HASH_RE.fullmatch(supplied_hash):
            raise ValueError("Malformed hash")

        data_check = "\n".join(
            f"{key}={value}" for key, value in sorted(values.items())
        ).encode("utf-8")
        secret = hmac.new(
            b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
        ).digest()
        expected = hmac.new(secret, data_check, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied_hash.lower()):
            raise ValueError("Signature mismatch")

        raw_date = values["auth_date"]
        if not raw_date.isascii() or not raw_date.isdecimal():
            raise ValueError("Invalid authentication date")
        auth_date = int(raw_date)
        current = int(time.time()) if now is None else now
        if not (
            current - max_age_seconds <= auth_date <= current + FUTURE_CLOCK_SKEW_SECONDS
        ):
            raise ValueError("Expired or future-dated credentials")

        user = json.loads(values["user"])
        if not isinstance(user, dict):
            raise ValueError("Invalid user data")
        user_id = user.get("id")
        if (
            isinstance(user_id, bool)
            or not isinstance(user_id, int)
            or not 0 < user_id < 2**52
        ):
            raise ValueError("Invalid user ID")
        return user_id
    except (ValueError, KeyError, TypeError, UnicodeError, OverflowError) as exc:
        raise InvalidTelegramInitData("Invalid Mini App credentials") from exc
