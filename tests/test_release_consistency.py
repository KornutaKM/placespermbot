from pathlib import Path

import pytest

from app.release_consistency import (
    assess_release_consistency,
    collect_release_consistency,
    main,
)


NAMES = ("Рязань", "Петрозаводск", "Пермь")


def _readme(names: tuple[str, ...] = NAMES, *, count: int = 3) -> str:
    cities = ", ".join(f"**{name}**" for name in names)
    return (
        f"Поддерживаются **{count} города**.\n"
        "## Города\n\nСейчас доступны:\n\n"
        f"- {cities}.\n\n## Конструктор маршрутов\n"
    )


def _assess(
    readme: str | None = None,
    *,
    guide: str = "--max-age-hours 24 --min-cities 3",
    manifest_city_names: tuple[str, ...] = NAMES,
    registered_cities: int = 3,
    production_minimum_cities: int = 3,
):
    return assess_release_consistency(
        _readme() if readme is None else readme,
        deployment_guide=guide,
        registered_cities=registered_cities,
        manifest_city_names=manifest_city_names,
        production_minimum_cities=production_minimum_cities,
    )


def test_current_release_metadata_consistent() -> None:
    root = Path(__file__).resolve().parents[1]
    report = collect_release_consistency(
        root / "README.md", root / "docs/production-deployment.md"
    )
    assert report.status == "ready"
    assert report.registered_cities == 34
    assert report.documented_cities == 34
    assert len(report.documented_city_names or ()) == 34
    assert "Рязань" in (report.documented_city_names or ())
    assert "Петрозаводск" in (report.documented_city_names or ())
    assert report.production_minimum_cities == 34
    assert report.deployment_guide_minimum_cities == 34
    assert report.issues == ()


def test_stale_readme_and_release_minimum_fail_explicitly() -> None:
    report = _assess(
        _readme(count=2),
        registered_cities=3,
        production_minimum_cities=2,
    )
    assert report.status == "inconsistent"
    assert set(report.issues) == {
        "readme_city_count_mismatch",
        "production_minimum_city_count_mismatch",
        "deployment_guide_city_count_mismatch",
    }


def test_missing_or_duplicate_count_fails_closed() -> None:
    readme = _readme()
    for text in (readme.replace("Поддерживаются **3 города**.", ""), readme + readme):
        report = _assess(text, manifest_city_names=NAMES[:-1])
        assert "readme_city_count_missing_or_ambiguous" in report.issues
        assert "manifest_city_count_mismatch" in report.issues


def test_city_list_must_match_manifest_even_when_count_matches() -> None:
    for names in (NAMES[:-1], ("Рязань", "Петрозаводск", "Калуга")):
        report = _assess(_readme(names))
        assert "readme_city_list_mismatch" in report.issues
        assert "readme_city_count_mismatch" not in report.issues


def test_city_list_rejects_duplicates() -> None:
    report = _assess(_readme(("Рязань", "Рязань", "Пермь")))
    assert "readme_city_list_duplicate" in report.issues
    assert "readme_city_list_mismatch" in report.issues


def test_city_list_rejects_missing_section_and_label() -> None:
    for text in (_readme().replace("## Города", "## Каталоги"), _readme().replace("Сейчас доступны:", "")):
        assert "readme_city_list_missing_or_ambiguous" in _assess(text).issues


def test_deployment_guide_minimum_is_checked_independently() -> None:
    for text in ("--min-cities 2", "", "--min-cities 3\n--min-cities 3"):
        report = _assess(guide=text)
        assert report.status == "inconsistent"
        if text == "--min-cities 2":
            assert "deployment_guide_city_count_mismatch" in report.issues
        else:
            assert "deployment_guide_city_count_missing_or_ambiguous" in report.issues


def test_release_consistency_cli_exit_code(tmp_path, capsys) -> None:
    root = Path(__file__).resolve().parents[1]
    path = tmp_path / "README.md"
    guide = tmp_path / "production-deployment.md"
    path.write_text((root / "README.md").read_text(encoding="utf-8"), encoding="utf-8")
    guide.write_text(
        (root / "docs/production-deployment.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    args = ["--readme", str(path), "--deployment-guide", str(guide), "--check"]
    main(args)
    assert '"status": "ready"' in capsys.readouterr().out
    path.write_text(
        path.read_text(encoding="utf-8").replace("**Рязань**", "**Калуга**"),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 1
