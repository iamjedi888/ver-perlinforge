"""
TriptokForge Main Server
All route logic lives in routes/ as Blueprints.
"""

import os

from flask import Flask, jsonify, render_template, send_from_directory

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

# Import all blueprints
from routes.platform import platform_bp
from routes.channels import channels_bp
from routes.auth import auth_bp
from routes.api import api_bp
from routes.whitepages import whitepages_bp
from routes.forge import forge_bp
from routes.forge_routes import forge_downloads_bp
from routes.leaderboard import leaderboard_bp
from routes.forge_upgrades import forge_upgrades_bp
from routes.news import news_bp
from routes.epic_games_api import epic_api_bp

# Register blueprints
app.register_blueprint(platform_bp)
app.register_blueprint(channels_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(whitepages_bp)
app.register_blueprint(forge_bp)
app.register_blueprint(forge_downloads_bp)
app.register_blueprint(leaderboard_bp)
app.register_blueprint(forge_upgrades_bp)
app.register_blueprint(news_bp)
app.register_blueprint(epic_api_bp)


@app.route("/favicon.svg")
@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.svg", mimetype="image/svg+xml")


@app.route("/manifest.json")
def manifest():
    return jsonify(
        {
            "name": "TriptokForge",
            "short_name": "TriptokForge",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#07090d",
            "theme_color": "#00e5a0",
            "icons": [
                {"src": "/static/favicon.svg", "sizes": "any", "type": "image/svg+xml"},
                {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }
    )


@app.route("/news")
def news_page():
    return render_template("news.html")


@app.route("/cardgame")
def cardgame():
    return render_template("cardgame.html")


@app.route("/sitemap.xml")
def sitemap():
    base = "https://triptokforge.org"
    pages = ["", "/home", "/forge", "/gallery", "/feed", "/channels", "/community", "/whitepages", "/cardgame"]
    urls = "\n".join(f"  <url><loc>{base}{page}</loc></url>" for page in pages)
    return (
        f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>""",
        200,
        {"Content-Type": "application/xml"},
    )


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
