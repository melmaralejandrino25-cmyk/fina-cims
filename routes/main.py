from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


# ===========================
# MAIN DASHBOARD
# ===========================
@main_bp.route("/main")
def main_dashboard():

    return render_template(
        "main/dashboard.html"
    )
