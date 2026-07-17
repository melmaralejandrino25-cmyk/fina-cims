from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from database import get_db

auth_bp = Blueprint("auth", __name__)


# =========================
# LOGIN ROUTE
# =========================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Kung naka-login na, dumiretso sa dashboard
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        # Pagsuporta sa parehong hashed password at legacy plain-text (kung may lumang accounts)
        is_valid_password = False
        if user:
            stored_password = user["password"]
            if stored_password.startswith(("scrypt:", "pbkdf2:")):
                is_valid_password = check_password_hash(stored_password, password)
            else:
                is_valid_password = (stored_password == password)

        if user and is_valid_password:
            session["user"] = user["username"]
            session["role"] = user["role"]

            flash("Login Successful!", "success")
            return redirect(url_for("dashboard.dashboard"))

        flash("Invalid Username or Password", "danger")

    return render_template("login.html")


# =========================
# LOGOUT ROUTE
# =========================
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))