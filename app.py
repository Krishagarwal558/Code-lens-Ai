from flask import Flask, jsonify, render_template
from flask_cors import CORS

from config import Config
from routes.analyze import analyze_bp
from routes.health import health_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    # API routes
    app.register_blueprint(health_bp)
    app.register_blueprint(analyze_bp, url_prefix="/api")

    # ✅ Home route
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "not_found"}), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=True)