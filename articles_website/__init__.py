import os
import re
from unicodedata import normalize
from typing import Optional
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
    UserMixin,
)
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from dotenv import load_dotenv

# Load environment variables (support instance/.env for local dev)
load_dotenv()  # project root .env if present

# Global extensions (initialized without app; bound in create_app)
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


# ---------- Models ----------
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(255))
    slug = db.Column(db.String(255), unique=True, nullable=False)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- Forms ----------
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo


class ArticleForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    tags = StringField("Tags (comma-separated)")
    body = TextAreaField("Body", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")


# ---------- Helpers ----------
from functools import wraps


def slugify(text: str) -> str:
    text = normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text or "post"


def unique_slug(title: str, existing_id: Optional[int] = None) -> str:
    base = slugify(title)
    slug = base
    n = 2
    while True:
        q = Article.query.filter_by(slug=slug)
        if existing_id:
            q = q.filter(Article.id != existing_id)
        if q.first() is None:
            return slug
        slug = f"{base}-{n}"
        n += 1


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return wrapper


# ---------- Application Factory ----------
def create_app():
    # Resolve project root to locate templates/static and instance/.env reliably
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    # Also load instance/.env if present
    load_dotenv(os.path.join(project_root, "instance", ".env"))

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
    )

    # Configuration
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
    login_manager.login_view = "login"
    login_manager.login_message_category = "warning"
    migrate.init_app(app, db)

    # Routes (kept inline to avoid blueprint switch in Phase 1)
    @app.route("/")
    def home():
        latest = Article.query.order_by(Article.id.desc()).limit(5).all()
        return render_template("home.html", latest=latest)

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/articles")
    def articles():
        items = Article.query.order_by(Article.id.desc()).all()
        return render_template("articles.html", items=items)

    @app.route("/a/<slug>")
    def article_by_slug(slug):
        article = Article.query.filter_by(slug=slug).first_or_404()
        article.body_html = markdown.markdown(
            article.body, extensions=["fenced_code", CodeHiliteExtension(linenums=False)]
        )
        return render_template("article_detail.html", article=article)

    @app.route("/article/<int:article_id>")
    def article_detail(article_id):
        article = Article.query.get_or_404(article_id)
        return redirect(url_for("article_by_slug", slug=article.slug or article.id))

    @app.route("/create", methods=["GET", "POST"])
    @admin_required
    def create():
        form = ArticleForm()
        if form.validate_on_submit():
            article = Article(
                title=form.title.data.strip(),
                body=form.body.data.strip(),
                tags=form.tags.data.strip(),
            )
            article.slug = unique_slug(article.title)
            db.session.add(article)
            db.session.commit()
            flash("Article created!", "success")
            return redirect(url_for("article_by_slug", slug=article.slug))
        return render_template("create.html", form=form)

    @app.route("/edit/<int:article_id>", methods=["GET", "POST"])
    @admin_required
    def edit(article_id):
        article = Article.query.get_or_404(article_id)
        form = ArticleForm(obj=article)
        if form.validate_on_submit():
            new_title = form.title.data.strip()
            article.title = new_title
            article.tags = form.tags.data.strip()
            article.body = form.body.data.strip()
            article.slug = unique_slug(new_title, existing_id=article.id)
            db.session.commit()
            flash("Article updated!", "success")
            return redirect(url_for("article_by_slug", slug=article.slug))
        return render_template("edit.html", form=form, article=article)

    @app.route("/delete/<int:article_id>", methods=["POST"])
    @admin_required
    def delete(article_id):
        article = Article.query.get_or_404(article_id)
        db.session.delete(article)
        db.session.commit()
        flash("Deleted.", "info")
        return redirect(url_for("articles"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("articles"))
        form = RegisterForm()
        if form.validate_on_submit():
            if User.query.filter_by(email=form.email.data.lower()).first():
                flash("Email is already registered.", "danger")
                return redirect(url_for("register"))
            user = User(email=form.email.data.lower())
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome! Account created.", "success")
            return redirect(url_for("articles"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("articles"))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.lower()).first()
            if not user or not user.check_password(form.password.data):
                flash("Invalid email or password.", "danger")
                return redirect(url_for("login"))
            login_user(user, remember=form.remember.data)
            flash("Logged in.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("articles"))
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("home"))

    @app.route("/tags/<tag>")
    def by_tag(tag):
        items = Article.query.filter(Article.tags.ilike(f"%{tag}%")).order_by(Article.id.desc()).all()
        return render_template("articles.html", items=items, active_tag=tag)

    @app.route("/healthz")
    def healthz():
        return ("ok", 200)

    # One-time auto migration on boot (kept behaviorally identical)
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
