import os
import pytest
from articles_website import create_app


@pytest.fixture()
def app():
    os.environ.setdefault("SECRET_KEY", "test-secret")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("ARTICLES_PER_PAGE", "5")
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        from articles_website.extensions import db
        db.create_all()
        yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_home_ok(client):
    res = client.get("/")
    assert res.status_code == 200


def test_articles_ok(client):
    res = client.get("/articles")
    assert res.status_code == 200


def test_search_redirects_without_q(client):
    res = client.get("/search", follow_redirects=False)
    assert res.status_code in (301, 302)


def test_tags_page_ok_empty(client):
    res = client.get("/tags/python")
    assert res.status_code == 200


def test_placeholder():
    assert True
