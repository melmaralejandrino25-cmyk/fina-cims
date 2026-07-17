from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

municipality_bp = Blueprint("municipality", __name__)

DB = "database.db"


# ===========================
# LIST MUNICIPALITIES
# ===========================
@municipality_bp.route("/")
def list_municipalities():

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    municipalities = c.execute(
        "SELECT * FROM municipalities ORDER BY name"
    ).fetchall()

    conn.close()

    return render_template(
        "municipalities.html",
        municipalities=municipalities
    )


# ===========================
# ADD MUNICIPALITY
# ===========================
@municipality_bp.route("/add", methods=["GET", "POST"])
def add_municipality():

    if request.method == "POST":

        name = request.form["name"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute(
            "INSERT INTO municipalities(name) VALUES(?)",
            (name,)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("municipality.list_municipalities"))

    return render_template("add_municipality.html")


# ===========================
# MUNICIPALITY DETAILS
# ===========================
@municipality_bp.route("/<int:muni_id>")
def municipality_detail(muni_id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    muni = c.execute(
        "SELECT * FROM municipalities WHERE id=?",
        (muni_id,)
    ).fetchone()

    if muni is None:
        conn.close()
        return render_template(
            "not_found.html",
            message="Municipality not found."
        ), 404

    associations = c.execute(
        """
        SELECT *
        FROM associations
        WHERE municipality_id=?
        ORDER BY name
        """,
        (muni_id,)
    ).fetchall()

    total_farmers = c.execute(
        """
        SELECT COUNT(*)
        FROM farmers f
        JOIN associations a ON f.association_id = a.id
        WHERE a.municipality_id=?
        """,
        (muni_id,)
    ).fetchone()[0]

    total_area = c.execute(
        """
        SELECT COALESCE(SUM(f.area),0)
        FROM farmers f
        JOIN associations a ON f.association_id = a.id
        WHERE a.municipality_id=?
        """,
        (muni_id,)
    ).fetchone()[0]

    total_sacks = c.execute(
        """
        SELECT COALESCE(SUM(f.sacks),0)
        FROM farmers f
        JOIN associations a ON f.association_id = a.id
        WHERE a.municipality_id=?
        """,
        (muni_id,)
    ).fetchone()[0]

    total_kg = c.execute(
        """
        SELECT COALESCE(SUM(f.kg),0)
        FROM farmers f
        JOIN associations a ON f.association_id = a.id
        WHERE a.municipality_id=?
        """,
        (muni_id,)
    ).fetchone()[0]

    total_mt = total_kg / 1000

    conn.close()

    return render_template(
        "municipality_detail.html",
        muni=muni,
        associations=associations,
        total_farmers=total_farmers,
        total_area=total_area,
        total_sacks=total_sacks,
        total_kg=total_kg,
        total_mt=total_mt
    )


# ===========================
# EDIT MUNICIPALITY (FIXED)
# ===========================
@municipality_bp.route("/edit/<int:muni_id>", methods=["GET", "POST"])
def edit_municipality(muni_id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        new_name = request.form["name"]

        c.execute("""
            UPDATE municipalities
            SET name = ?
            WHERE id = ?
        """, (new_name, muni_id))

        conn.commit()
        conn.close()

        return redirect(url_for("municipality.list_municipalities"))

    muni = c.execute(
        "SELECT * FROM municipalities WHERE id=?",
        (muni_id,)
    ).fetchone()

    conn.close()

    return render_template("edit_municipality.html", muni=muni)


# ===========================
# DELETE MUNICIPALITY
# ===========================
@municipality_bp.route("/delete/<int:muni_id>")
def delete_municipality(muni_id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "DELETE FROM associations WHERE municipality_id=?",
        (muni_id,)
    )

    c.execute(
        "DELETE FROM municipalities WHERE id=?",
        (muni_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("municipality.list_municipalities"))