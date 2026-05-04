"""CodeLens AI — Flask entrypoint."""
import logging
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from routes.analyze import analyze_bp
from routes.health import health_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        resources={r"/*": {"origins": Config.CORS_ORIGINS}},
        supports_credentials=False,
    )

    app.register_blueprint(health_bp)
    app.register_blueprint(analyze_bp, url_prefix="/api")

    @app.errorhandler(404)
    def _404(_):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(500)
    def _500(_):
        return jsonify({"error": "internal_error"}), 500

    return app


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
