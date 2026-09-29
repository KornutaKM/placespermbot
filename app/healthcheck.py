import asyncio

from app.config import get_settings
from app.runtime_checks import validate_health


async def check() -> None:
    await validate_health(get_settings())


def main() -> None:
    asyncio.run(check())
    print("healthy")


if __name__ == "__main__":
    main()
