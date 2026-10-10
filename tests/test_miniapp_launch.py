import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.handlers.main import miniapp_command
from app.keyboards import home_keyboard
from app.miniapp_launch import miniapp_launch_url


class FakeMessage:
    def __init__(self):
        self.answers = []

    async def answer(self, text, *, reply_markup=None):
        self.answers.append((text, reply_markup))


@pytest.mark.parametrize(
    "url",
    (
        "http://example.com/app", "https://", "javascript:alert(1)",
        "https://user:secret@example.org/app", "https://example.org/#frag",
    ),
)
def test_unsafe_launch_urls_are_rejected(url):
    with pytest.raises(ValueError, match="HTTPS"):
        miniapp_launch_url(url)


def test_launch_url_accepts_https_and_unset_configuration():
    assert miniapp_launch_url("  ") is None
    assert miniapp_launch_url("https://guide.example.com/") == (
        "https://guide.example.com/"
    )


def test_app_command_fail_closed_until_https_host_is_configured():
    async def scenario():
        without_url = FakeMessage()
        with patch(
            "app.handlers.main.get_settings",
            return_value=SimpleNamespace(mini_app_url=""),
        ):
            await miniapp_command(without_url)
        assert "пока не опубликовано" in without_url.answers[0][0]
        assert without_url.answers[0][1] is None

        with_url = FakeMessage()
        with patch(
            "app.handlers.main.get_settings",
            return_value=SimpleNamespace(
                mini_app_url="https://guide.example.com/"
            ),
        ):
            await miniapp_command(with_url)
        markup = with_url.answers[0][1]
        assert markup.inline_keyboard[0][0].web_app.url == (
            "https://guide.example.com/"
        )

    asyncio.run(scenario())


def test_home_button_only_exists_when_url_is_configured():
    with patch(
        "app.keyboards.get_settings",
        return_value=SimpleNamespace(mini_app_url=""),
    ):
        assert all(
            button.web_app is None
            for row in home_keyboard().inline_keyboard
            for button in row
        )
    with patch(
        "app.keyboards.get_settings",
        return_value=SimpleNamespace(mini_app_url="https://guide.example.com/"),
    ):
        markup = home_keyboard()
        assert markup.inline_keyboard[0][0].web_app.url == (
            "https://guide.example.com/"
        )
