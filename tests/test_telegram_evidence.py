"""A source capture timestamp must not masquerade as today's visit check."""

import inspect
from datetime import date

from app.handlers.main import place_card
from app.place_evidence import telegram_evidence_notice


def test_telegram_place_shows_operator_evidence_without_access_certification():
    result = telegram_evidence_notice(
        "perm", "perm-zoo", as_of=date(2026, 10, 11)
    )
    assert "Объект указан на сайте учреждения (2026-10-11)" in result
    assert "<a href=\"https://zoo.perm.ru/news/2026/09/30/2115\">" in result
    assert "не гарант" not in result
    assert "уточняйте" in result


def test_telegram_unknown_and_expired_evidence_are_explicit():
    missing = telegram_evidence_notice(
        "nalchik", "nalchik-osm-relation-9283129",
        as_of=date(2026, 10, 11),
    )
    assert "не подтверждены" in missing
    assert "перед поездкой" in missing
    assert "указан на сайте" not in missing
    stale = telegram_evidence_notice(
        "perm", "perm-zoo", as_of=date(2027, 2, 1)
    )
    assert "устарело" in stale
    assert "Фактическую доступность" in stale


def test_telegram_handler_labels_source_timestamp_as_capture_not_verification():
    body = inspect.getsource(place_card)
    assert "Дата записи источника:" in body
    assert "не дата проверки доступности" in body
    assert "telegram_evidence_notice(catalog.slug, place.slug)" in body
    assert 'f"Проверено:' not in body
