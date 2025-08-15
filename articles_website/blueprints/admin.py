from flask import Blueprint, render_template, redirect, url_for, flash
from ..forms import ArticleForm
from ..models import Article
from ..extensions import db
from ..helpers import admin_required, unique_slug, normalize_tags

bp = Blueprint("admin", __name__)


@bp.route("/create", methods=["GET", "POST"])
@admin_required
def create():
    form = ArticleForm()
    if form.validate_on_submit():
        article = Article(
            title=form.title.data.strip(),
            body=form.body.data.strip(),
            tags=normalize_tags(form.tags.data),
            cover_image=(form.cover_image.data or "").strip() or None,
        )
        article.slug = unique_slug(article.title)
        db.session.add(article)
        db.session.commit()
        flash("Article created!", "success")
        return redirect(url_for("main.article_by_slug", slug=article.slug))
    return render_template("create.html", form=form)


@bp.route("/edit/<int:article_id>", methods=["GET", "POST"])
@admin_required
def edit(article_id):
    article = Article.query.get_or_404(article_id)
    form = ArticleForm(obj=article)
    if form.validate_on_submit():
        new_title = form.title.data.strip()
        article.title = new_title
        article.tags = normalize_tags(form.tags.data)
        article.body = form.body.data.strip()
        article.cover_image = (form.cover_image.data or "").strip() or None
        article.slug = unique_slug(new_title, existing_id=article.id)
        db.session.commit()
        flash("Article updated!", "success")
        return redirect(url_for("main.article_by_slug", slug=article.slug))
    return render_template("edit.html", form=form, article=article)


@bp.route("/delete/<int:article_id>", methods=["POST"])
@admin_required
def delete(article_id):
    article = Article.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    flash("Deleted.", "info")
    return redirect(url_for("main.articles"))
