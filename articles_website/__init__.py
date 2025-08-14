import os
from flask import Flask, render_template, redirect, url_for, request, flash
from dotenv import load_dotenv
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from flask_login import current_user, login_user, logout_user, login_required
from .extensions import db, login_manager, migrate
from .forms import ArticleForm, RegisterForm, LoginForm
from .helpers import admin_required, unique_slug
from .models import Article, User


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
    login_manager.login_view = "login"
    login_manager.login_message_category = "warning"
    migrate.init_app(app, db)

    # Routes
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
        return redirect(url_for("article_by_slug", slug=Article.query.get_or_404(article_id).slug))

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
