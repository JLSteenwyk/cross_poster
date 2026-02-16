# Cross-Poster

A web app for composing and posting to Twitter/X, BlueSky, and LinkedIn simultaneously. Write once, preview per-platform, and post everywhere.

## Features

- **Smart text splitting** — Automatically breaks long text into threads respecting each platform's character/grapheme limits (Twitter 280 chars, BlueSky 300 graphemes, LinkedIn 3000 chars). Splits at sentence boundaries first, then word boundaries.
- **Live preview** — Real-time platform-specific mockups that match the look of actual Twitter, BlueSky, and LinkedIn posts, including thread connectors.
- **Image attachment** — Attach a single image to your post. It's shown in the preview and auto-resized to meet each platform's size limits (Twitter 5 MB, BlueSky 1 MB, LinkedIn 10 MB).
- **Thread support** — Twitter and BlueSky posts are threaded as proper replies. LinkedIn joins parts into a single post.
- **Character counters** — Live counts with visual warnings when you exceed a platform's limit.
- **LinkedIn OAuth** — Built-in OAuth2 flow for LinkedIn authorization.

## Supported Platforms

| Platform | Thread Support | Image Support | Character Limit | Auth Method |
|----------|---------------|---------------|-----------------|-------------|
| Twitter/X | Yes | Yes | 280 chars | API keys |
| BlueSky | Yes | Yes | 300 graphemes | Username + app password |
| LinkedIn | No (joined) | Yes | 3,000 chars | OAuth2 |

## Setup

### 1. Clone and install

```bash
cd cross_poster
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

- **Twitter/X** — Create an app at [developer.x.com](https://developer.x.com/en/portal/dashboard) and fill in your API key, API secret, access token, and access token secret.
- **BlueSky** — Use your handle and an [app password](https://bsky.app/settings/app-passwords).
- **LinkedIn** — Create an app at [linkedin.com/developers](https://www.linkedin.com/developers/apps), add your client ID and secret. The access/refresh tokens are auto-managed after completing the OAuth flow in the app.

### 3. Run

```bash
python main.py
```

Opens at [http://localhost:5001](http://localhost:5001).

## Usage

1. Check the platforms you want to post to.
2. Type your message in the compose area.
3. Optionally attach an image (appears on the first post in a thread).
4. Preview your post across platform tabs — the character counters update live.
5. Click **Post** to publish to all selected platforms.

For LinkedIn, click **Authorize LinkedIn** the first time to complete the OAuth flow.

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

48 tests covering text splitting, API routes, image handling, and platform integrations.

## Project Structure

```
cross_poster/
├── main.py              # Entry point — starts Flask on port 5001
├── requirements.txt
├── .env.example
├── core/
│   ├── splitter.py      # Thread splitting algorithm
│   └── media.py         # Image validation & resizing
├── platforms/
│   ├── twitter.py       # Twitter/X via tweepy
│   ├── bluesky.py       # BlueSky via atproto
│   └── linkedin.py      # LinkedIn via OAuth2 + REST API
├── web/
│   ├── app.py           # Flask app factory
│   ├── routes.py        # API routes
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
└── tests/
    ├── test_splitter.py
    ├── test_routes.py
    ├── test_media.py
    ├── test_twitter.py
    ├── test_bluesky.py
    └── test_linkedin.py
```
