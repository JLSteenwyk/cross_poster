"""Flask app factory for Cross-Poster."""

import sys
from pathlib import Path

from flask import Flask

# Ensure cross_poster directory is on sys.path for module imports
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def create_app():
    app = Flask(__name__)
    app.secret_key = "cross-poster-local-only"

    from web.routes import bp
    app.register_blueprint(bp)

    return app
