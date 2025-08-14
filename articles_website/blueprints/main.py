from flask import Blueprint, render_template
from ..models import Article
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    latest = Article.query.order_by(Article.id.desc()).limit(5).all()
    return render_template("home.html", latest=latest)


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/articles")
def articles():
    items = Article.query.order_by(Article.id.desc()).all()
    return render_template("articles.html", items=items)


@bp.route("/a/<slug>")
def article_by_slug(slug):
    article = Article.query.filter_by(slug=slug).first_or_404()
    article.body_html = markdown.markdown(
        article.body, extensions=["fenced_code", CodeHiliteExtension(linenums=False)]
    )
    return render_template("article_detail.html", article=article)


@bp.route("/article/<int:article_id>")
def article_detail(article_id):
    article = Article.query.get_or_404(article_id)
    # keep redirect to slug URL behavior identical
    from flask import redirect, url_for

    return redirect(url_for("main.article_by_slug", slug=article.slug or article.id))


@bp.route("/tags/<tag>")
def by_tag(tag):
    items = Article.query.filter(Article.tags.ilike(f"%{tag}%")).order_by(Article.id.desc()).all()
    return render_template("articles.html", items=items, active_tag=tag)


@bp.route("/healthz")
def healthz():
    return ("ok", 200)
