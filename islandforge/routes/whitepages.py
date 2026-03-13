from flask import Blueprint, Response, abort
import os

whitepages_bp = Blueprint("whitepages", __name__)

@whitepages_bp.route("/whitepages")
def index():
    p = "/home/ubuntu/ver-perlinforge/islandforge/templates/whitepages/index.html"
    if os.path.exists(p):
        return Response(open(p).read(), mimetype="text/html")
    abort(404)
