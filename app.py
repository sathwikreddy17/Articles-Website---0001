import os
from articles_website import create_app

app = create_app()

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.getenv("FLASK_RUN_PORT") or os.getenv("PORT") or "8000")
    app.run(debug=True, port=port)
