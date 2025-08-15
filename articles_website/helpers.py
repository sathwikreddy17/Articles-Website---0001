import re
from functools import wraps
from typing import Optional
from unicodedata import normalize
from flask import abort
from flask_login import login_required, current_user
from .models import Article

# New: Markdown rendering and HTML sanitization
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
import bleach
from markupsafe import Markup, escape


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


def normalize_tags(tags: Optional[str]) -> str:
    """Normalize comma-separated tags: trim, lowercase, deduplicate, preserve order."""
    if not tags:
        return ""
    seen = set()
    result = []
    for raw in tags.split(","):
        t = raw.strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        result.append(t)
    return ", ".join(result)


# Allowlist for Bleach: keep typical Markdown output and codehilite wrappers
_ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS).union(
    {
        "p",
        "pre",
        "code",
        "h2",
        "h3",
        "div",
        "span",
        "ul",
        "ol",
        "li",
        "blockquote",
        "hr",
        "br",
        "a",
        "strong",
        "em",
    }
)
_ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "rel", "target"],
    "div": ["class"],
    "span": ["class"],
    "code": ["class"],
    "pre": ["class"],
    "h2": ["id", "class"],
    "h3": ["id", "class"],
}
_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def render_markdown_safe(text: str) -> str:
    """Render Markdown to HTML and sanitize via Bleach.

    Keeps fenced code blocks with Pygments (codehilite), headings (h2/h3), links, lists, etc.
    """
    html = markdown.markdown(
        text or "",
        extensions=["fenced_code", CodeHiliteExtension(linenums=False)],
    )
    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned


def highlight(text: str, query: str) -> Markup:
    """Highlight occurrences of query terms in text using <mark> safely.

    - Escapes the text first to prevent XSS.
    - Case-insensitive match on whitespace-separated tokens.
    - Returns Markup so Jinja won't re-escape the <mark> tags.
    """
    if not text or not query:
        return Markup(escape(text or ""))
    escaped = escape(text)
    # Build regex for any of the query words
    words = [w for w in re.split(r"\s+", query.strip()) if w]
    if not words:
        return Markup(escaped)
    pattern = re.compile(r"(" + "|".join(re.escape(w) for w in words) + r")", re.IGNORECASE)

    def _repl(m: re.Match) -> str:
        return f"<mark>{m.group(0)}</mark>"

    result = pattern.sub(_repl, str(escaped))
    return Markup(result)


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return wrapper
