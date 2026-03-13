from flask import Blueprint, send_from_directory, abort
import os

whitepages_bp = Blueprint("whitepages", __name__)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@whitepages_bp.route("/whitepages")
def index():
    p = os.path.join(ROOT, "templates", "whitepages", "index.html")
    if os.path.exists(p):
        return send_from_directory(os.path.join(ROOT,"templates","whitepages"), "index.html")
    abort(404)
