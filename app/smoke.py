from app import main as main_module
from app.config import get_settings
from app.runtime_checks import validate_static_runtime


def main() -> None:
    validate_static_runtime(get_settings())
    if not callable(main_module.main):
        raise TypeError("app.main entrypoint is unavailable")
    print("smoke: ok")


if __name__ == "__main__":
    main()
