"""Guard Telegram Mini App launch URLs (Telegram requires HTTPS)."""

from urllib.parse import urlsplit


def miniapp_launch_url(configured_url: str) -> str | None:
    url = configured_url.strip()
    if not url:
        return None
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
    ):
        raise ValueError("PLACES_MINI_APP_URL must be a public HTTPS URL")
    return url
