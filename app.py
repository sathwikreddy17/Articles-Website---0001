from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-later"        # fine for local
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db" # local DB file
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------- Models ----------
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(200), default="")  # comma-separated for now

# ---------- Forms ----------
class ArticleForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    tags  = StringField("Tags (comma-separated)")
    body  = TextAreaField("Body", validators=[DataRequired()])

# ---------- Routes ----------
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

@app.route("/article/<int:article_id>")
def article_detail(article_id):
    item = Article.query.get_or_404(article_id)
    return render_template("article_detail.html", item=item)

@app.route("/create", methods=["GET","POST"])
def create():
    form = ArticleForm()
    if form.validate_on_submit():
        a = Article(title=form.title.data.strip(),
                    body=form.body.data.strip(),
                    tags=form.tags.data.strip())
        db.session.add(a)
        db.session.commit()
        flash("Article created!", "success")
        return redirect(url_for("articles"))
    return render_template("create.html", form=form)

@app.route("/delete/<int:article_id>", methods=["POST"])
def delete(article_id):
    item = Article.query.get_or_404(article_id)
    db.session.delete(item)
    db.session.commit()
    flash("Deleted.", "info")
    return redirect(url_for("articles"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # creates site.db if missing
    app.run(debug=True)
