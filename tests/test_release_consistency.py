from pathlib import Path

from app.release_consistency import (
    assess_release_consistency,
    collect_release_consistency,
    main,
)


def test_current_release_metadata_consistent() -> None:
    root = Path(__file__).resolve().parents[1]
    report = collect_release_consistency(root / "README.md")
    assert report.status == "ready"
    assert report.registered_cities == 34
    assert report.documented_cities == 34
    assert report.production_minimum_cities == 34
    assert report.issues == ()


def test_stale_readme_and_release_minimum_fail_explicitly() -> None:
    report = assess_release_consistency(
        "Поддерживаются **32 города**.",
        registered_cities=34,
        manifest_cities=34,
        production_minimum_cities=33,
    )
    assert report.status == "inconsistent"
    assert set(report.issues) == {
        "readme_city_count_mismatch",
        "production_minimum_city_count_mismatch",
    }


def test_missing_or_duplicate_documentation_fails_closed() -> None:
    readme = "Поддерживаются **34 города**."
    for text in ("no count", readme + "\n" + readme):
        report = assess_release_consistency(
            text,
            registered_cities=34,
            manifest_cities=33,
            production_minimum_cities=34,
        )
        assert "readme_city_count_missing_or_ambiguous" in report.issues
        assert "manifest_city_count_mismatch" in report.issues


def test_release_consistency_cli_exit_code(tmp_path, capsys) -> None:
    path = tmp_path / "README.md"
    path.write_text("Поддерживаются **34 города**.", encoding="utf-8")
    main(["--readme", str(path), "--check"])
    assert '"status": "ready"' in capsys.readouterr().out
    path.write_text("Поддерживаются **33 города**.", encoding="utf-8")
    import pytest
    with pytest.raises(SystemExit) as error:
        main(["--readme", str(path), "--check"])
    assert error.value.code == 1
