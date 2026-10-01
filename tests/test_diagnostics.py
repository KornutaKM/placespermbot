import asyncio

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
