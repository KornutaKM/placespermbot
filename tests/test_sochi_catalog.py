from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_sochi_city_museums_and_geography() -> None:
    city = get_catalog("sochi")
    assert len(city.places) >= 34
    assert len(city.routes) >= 12
    assert len({p.category for p in city.places}) == 5
    assert len({p.district for p in city.places}) >= 10
    assert sum(p.category == "museums" for p in city.places) >= 9
    for slug, host in {
        "soc-city-history-museum": "sochimuseum-history.ru",
        "soc-adler-local-museum": "museumadler.ru",
        "soc-lazarev-ethnomuseum": "sochimuseum-history.ru",
        "soc-ostrovsky-house": "www.muzei-ostrovskogo.ru",
        "soc-riviera-attractions": "rivierasochi.ru",
    }.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == host


def test_sochi_routed_districts_and_ticket_boundary() -> None:
    city = get_catalog("sochi")
    routes = {r.slug: r for r in city.routes}
    assert "soc-adler-local-museum" in routes["soc-adler-history"].place_slugs
    assert "soc-lazarev-ethnomuseum" in routes["soc-lazarevskoye"].place_slugs
    assert "soc-ostrovsky-house" in routes["soc-literary-musical"].place_slugs
    assert "soc-sports-glory-museum" in routes["soc-city-museums"].place_slugs
    assert all(len(r.place_slugs) >= 2 for r in city.routes)
    family = {p.slug for p in city.places_for_category("family")}
    free = {p.slug for p in city.places_for_category("free")}
    assert "soc-riviera-attractions" in family
    assert "soc-riviera-attractions" not in free
    assert "soc-riviera-dolphinarium" not in free
    assert "soc-navaginskaya-street" in free
    assert city.search_places("Музей спортивной славы")[0].slug == "soc-sports-glory-museum"


def test_sochi_museum_remote_routes_and_no_sirius_conflation() -> None:
    city = get_catalog("sochi")
    assert "Отдельный район" in routes_summary(city, "soc-lazarevskoye")
    assert "Сириус" not in " ".join(p.title for p in city.places)
    museums = [p for p in city.places if p.category == "museums"]
    assert all(not p.is_free for p in museums)


def routes_summary(city, slug: str) -> str:
    route = city.route_by_slug(slug)
    assert route is not None
    return route.summary


def test_sochi_port_and_theatre_have_venue_sources_without_false_access_claims() -> None:
    from app.place_evidence import public_evidence

    city = get_catalog("sochi")
    expected = {
        "winter-theatre-sochi": (
            "https://www.skfo.online/contacts/", "www.skfo.online"
        ),
        "marine-station-sochi": (
            "https://www.morport-sochi.ru/contacts/", "www.morport-sochi.ru"
        ),
    }
    for slug, (url, host) in expected.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.url == url
        assert urlparse(url).hostname == host
        assert place.source.checked_at == date(2026, 10, 11)
        evidence = public_evidence("sochi", slug, as_of=date(2026, 10, 11))
        assert evidence["status"] == "operator_listed"
        assert evidence["evidence_url"] == url
        assert "доступ" in evidence["finding"].lower() or (
            "билеты" in evidence["finding"].lower()
        )

    assert "служебные зоны" in city.place_by_slug(
        "marine-station-sochi"
    ).summary
    assert "билетов" in city.place_by_slug("winter-theatre-sochi").summary
    assert any(
        "winter-theatre-sochi" in r.place_slugs for r in city.routes
    )
    assert any(
        "marine-station-sochi" in r.place_slugs for r in city.routes
    )
