"""MVP-136: misleading HTTP redirects must enter review, not mark POIs current."""

from copy import deepcopy

import pytest

from app.place_review_queue import build_review_queue, render_markdown
from app.place_source_probe import (
    probe_page,
    redirect_review_signal,
    run_audit,
)


@pytest.mark.parametrize(
    ("original", "final", "expected"),
    [
        (
            "https://www.volgadmin.ru/d/about/Tourism",
            "http://www.volgadmin.ru/d/units/Error?aspxerrorpath=/d/about/Tourism",
            "source_insecure_redirect_review_required",
        ),
        (
            "https://museum.example/articles/ticket",
            "https://museum.example/d/units/Error?aspxerrorpath=/articles/ticket",
            "source_error_page_review_required",
        ),
        (
            "https://www.volkovteatr.ru/theatre/basic-information/",
            "https://volkovteatr.ru/",
            "source_generic_home_redirect_review_required",
        ),
        (
            "https://samara.travel/products/dostoprimechatelnosti/",
            "https://xn--80aaafzfb7a0bgk.xn--p1ai/products/dostoprimechatelnosti/",
            "source_cross_host_redirect_review_required",
        ),
        (
            "https://museum.example/",
            "https://www.museum.example/ru/",
            None,
        ),
        (
            "https://museum.example/exhibitions",
            "https://www.museum.example/ru/exhibitions",
            None,
        ),
        (
            "https://www.museum.example/page/",
            "https://museum.example/page/",
            None,
        ),
    ],
)
def test_redirect_classification_is_not_closure_proof(
    original: str, final: str, expected: str | None,
):
    assert redirect_review_signal(original, final) == expected


def test_successful_http_200_with_insecure_redirect_is_not_reachable_signal(monkeypatch):
    from app import place_source_probe

    def http(url: str, *, timeout: float, method: str = "GET"):
        assert method == "HEAD"
        return 200, "http://example.org/redirected", b""

    monkeypatch.setattr(place_source_probe, "http_request", http)
    result = probe_page("https://example.org/details")
    assert result["signal"] == "source_insecure_redirect_review_required"
    assert result["http_status"] == 200
    assert result["redirected_to"].startswith("http://")


def test_valid_same_host_redirect_remains_source_reachable_not_venue_verified(
    monkeypatch,
):
    from app import place_source_probe

    def http(url: str, *, timeout: float, method: str = "GET"):
        return 200, "https://example.org/ru/details", b""

    monkeypatch.setattr(place_source_probe, "http_request", http)
    result = probe_page("https://www.example.org/details")
    assert result["signal"] == "source_reachable_not_venue_verified"
    assert result["redirected_to"] == "https://example.org/ru/details"


def test_review_queue_prioritizes_redirect_and_retains_route_impact():
    report = run_audit(live=False)
    changed = next(
        row for row in report["places"]
        if row["city_slug"] == "volgograd"
        and row["place_slug"] == "pavlov-house"
    )
    original = deepcopy(report)
    changed["probe"] = {
        "signal": "source_error_page_review_required",
        "http_status": 200,
        "redirected_to": "https://monument.volgadmin.ru/error",
    }
    queue = build_review_queue(report, previous=original)
    row = next(
        item for item in queue["queue"]
        if item["city_slug"] == "volgograd"
        and item["place_slug"] == "pavlov-house"
    )
    assert row["priority"] == "P1_source_identity_review"
    assert row["new_or_changed"] is True
    assert queue["source_identity_review_count"] == 1
    assert queue["redirect_review_count"] == 1
    city = next(
        item for item in queue["city_summary"]
        if item["slug"] == "volgograd"
    )
    assert city["source_redirect"] == 1
    assert city["source_missing"] == 0
    assert row["route_count"] >= 0
    assert "Redirect" in render_markdown(queue)
