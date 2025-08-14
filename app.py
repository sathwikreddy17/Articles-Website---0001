from articles_website import create_app

app = create_app()

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
