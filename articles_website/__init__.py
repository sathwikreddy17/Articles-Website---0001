import os
from flask import Flask
from dotenv import load_dotenv
from .extensions import db, login_manager, migrate
from .models import User
from flask_login import current_user


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    load_dotenv()
    load_dotenv(os.path.join(project_root, "instance", ".env"))

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
    )

    # Config
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-later")
    uri = os.getenv("DATABASE_URL", "sqlite:///site.db")
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql+psycopg://", 1)
    elif uri.startswith("postgresql://"):
        uri = uri.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if os.getenv("FLASK_ENV") == "production":
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
        )

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    migrate.init_app(app, db)

    # Register blueprints (no prefixes to preserve URLs)
    from .blueprints.main import bp as main_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.admin import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # Error handlers
    @app.errorhandler(404)
    def handle_404(e):
        from flask import request, render_template
        app.logger.info(f"404 Not Found: {request.path}")
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_500(e):
        from flask import request, render_template
        # Logs full stack trace
        app.logger.exception(f"500 Internal Server Error on {request.path}")
        return render_template("errors/500.html"), 500

    # AUTO_MIGRATE block unchanged
    if os.getenv("AUTO_MIGRATE", "0") == "1":
        try:
            print("🛠 AUTO_MIGRATE=1 -> running Alembic upgrade() ...")
            from flask_migrate import upgrade as _upgrade
            with app.app_context():
                _upgrade()
                print("✅ Auto-migration complete.")
        except Exception as e:
            try:
                print(f"⚠️ Auto-migration failed: {e}. Falling back to db.create_all() ...")
                with app.app_context():
                    db.create_all()
                    print("✅ create_all() complete.")
            except Exception as e2:
                print(f"❌ create_all() also failed: {e2}")

    return app
