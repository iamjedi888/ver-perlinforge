"""
TriptokForge Main Server
All route logic lives in routes/ as Blueprints.
"""

from flask import Flask, render_template
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev')

# Import all blueprints
from routes.platform        import platform_bp
from routes.channels        import channels_bp
from routes.auth            import auth_bp
from routes.api             import api_bp
from routes.whitepages      import whitepages_bp
from routes.forge           import forge_bp  # FIXED: was forge_routes
from routes.leaderboard     import leaderboard_bp
from routes.forge_upgrades  import forge_upgrades_bp
from routes.news            import news_bp
from routes.epic_games_api  import epic_api_bp

# Register blueprints (ONCE each)
app.register_blueprint(platform_bp)
app.register_blueprint(channels_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(whitepages_bp)
app.register_blueprint(forge_bp)
app.register_blueprint(leaderboard_bp)
app.register_blueprint(forge_upgrades_bp)
app.register_blueprint(news_bp)
app.register_blueprint(epic_api_bp)

# Main routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/news')
def news_page():
    return render_template('news.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

@app.route('/cardgame')
def cardgame():
    return render_template('cardgame.html')
