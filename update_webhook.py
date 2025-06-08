import hmac
import hashlib
import os
import subprocess
from flask import Flask, request, abort

app = Flask(__name__)

# Secret token configured in GitHub webhook settings
GITHUB_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "").encode()

# Path to this repository and WSGI file used by PythonAnywhere
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
WSGI_FILE = os.path.expanduser(os.environ.get(
    "WSGI_FILE",
    "/var/www/yourusername_pythonanywhere_com_wsgi.py"
))

@app.route("/update", methods=["POST"])
def update():
    """Pull the latest code and reload the app when GitHub sends a push webhook."""
    header_signature = request.headers.get("X-Hub-Signature-256")
    if not header_signature or "=" not in header_signature:
        abort(403)

    sha_name, signature = header_signature.split("=")
    if sha_name != "sha256":
        abort(501)

    mac = hmac.new(GITHUB_SECRET, msg=request.data, digestmod=hashlib.sha256)
    if not hmac.compare_digest(mac.hexdigest(), signature):
        abort(403)

    subprocess.call(["git", "-C", REPO_PATH, "pull"])  # Update repo
    subprocess.call(["touch", WSGI_FILE])  # Trigger app reload

    return "Updated", 200

if __name__ == "__main__":
    app.run()
