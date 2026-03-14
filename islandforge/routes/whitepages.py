from flask import Blueprint, render_template

whitepages_bp = Blueprint("whitepages", __name__)

@whitepages_bp.route("/whitepages")
def index():
    return render_template("whitepages/index.html")
