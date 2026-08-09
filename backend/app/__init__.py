from flask import Flask
from flask_cors import CORS
from .db import exdb

from .routes import main_bp, activities_bp, hrm_bp, sync_bp
from .hrmbak import hrm_bpbak
from .routes.preferences import preferences_bp
from .routes.performance import performance_bp
from .routes.health import health_records_bp
from .routes.auth import auth_bp



def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    # Ensure sessions use configured secret and allow credentialed CORS
    app.secret_key = app.config.get('SECRET_KEY')
    CORS(app, supports_credentials=True)
    exdb.init_app(app)

    # # Ensure garmin_accounts table exists on startup (best-effort).
    # try:
    #     from .routes.sync import _ensure_garmin_accounts_table

    #     # Run the table-ensure function; ignore failures so startup isn't blocked
    #     # in environments where the DB isn't reachable during quick dev checks.
    #     try:
    #         _ensure_garmin_accounts_table()
    #     except Exception:
    #         pass
    # except Exception:
    #     # If the sync module or function isn't importable, skip silently.
    #     pass

    app.register_blueprint(main_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(hrm_bp)
    app.register_blueprint(hrm_bpbak)
    app.register_blueprint(sync_bp)
    app.register_blueprint(preferences_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(health_records_bp)
    app.register_blueprint(auth_bp)
    return app
