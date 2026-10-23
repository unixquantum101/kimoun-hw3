import os
import socket

from flask import Flask, Response

app = Flask(__name__)

# ---- values baked into the image at build time by Jenkins -----------------
APP_VERSION = os.environ.get("APP_VERSION", "dev")      # the exact git tag, e.g. v1.1.0
GIT_SHA = os.environ.get("GIT_SHA", "unknown")
BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "0")

# ---- edit these between releases so every version looks different ---------
THEME_COLOR = "#c92a2a"
BANNER = "v1.0.0 First release"          # e.g. "New in this release: ..."


@app.route("/")
def index():
    banner = f'<p class="banner">{BANNER}</p>' if BANNER else ""
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Release Demo {APP_VERSION}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 3rem auto; max-width: 36rem;
           line-height: 1.6; color: #14202b; }}
    .version {{ font-size: 3rem; font-weight: 700; color: {THEME_COLOR}; margin: 0; }}
    .banner {{ background: #fff4e5; border-left: 4px solid #f08c00; padding: .5rem 1rem; }}
    code {{ background: #eef2f5; padding: .1rem .35rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <p>Release Management with Jenkins, ECR &amp; Docker Swarm</p>
  <p class="version">{APP_VERSION}</p>
  {banner}
  <p>Jenkins build: <code>#{BUILD_NUMBER}</code> &middot; commit: <code>{GIT_SHA}</code></p>
  <p>Served by container: <code>{socket.gethostname()}</code></p>
</body>
</html>"""
    resp = Response(html, mimetype="text/html")
    resp.headers["X-App-Version"] = APP_VERSION
    return resp


@app.route("/health")
def health():
    return {"status": "ok", "version": APP_VERSION, "sha": GIT_SHA, "build": BUILD_NUMBER}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
