import os
from flask import Flask, render_template
from config import (
    SECRET_KEY,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    MAX_CONTENT_LENGTH,
)
import database

# ============================
# BLUEPRINTS IMPORT
# ============================
from routes.dashboard import dashboard_bp
from routes.comparison import comparison_bp
from routes.settings import settings_bp
from routes.auth import auth_bp
from routes.report import report_bp

# WET SEASON
from routes.wet_municipality import wet_municipality_bp
from routes.wet_association import wet_association_bp
from routes.wet_farmer import wet_farmer_bp

# DRY SEASON
from routes.dry_municipality import dry_municipality_bp
from routes.dry_association import dry_association_bp
from routes.dry_farmer import dry_farmer_bp


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = SESSION_COOKIE_SAMESITE
    app.config["SESSION_COOKIE_SECURE"] = SESSION_COOKIE_SECURE
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # ============================
    # INITIALIZE DATABASE HANDLER
    # ============================
    database.init_db(app)

    # ============================
    # REGISTER BLUEPRINTS
    # ============================
    app.register_blueprint(dashboard_bp, url_prefix="/")
    app.register_blueprint(comparison_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(report_bp)

    app.register_blueprint(wet_municipality_bp, url_prefix="/wet/municipality")
    app.register_blueprint(wet_association_bp, url_prefix="/wet/association")
    app.register_blueprint(wet_farmer_bp, url_prefix="/wet/farmer")

    app.register_blueprint(dry_municipality_bp, url_prefix="/dry/municipality")
    app.register_blueprint(dry_association_bp, url_prefix="/dry/association")
    app.register_blueprint(dry_farmer_bp, url_prefix="/dry/farmer")

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404


    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500



    return app

app = create_app()

# ============================
# PRINT ALL REGISTERED ROUTES
# ============================
if __name__ == "__main__":
    print("\n========== CIMS V12 REGISTERED ROUTES ==========")
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
        print(f"{rule.endpoint:35s} {methods:10s} {rule}")
    print("================================================\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )