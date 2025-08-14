from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Create extension instances here to avoid circular imports

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
