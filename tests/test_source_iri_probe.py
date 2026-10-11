"""RFC 3987-style IRI source URLs must be probed without false failures."""

from urllib.parse import unquote, urlsplit

import pytest

from app.place_source_probe import http_request, http_transport_url, probe_page


def test_percent_encodes_cyrillic_source_path_without_double_encoding():
    original = "https://derbenttourism.ru/достопримечательности/"
    encoded = http_transport_url(original)
    assert encoded.startswith("https://derbenttourism.ru/%D0%B4")
    assert unquote(urlsplit(encoded).path) == "/достопримечательности/"
    assert http_transport_url(encoded) == encoded
    assert http_transport_url(original + "?q=музей&sort=asc#top") == (
        encoded + "?q=%D0%BC%D1%83%D0%B7%D0%B5%D0%B9&sort=asc"
    )


def test_public_https_probe_rejects_unsafe_schemes_and_credentials():
    for candidate in (
        "http://example.com/",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https://user:password@example.com/",
    ):
        with pytest.raises(ValueError, match="public HTTPS"):
            http_transport_url(candidate)


def test_urllib_receives_normalized_url_but_catalog_evidence_keeps_iri(monkeypatch):
    from app import place_source_probe

    seen = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _size=0):
            return b"valid"

        def geturl(self):
            return seen[-1].full_url

    def fake_urlopen(request, *, timeout):
        seen.append(request)
        assert timeout == 1
        return Response()

    monkeypatch.setattr(place_source_probe, "urlopen", fake_urlopen)
    iri = "https://derbenttourism.ru/достопримечательности/"
    status, final_url, body = http_request(iri, timeout=1)
    assert status == 200
    assert body == b"valid"
    assert "%D0" in final_url
    assert seen[0].full_url == http_transport_url(iri)
    report = probe_page(iri, timeout=1)
    assert report["signal"] == "source_reachable_not_venue_verified"
    assert report["redirected_to"] is None
    assert seen[1].get_method() == "HEAD"
