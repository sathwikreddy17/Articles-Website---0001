from flask import Blueprint, render_template, request, current_app
from ..models import Article
from sqlalchemy import or_
from ..helpers import render_markdown_safe

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
    # Pagination
    page = request.args.get("page", default=1, type=int)
    per_page_default = current_app.config.get("ARTICLES_PER_PAGE", 10)
    per_page = request.args.get("per_page", default=per_page_default, type=int)

    query = Article.query.order_by(Article.id.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    has_prev = page > 1
    has_next = page * per_page < total

    return render_template(
        "articles.html",
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        has_prev=has_prev,
        has_next=has_next,
    )


@bp.route("/a/<slug>")
def article_by_slug(slug):
    article = Article.query.filter_by(slug=slug).first_or_404()
    article.body_html = render_markdown_safe(article.body)
    return render_template("article_detail.html", article=article)


@bp.route("/article/<int:article_id>")
def article_detail(article_id):
    article = Article.query.get_or_404(article_id)
    # keep redirect to slug URL behavior identical
    from flask import redirect, url_for

    return redirect(url_for("main.article_by_slug", slug=article.slug or article.id))


@bp.route("/tags/<tag>")
def by_tag(tag):
    # Add pagination for tag-filtered listing
    page = request.args.get("page", default=1, type=int)
    per_page_default = current_app.config.get("ARTICLES_PER_PAGE", 10)
    per_page = request.args.get("per_page", default=per_page_default, type=int)

    query = Article.query.filter(Article.tags.ilike(f"%{tag}%")).order_by(Article.id.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    has_prev = page > 1
    has_next = page * per_page < total

    return render_template(
        "articles.html",
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        has_prev=has_prev,
        has_next=has_next,
        active_tag=tag,
    )


@bp.route("/search")
def search():
    # Simple title/body search with pagination
    q = (request.args.get("q", "") or "").strip()
    if not q:
        from flask import redirect, url_for

        return redirect(url_for("main.articles"))

    page = request.args.get("page", default=1, type=int)
    per_page_default = current_app.config.get("ARTICLES_PER_PAGE", 10)
    per_page = request.args.get("per_page", default=per_page_default, type=int)

    query = Article.query.filter(
        or_(
            Article.title.ilike(f"%{q}%"),
            Article.body.ilike(f"%{q}%"),
        )
    ).order_by(Article.id.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    has_prev = page > 1
    has_next = page * per_page < total

    return render_template(
        "articles.html",
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        has_prev=has_prev,
        has_next=has_next,
        q=q,
    )


@bp.route("/healthz")
def healthz():
    return ("ok", 200)
