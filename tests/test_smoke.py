import asyncio

import pytest

from app.config import Settings
from app.smoke import main, validate_packaged_storage


def test_packaged_smoke_runs_real_sqlite_backup_and_restore() -> None:
    asyncio.run(
        validate_packaged_storage(
            Settings(
                bot_token="123456789:smoke-test",
                environment="ci",
                city_slug="saint-petersburg",
                database_path="/nonexistent/should-not-touch.db",
            ),
        )
    )


def test_packaged_smoke_entrypoint_checks_configuration(monkeypatch, capsys) -> None:
    settings = Settings(
        bot_token="123456789:smoke-test",
        environment="ci",
        city_slug="saint-petersburg",
        database_path="/nonexistent/should-not-touch.db",
    )
    monkeypatch.setattr("app.smoke.get_settings", lambda: settings)
    main()
    assert capsys.readouterr().out.strip() == "smoke: ok"


def test_packaged_smoke_rejects_missing_token(monkeypatch) -> None:
    settings = Settings(bot_token="", environment="ci")
    monkeypatch.setattr("app.smoke.get_settings", lambda: settings)
    with pytest.raises(RuntimeError, match="PLACES_BOT_TOKEN"):
        main()
