from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth_utils import login_required, role_required
from database import get_db

wet_municipality_bp = Blueprint("wet_municipality", __name__)


# ===========================
# LIST MUNICIPALITIES
# ===========================
@wet_municipality_bp.route("/")
@login_required
def list_municipalities():
    db = get_db()

    municipalities = db.execute(
        """
        SELECT *
        FROM wet_municipalities
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "wet/municipalities.html",
        municipalities=municipalities
    )


# ===========================
# ADD MUNICIPALITY
# ===========================
@wet_municipality_bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required("admin", "encoder")
def add_municipality():
    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("Municipality name cannot be empty.", "danger")
            return render_template("wet/add_municipality.html")

        db = get_db()
        db.execute(
            """
            INSERT INTO wet_municipalities (name)
            VALUES (?)
            """,
            (name,)
        )
        db.commit()
        flash(f"Municipality '{name}' added successfully.", "success")

        return redirect(url_for("wet_municipality.list_municipalities"))

    return render_template("wet/add_municipality.html")


# ===========================
# MUNICIPALITY DETAILS
# ===========================
@wet_municipality_bp.route("/<int:muni_id>")
@login_required
def municipality_detail(muni_id):
    db = get_db()

    muni = db.execute(
        """
        SELECT *
        FROM wet_municipalities
        WHERE id = ?
        """,
        (muni_id,)
    ).fetchone()

    if not muni:
        flash("Wet Municipality not found.", "danger")
        return redirect(url_for("wet_municipality.list_municipalities"))

    # Fetch associations with their aggregated farmer metrics
    associations = db.execute(
        """
        SELECT
            a.id,
            a.name,
            COUNT(f.id) AS farmer_count,
            COALESCE(SUM(f.area), 0) AS total_area,
            COALESCE(SUM(f.sacks), 0) AS total_sacks,
            COALESCE(SUM(f.sacks * f.kg), 0) AS total_kg
        FROM wet_associations a
        LEFT JOIN wet_farmers f
            ON a.id = f.association_id
        WHERE a.municipality_id = ?
        GROUP BY a.id, a.name
        ORDER BY a.name
        """,
        (muni_id,)
    ).fetchall()

    # Single aggregate query for overall totals
    totals = db.execute(
        """
        SELECT 
            COUNT(f.id) AS total_farmers,
            COALESCE(SUM(f.area), 0) AS total_area,
            COALESCE(SUM(f.sacks), 0) AS total_sacks,
            COALESCE(SUM(f.sacks * f.kg), 0) AS total_kg
        FROM wet_farmers f
        JOIN wet_associations a ON f.association_id = a.id
        WHERE a.municipality_id = ?
        """,
        (muni_id,)
    ).fetchone()

    total_farmers = totals["total_farmers"]
    total_area = round(totals["total_area"], 2)
    total_sacks = round(totals["total_sacks"], 2)
    total_kg = round(totals["total_kg"], 2)
    total_mt = round(total_kg / 1000.0, 2)

    return render_template(
        "wet/municipality_detail.html",
        muni=muni,
        associations=associations,
        association_count=len(associations),
        total_farmers=total_farmers,
        total_area=total_area,
        total_sacks=total_sacks,
        total_kg=total_kg,
        total_mt=total_mt
    )


# ===========================
# EDIT MUNICIPALITY
# ===========================
@wet_municipality_bp.route("/edit/<int:muni_id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "encoder")
def edit_municipality(muni_id):
    db = get_db()

    muni = db.execute(
        "SELECT * FROM wet_municipalities WHERE id = ?", (muni_id,)
    ).fetchone()

    if not muni:
        flash("Wet Municipality not found.", "danger")
        return redirect(url_for("wet_municipality.list_municipalities"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("Municipality name cannot be empty.", "danger")
            return render_template("wet/edit_municipality.html", muni=muni)

        db.execute(
            """
            UPDATE wet_municipalities
            SET name = ?
            WHERE id = ?
            """,
            (name, muni_id)
        )
        db.commit()
        flash("Municipality updated successfully.", "info")

        return redirect(url_for("wet_municipality.list_municipalities"))

    return render_template("wet/edit_municipality.html", muni=muni)


# ===========================
# DELETE MUNICIPALITY
# ===========================
@wet_municipality_bp.route("/delete/<int:muni_id>")
@login_required
@role_required("admin")
def delete_municipality(muni_id):
    db = get_db()

    # Cascade delete farmers first, then associations, then municipality
    db.execute(
        """
        DELETE FROM wet_farmers
        WHERE association_id IN (
            SELECT id FROM wet_associations WHERE municipality_id = ?
        )
        """,
        (muni_id,)
    )

    db.execute(
        "DELETE FROM wet_associations WHERE municipality_id = ?",
        (muni_id,)
    )

    db.execute(
        "DELETE FROM wet_municipalities WHERE id = ?",
        (muni_id,)
    )

    db.commit()
    flash("Municipality and all associated records deleted.", "warning")

    return redirect(url_for("wet_municipality.list_municipalities"))