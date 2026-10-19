"""API de competições de robótica (Flask + MongoDB)."""

import os

from flask import Flask
from flask_cors import CORS

from robotica import db
from robotica.errors import register_error_handlers
from robotica.json_provider import MongoJSONProvider
from robotica.routes import events, ranking, robots
from robotica.seed import register_seed_command


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.json = MongoJSONProvider(app)
    app.config.update(
        MONGO_URI=os.environ.get("MONGO_URI", "mongodb://localhost:27017/robotica"),
    )
    if config:
        app.config.update(config)

    # A API é pública e só de leitura para o painel web; liberar CORS em /api
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    register_error_handlers(app)
    register_seed_command(app)

    app.register_blueprint(robots.bp)
    app.register_blueprint(events.bp)
    app.register_blueprint(ranking.bp)

    @app.get("/health")
    def health():
        db.get_db().command("ping")
        return {"status": "healthy"}

    return app
