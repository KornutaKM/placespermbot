import asyncio
import sys

from app.config import get_settings
from app.runtime_checks import validate_health


async def check() -> int:
    try:
        await validate_health(get_settings())
    except Exception as exc:
        print(f"unhealthy: {exc}", file=sys.stderr)
        return 1

    print("healthy")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(check()))


if __name__ == "__main__":
    main()
