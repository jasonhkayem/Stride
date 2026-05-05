import os
from importlib import import_module
from pathlib import Path

from flask import Blueprint, Flask, jsonify, send_from_directory


def _load_env_file() -> None:
    """Load .env if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # Keep startup resilient if dotenv is not installed.
        pass


def _iter_route_modules():
    training_dir = Path(__file__).resolve().parent / "training"
    for entry in sorted(training_dir.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / "routes.py").exists():
            yield f"training.{entry.name}.routes"


def create_app() -> Flask:
    _load_env_file()
    app = Flask(__name__)

    registered_prefixes = []

    for module_name in _iter_route_modules():
        module = import_module(module_name)
        for value in vars(module).values():
            if isinstance(value, Blueprint):
                app.register_blueprint(value)
                registered_prefixes.append(value.url_prefix or "")

    # Create any new tables that don't yet exist. Import engine here (after
    # _load_env_file) so DATABASE_URL is already set from .env.
    from training.db import engine
    from training.club_memberships.models import ClubKickLog
    ClubKickLog.__table__.create(engine, checkfirst=True)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Admin-User-Id"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    images_dir = Path(__file__).resolve().parent / "images"

    @app.get("/images/<path:filename>")
    def serve_image(filename):
        return send_from_directory(images_dir, filename)

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "blueprints_registered": len(registered_prefixes),
            }
        )

    @app.get("/")
    def index():
        return jsonify(
            {
                "name": "Final Year Project API",
                "status": "running",
                "health": "/health",
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
