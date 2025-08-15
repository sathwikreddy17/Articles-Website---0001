import os
from flask import Flask
from dotenv import load_dotenv
from .extensions import db, login_manager, migrate
from .models import User
from .helpers import highlight
from .config import DevelopmentConfig, TestingConfig, ProductionConfig


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

    # Config selection
    cfg_name = os.getenv("FLASK_CONFIG")
    if not cfg_name:
        cfg_name = (
            "ProductionConfig" if os.getenv("FLASK_ENV") == "production" else "DevelopmentConfig"
        )
    mapping = {
        "DevelopmentConfig": DevelopmentConfig,
        "TestingConfig": TestingConfig,
        "ProductionConfig": ProductionConfig,
    }
    app.config.from_object(mapping.get(cfg_name, DevelopmentConfig))

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    migrate.init_app(app, db)

    # Jinja filters
    app.jinja_env.filters["highlight"] = highlight

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

        app.logger.exception(f"500 Internal Server Error on {request.path}")
        return render_template("errors/500.html"), 500

    return app
