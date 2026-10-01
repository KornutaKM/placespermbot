from unittest.mock import MagicMock

import pytest

from app.database_contract import validate_database_integrity, validate_integrity_result


@pytest.mark.parametrize(
    ("mode", "pragma"),
    (
        ("quick", "quick_check"),
        ("full", "integrity_check"),
    ),
)
def test_database_integrity_uses_requested_sqlite_check(mode, pragma) -> None:
    database = MagicMock()
    database.execute.return_value.fetchone.return_value = ("ok",)

    validate_database_integrity(
        database,
        subject="Database",
        mode=mode,
    )

    database.execute.assert_called_once_with(f"PRAGMA {pragma}")


def test_integrity_result_rejects_failed_quick_check() -> None:
    with pytest.raises(RuntimeError, match="failed quick integrity check"):
        validate_integrity_result(
            ("database disk image is malformed",),
            subject="Database",
            mode="quick",
        )
