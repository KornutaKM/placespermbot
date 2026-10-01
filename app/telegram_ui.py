TELEGRAM_MESSAGE_LIMIT = 4096
USER_TEXT_PREVIEW_LIMIT = 120


def user_text_preview(value: str, *, limit: int = USER_TEXT_PREVIEW_LIMIT) -> str:
    if limit <= 0:
        raise ValueError("preview limit must be positive")
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"
