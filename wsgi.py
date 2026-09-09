"""WSGI-точка входа для запуска API: ``python wsgi.py`` или через ``start.bat``."""

from __future__ import annotations

from api import create_app
from api.config import APIConfig


def main() -> None:
    cfg = APIConfig.from_env()
    app = create_app(cfg)
    app.run(host=cfg.host, port=cfg.port, debug=cfg.debug, use_reloader=False)


if __name__ == "__main__":
    main()