"""Docker healthcheck for the separately running Mini App HTTP service."""

import json
from urllib.request import urlopen


def main() -> None:
    with urlopen("http://127.0.0.1:8080/healthz", timeout=3) as response:
        result = json.load(response)
    if result.get("status") != "ok":
        raise RuntimeError("Mini App health check failed")


if __name__ == "__main__":
    main()
