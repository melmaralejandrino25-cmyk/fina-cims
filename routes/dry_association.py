import io
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from database import get_db
from auth_utils import login_required, role_required

dry_association_bp = Blueprint("dry_association", __name__)


# =========================
# EXPORT FARMERS (EXCEL)
# =========================
@dry_association_bp.route("/export/<int:assoc_id>")
@login_required
@role_required("admin", "encoder")
def export_farmers(assoc_id):
    db = get_db()

    association = db.execute(
        "SELECT name FROM dry_associations WHERE id = ?", (assoc_id,)
    ).fetchone()

    farmers = db.execute(
        """
        SELECT
            id, rsbsa, last_name, first_name, middle_name,
            suffix, area, variety, sacks, kg
        FROM dry_farmers
        WHERE association_id = ?
        ORDER BY last_name, first_name
        """,
        (assoc_id,)
    ).fetchall()

    if not farmers:
        flash("No farmers found to export in this association.", "warning")
        return redirect(request.referrer or url_for("dry_municipality.list_municipalities"))

    # Convert SQLite Rows to List of Dicts for Pandas DataFrame
    rows = []
    for f in farmers:
        rows.append({
            "ID": f["id"],
            "RSBSA": f["rsbsa"],
            "Last Name": f["last_name"],
            "First Name": f["first_name"],
            "Middle Name": f["middle_name"],
            "Suffix": f["suffix"],
            "Area (ha)": f["area"],
            "Variety": f["variety"],
            "Sacks": f["sacks"],
            "Kilograms": f["kg"]
        })

    df = pd.DataFrame(rows)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dry Farmers")

    output.seek(0)

    # Dynamic file naming
    assoc_name = association["name"] if association else "association"
    clean_name = secure_filename(assoc_name.lower().replace(" ", "_"))
    filename = f"{clean_name}_dry_farmers.xlsx"

    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =========================
# VIEW ASSOCIATIONS
# =========================
@dry_association_bp.route("/<int:muni_id>")
@login_required
def view_associations(muni_id):

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
        flash("Dry Municipality not found.", "danger")
        return redirect(
            url_for("dry_municipality.list_municipalities")
        )


    associations = db.execute(
        """
        SELECT
            a.id,
            a.name,
            a.municipality_id,
            COUNT(f.id) AS farmer_count,
            COALESCE(SUM(f.area),0) AS total_area,
            COALESCE(SUM(f.sacks),0) AS total_sacks,
            COALESCE(SUM(f.sacks * f.kg),0) AS total_kg

        FROM dry_associations a

        LEFT JOIN dry_farmers f
        ON a.id = f.association_id

        WHERE a.municipality_id = ?

        GROUP BY 
            a.id,
            a.name,
            a.municipality_id

        ORDER BY a.name
        """,
        (muni_id,)
    ).fetchall()


    return render_template(
        "dry/association.html",
        muni=muni,
        associations=associations
    )

# =========================
# ADD ASSOCIATION
# =========================

@dry_association_bp.route("/add/<int:muni_id>", methods=["POST"])
@login_required
@role_required("admin", "encoder")
def add_association(muni_id):
    name = request.form.get("name", "").strip()

    if not name:
        flash("Association name cannot be empty.", "danger")
        return redirect(url_for("dry_association.view_associations", muni_id=muni_id))

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM dry_associations
        WHERE municipality_id = ?
          AND LOWER(TRIM(name)) = LOWER(TRIM(?))
        """,
        (muni_id, name)
    ).fetchone()

    if existing:
        flash("Association already exists in this municipality.", "warning")
        return redirect(url_for("dry_association.view_associations", muni_id=muni_id))

    db.execute(
        """
        INSERT INTO dry_associations (municipality_id, name)
        VALUES (?, ?)
        """,
        (muni_id, name)
    )

    db.commit()
    flash(f"Association '{name}' created successfully.", "success")

    return redirect(url_for("dry_association.view_associations", muni_id=muni_id))


# =========================
# EDIT ASSOCIATION
# =========================
@dry_association_bp.route("/edit/<int:id>/<int:muni_id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "encoder")
def edit_association(id, muni_id):

    db = get_db()

    association = db.execute(
        """
        SELECT *
        FROM dry_associations
        WHERE id = ?
        """,
        (id,)
    ).fetchone()


    if not association:
        flash("Association not found.", "danger")
        return redirect(
            url_for(
                "dry_association.view_associations",
                muni_id=muni_id
            )
        )


    if request.method == "POST":

        name = request.form.get("name", "").strip()


        if not name:
            flash(
                "Association name cannot be empty.",
                "danger"
            )

            return render_template(
                "dry/edit_association.html",
                association=association,
                muni_id=muni_id
            )


        existing = db.execute(
            """
            SELECT id
            FROM dry_associations
            WHERE municipality_id = ?
            AND LOWER(TRIM(name)) = LOWER(TRIM(?))
            AND id != ?
            """,
            (
                muni_id,
                name,
                id
            )
        ).fetchone()


        if existing:
            flash(
                "Association name already exists.",
                "warning"
            )

            return render_template(
                "dry/edit_association.html",
                association=association,
                muni_id=muni_id
            )


        db.execute(
            """
            UPDATE dry_associations
            SET name = ?
            WHERE id = ?
            """,
            (
                name,
                id
            )
        )


        db.commit()


        flash(
            "Association name updated successfully.",
            "info"
        )


        return redirect(
            url_for(
                "dry_association.view_associations",
                muni_id=muni_id
            )
        )


    return render_template(
        "dry/edit_association.html",
        association=association,
        muni_id=muni_id
    )
# =========================
# DELETE ASSOCIATION
# =========================
@dry_association_bp.route("/delete/<int:id>/<int:muni_id>")
@login_required
@role_required("admin")
def delete_association(id, muni_id):
    db = get_db()

    # Delete all farmers belonging to this association first
    db.execute("DELETE FROM dry_farmers WHERE association_id = ?", (id,))

    # Delete the association record
    db.execute("DELETE FROM dry_associations WHERE id = ?", (id,))

    db.commit()
    flash("Association and its farmer records deleted.", "warning")

    return redirect(url_for("dry_association.view_associations", muni_id=muni_id))