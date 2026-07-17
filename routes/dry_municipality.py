from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from auth_utils import login_required, role_required

dry_municipality_bp = Blueprint("dry_municipality", __name__)


# ===========================
# LIST MUNICIPALITIES
# ===========================
@dry_municipality_bp.route("/")
@login_required
def list_municipalities():
    db = get_db()
    
    municipalities = db.execute(
        """
        SELECT *
        FROM dry_municipalities
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "dry/municipalities.html",
        municipalities=municipalities
    )


# ===========================
# ADD MUNICIPALITY
# ===========================
@dry_municipality_bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required("admin", "encoder")
def add_municipality():
    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("Municipality name cannot be empty.", "danger")
            return render_template("dry/add_municipality.html")

        db = get_db()

        existing = db.execute(
            """
            SELECT id
            FROM dry_municipalities
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            """,
            (name,)
        ).fetchone()

        if existing:
            flash("Municipality already exists.", "warning")
            return render_template("dry/add_municipality.html")

        db.execute(
            """
            INSERT INTO dry_municipalities (name)
            VALUES (?)
            """,
            (name,)
        )

        db.commit()
        flash(f"Municipality '{name}' added successfully.", "success")

        return redirect(url_for("dry_municipality.list_municipalities"))

    return render_template("dry/add_municipality.html")


# ===========================
# MUNICIPALITY DETAILS
# ===========================
@dry_municipality_bp.route("/<int:muni_id>")
@login_required
def municipality_detail(muni_id):
    db = get_db()

    muni = db.execute(
        """
        SELECT *
        FROM dry_municipalities
        WHERE id = ?
        """,
        (muni_id,)
    ).fetchone()

    if not muni:
        flash("Municipality not found.", "danger")
        return redirect(url_for("dry_municipality.list_municipalities"))

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
        FROM dry_associations a
        LEFT JOIN dry_farmers f
            ON a.id = f.association_id
        WHERE a.municipality_id = ?
        GROUP BY a.id, a.name
        ORDER BY a.name
        """,
        (muni_id,)
    ).fetchall()

    # Optimized single aggregate query for the entire municipality
    totals = db.execute(
        """
        SELECT 
            COUNT(f.id) AS total_farmers,
            COALESCE(SUM(f.area), 0) AS total_area,
            COALESCE(SUM(f.sacks), 0) AS total_sacks,
            COALESCE(SUM(f.sacks * f.kg), 0) AS total_kg
        FROM dry_farmers f
        JOIN dry_associations a ON f.association_id = a.id
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
        "dry/municipality_detail.html",
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
@dry_municipality_bp.route("/edit/<int:muni_id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "encoder")
def edit_municipality(muni_id):
    db = get_db()

    muni = db.execute(
        "SELECT * FROM dry_municipalities WHERE id = ?", (muni_id,)
    ).fetchone()

    if not muni:
        flash("Municipality not found.", "danger")
        return redirect(url_for("dry_municipality.list_municipalities"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("Municipality name cannot be empty.", "danger")
            return render_template("dry/edit_municipality.html", muni=muni)

        db.execute(
            """
            UPDATE dry_municipalities
            SET name = ?
            WHERE id = ?
            """,
            (name, muni_id)
        )
        db.commit()
        flash("Municipality updated successfully.", "info")

        return redirect(url_for("dry_municipality.list_municipalities"))

    return render_template("dry/edit_municipality.html", muni=muni)


# ===========================
# DELETE MUNICIPALITY
# ===========================
@dry_municipality_bp.route("/delete/<int:muni_id>")
@login_required
@role_required("admin")
def delete_municipality(muni_id):
    db = get_db()

    # Cascade delete farmers first, then associations, then municipality
    db.execute(
        """
        DELETE FROM dry_farmers
        WHERE association_id IN (
            SELECT id FROM dry_associations WHERE municipality_id = ?
        )
        """,
        (muni_id,)
    )

    db.execute(
        "DELETE FROM dry_associations WHERE municipality_id = ?",
        (muni_id,)
    )

    db.execute(
        "DELETE FROM dry_municipalities WHERE id = ?",
        (muni_id,)
    )

    db.commit()
    flash("Municipality and all associated records deleted.", "warning")

    return redirect(url_for("dry_municipality.list_municipalities"))