from app.config import get_settings
from app.runtime_checks import validate_static_runtime


def main() -> None:
    validate_static_runtime(get_settings())
    print("smoke: ok")


if __name__ == "__main__":
    main()
