import asyncio
from unittest.mock import patch

import pytest

from app.config import Settings
from app.database import LATEST_SCHEMA_VERSION, migrate_database
from app.diagnostics import collect_diagnostics


def test_diagnostics_reports_operational_state_without_secrets(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "places.db"
        await migrate_database(database_path)
        settings = Settings(
            bot_token="123456789:secret-token",
            environment="test",
            city_slug="saint-petersburg",
            database_path=str(database_path),
        )

        result = await collect_diagnostics(settings)

        assert result["status"] == "healthy"
        assert result["environment"] == "test"
        assert result["build_sha"] == "unverified"
        assert result["city_slug"] == "saint-petersburg"
        assert result["database"]["size_bytes"] > 0
        assert result["database"]["journal_mode"] == "wal"
        assert result["database"]["integrity"] == "ok"
        assert result["database"]["latest_migration"] == LATEST_SCHEMA_VERSION
        assert result["database"]["migration_versions"] == list(
            range(1, LATEST_SCHEMA_VERSION + 1)
        )

        rendered = repr(result)
        assert "secret-token" not in rendered
        assert str(database_path) not in rendered

    asyncio.run(scenario())

def test_diagnostics_rejects_failed_quick_integrity_gate(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "places.db"
        await migrate_database(database_path)
        settings = Settings(
            bot_token="123456789:secret-token",
            environment="test",
            city_slug="saint-petersburg",
            database_path=str(database_path),
        )

        with (
            patch(
                "app.diagnostics.validate_integrity_result",
                side_effect=RuntimeError("Database database failed quick integrity check"),
            ) as validate_integrity,
            pytest.raises(RuntimeError, match="failed quick integrity check"),
        ):
            await collect_diagnostics(settings)

        validate_integrity.assert_called_once()
        assert validate_integrity.call_args.kwargs == {
            "subject": "Database",
            "mode": "quick",
        }

    asyncio.run(scenario())



def test_diagnostics_reports_valid_build_sha_but_redacts_other_env_text(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "places.db"
        await migrate_database(database_path)
        known = Settings(
            bot_token="123456789:secret", database_path=str(database_path),
            build_sha="f" * 40,
        )
        assert (await collect_diagnostics(known))["build_sha"] == "f" * 40
        bad = Settings(
            bot_token="123456789:secret", database_path=str(database_path),
            build_sha="do-not-publish-secret",
        )
        report = await collect_diagnostics(bad)
        assert report["build_sha"] == "unverified"
        assert "do-not-publish" not in repr(report)

    asyncio.run(scenario())
