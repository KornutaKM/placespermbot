import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.miniapp_auth import InvalidTelegramInitData, validate_init_data

TOKEN = "123456789:miniapp-test-secret"
NOW = 1_760_000_000


def signed_data(*, user_id: int = 42, at: int = NOW, extra=None) -> str:
    values = {
        "auth_date": str(at),
        "query_id": "sample-web-app-query",
        "user": json.dumps({"id": user_id, "first_name": "Тест"}, ensure_ascii=False),
        **(extra or {}),
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode({**values, "hash": digest})


def test_telegram_init_data_hmac_verifies_expected_user():
    assert validate_init_data(signed_data(), TOKEN, now=NOW) == 42
    assert validate_init_data(
        signed_data(extra={"start_param": "places", "signature": "not-validated-separately"}),
        TOKEN, now=NOW
    ) == 42


@pytest.mark.parametrize(
    "corrupt",
    [
        "", "auth_date=bad", "auth_date=1&user=foo&hash=no",
        "user=%7B%7D&auth_date=1&hash=" + "x" * 64,
        "auth_date=1&auth_date=1&user=foo&hash=" + "0" * 64,
    ],
)
def test_missing_or_malformed_init_data_is_rejected(corrupt):
    with pytest.raises(InvalidTelegramInitData):
        validate_init_data(corrupt, TOKEN, now=NOW)


def test_invalid_signature_wrong_secret_and_replayed_credentials_are_rejected():
    valid = signed_data()
    for payload, token, now in (
        (valid.replace("query_id=sample", "query_id=forged"), TOKEN, NOW),
        (valid, "wrong-secret", NOW),
        (valid, TOKEN, NOW + 3601),
        (signed_data(at=NOW + 31), TOKEN, NOW),
        (signed_data(at=NOW - 3601), TOKEN, NOW),
        (valid + "&auth_date=100", TOKEN, NOW),
    ):
        with pytest.raises(InvalidTelegramInitData):
            validate_init_data(payload, token, now=now)


@pytest.mark.parametrize("user", [{}, {"id": True}, {"id": -1}, {"id": "42"}])
def test_invalid_user_identity_is_rejected(user):
    with pytest.raises(InvalidTelegramInitData):
        validate_init_data(
            signed_data(extra={"user": json.dumps(user)}), TOKEN, now=NOW
        )


def test_bot_token_is_never_part_of_error_message():
    with pytest.raises(InvalidTelegramInitData) as exc:
        validate_init_data("bad", TOKEN, now=NOW)
    assert TOKEN not in str(exc.value)
