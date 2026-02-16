"""Cross-Poster: Post to Twitter, BlueSky, and LinkedIn."""

import sys
import threading
import webbrowser
from pathlib import Path

# Add cross_poster directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load .env from the cross_poster directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


def open_browser():
    """Open the browser after a short delay to let Flask start."""
    import time
    time.sleep(1)
    webbrowser.open("http://localhost:5001")


def main():
    from web.app import create_app

    app = create_app()

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="localhost", port=5001, debug=False)


if __name__ == "__main__":
    main()
