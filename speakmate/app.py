import os
from flask import Flask, render_template
from speakmate.config import Config
from speakmate.database import init_db
from speakmate.routes.auth import auth_bp
from speakmate.routes.views import views_bp
from speakmate.routes.api import api_bp

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database with Flask app
init_db(app)

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
    app.run(host="127.0.0.1", port=5000, debug=True)
