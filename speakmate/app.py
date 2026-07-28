import os
from flask import Flask, render_template
from speakmate.config import Config
from speakmate.database import init_db
from speakmate.routes.auth import auth_bp
from speakmate.routes.views import views_bp
from speakmate.routes.api import api_bp

app = Flask(__name__)
app.config.from_object(Config)

# Ensure the instance or database path folder exists
db_dir = os.path.dirname(Config.DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# Initialize Database tables
init_db()

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)
app.register_blueprint(api_bp, url_prefix="/api")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("landing.html", error_message="404 - Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("landing.html", error_message="500 - Internal Server Error"), 500

if __name__ == "__main__":
    # Host on 0.0.0.0 to enable local network testing if requested
    app.run(host="127.0.0.1", port=5000, debug=True)
