import re
from functools import wraps
from typing import Optional
from unicodedata import normalize
from flask import abort
from flask_login import login_required, current_user
from .models import Article


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
