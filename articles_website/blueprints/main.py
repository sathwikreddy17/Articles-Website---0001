from flask import Blueprint, render_template, request, current_app, url_for, Response
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

    # Partial fragment for infinite scroll
    if request.args.get("partial") == "1" or request.headers.get("HX-Request"):
        return render_template(
            "partials/_article_cards.html",
            items=items,
            q=None,
            active_tag=None,
        )

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
    from flask import redirect

    return redirect(url_for("main.article_by_slug", slug=article.slug or article.id))


@bp.route("/tags/<tag>")
def by_tag(tag):
    # Add pagination for tag-filtered listing
    page = request.args.get("page", default=1, type=int)
    per_page_default = current_app.config.get("ARTICLES_PER_PAGE", 10)
    per_page = request.args.get("per_page", default=per_page_default, type=int)

    query = (
        Article.query.filter(Article.tags.ilike(f"%{tag}%"))
        .order_by(Article.id.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    has_prev = page > 1
    has_next = page * per_page < total

    # Partial fragment for infinite scroll
    if request.args.get("partial") == "1" or request.headers.get("HX-Request"):
        return render_template(
            "partials/_article_cards.html",
            items=items,
            q=None,
            active_tag=tag,
        )

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
        from flask import redirect
        return redirect(url_for("main.articles"))

    page = request.args.get("page", default=1, type=int)
    per_page_default = current_app.config.get("ARTICLES_PER_PAGE", 10)
    per_page = request.args.get("per_page", default=per_page_default, type=int)

    query = (
        Article.query.filter(
            or_(
                Article.title.ilike(f"%{q}%"),
                Article.body.ilike(f"%{q}%"),
            )
        )
        .order_by(Article.id.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    has_prev = page > 1
    has_next = page * per_page < total

    # Partial fragment for infinite scroll
    if request.args.get("partial") == "1" or request.headers.get("HX-Request"):
        return render_template(
            "partials/_article_cards.html",
            items=items,
            q=q,
            active_tag=None,
        )

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


@bp.get("/search/suggest")
def search_suggest():
    # Lightweight suggestions for HTMX dropdown
    q = (request.args.get("q", "") or "").strip()
    if not q:
        return render_template("partials/_suggestions.html", suggestions=[], q=q)
    suggestions = (
        Article.query.filter(
            or_(Article.title.ilike(f"%{q}%"), Article.body.ilike(f"%{q}%"))
        )
        .order_by(Article.id.desc())
        .limit(5)
        .all()
    )
    return render_template("partials/_suggestions.html", suggestions=suggestions, q=q)


@bp.route("/robots.txt")
def robots_txt():
    sitemap_url = url_for("main.sitemap", _external=True)
    content = f"""User-agent: *
Allow: /
Sitemap: {sitemap_url}
"""
    return Response(content, mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap():
    # Build a simple sitemap including key pages and all article slugs
    urls = [
        url_for("main.home", _external=True),
        url_for("main.articles", _external=True),
        url_for("main.about", _external=True),
    ]
    for (slug,) in Article.query.with_entities(Article.slug).order_by(Article.id.desc()).all():
        urls.append(url_for("main.article_by_slug", slug=slug, _external=True))

    xml_parts = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        xml_parts.append(f"  <url><loc>{u}</loc></url>")
    xml_parts.append("</urlset>")

    return Response("\n".join(xml_parts), mimetype="application/xml")


@bp.route("/feed.xml")
def feed():
    # Simple RSS 2.0 feed with latest 20 articles
    items = (
        Article.query.order_by(Article.id.desc()).limit(20).all()
    )
    site_url = url_for("main.home", _external=True)
    xml_parts = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<rss version=\"2.0\">",
        "<channel>",
        f"  <title>Articles Feed</title>",
        f"  <link>{site_url}</link>",
        f"  <description>Latest articles</description>",
    ]
    for a in items:
        link = url_for("main.article_by_slug", slug=a.slug, _external=True)
        title = a.title
        desc = (a.body[:200] + ("..." if len(a.body) > 200 else "")).replace("&", "&amp;")
        xml_parts += [
            "  <item>",
            f"    <title>{title}</title>",
            f"    <link>{link}</link>",
            f"    <guid>{link}</guid>",
            f"    <description>{desc}</description>",
            "  </item>",
        ]
    xml_parts += ["</channel>", "</rss>"]
    return Response("\n".join(xml_parts), mimetype="application/rss+xml")


@bp.route("/healthz")
def healthz():
    return ("ok", 200)
