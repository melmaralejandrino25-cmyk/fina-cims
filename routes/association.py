from flask import Blueprint, render_template, request, redirect, url_for, Response
import sqlite3
import pandas as pd
import io

association_bp = Blueprint("association", __name__)
DB = "database.db"


# =========================
# EXPORT FARMERS (EXCEL - CLEAN VERSION)
# =========================
@association_bp.route("/export/<int:assoc_id>")
def export_farmers(assoc_id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    association = c.execute("""
        SELECT name FROM associations WHERE id=?
    """, (assoc_id,)).fetchone()

    farmers = c.execute("""
        SELECT
            id,
            rsbsa,
            last_name,
            first_name,
            middle_name,
            suffix,
            area,
            variety,
            sacks,
            kg
        FROM farmers
        WHERE association_id=?
    """, (assoc_id,)).fetchall()

    conn.close()

    df = pd.DataFrame(farmers, columns=[
        "ID",
        "RSBSA",
        "Last Name",
        "First Name",
        "Middle Name",
        "Suffix",
        "Area (ha)",
        "Variety",
        "Sacks",
        "Kilograms"
    ])

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Farmers")

    output.seek(0)

    filename = f"{association['name']}_farmers.xlsx"

    return Response(
        output.read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# =========================
# VIEW ASSOCIATIONS
# =========================
@association_bp.route("/<int:muni_id>")
def view_associations(muni_id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    muni = c.execute("""
        SELECT * FROM municipalities WHERE id=?
    """, (muni_id,)).fetchone()

    if not muni:
        return "Municipality not found", 404

    associations = c.execute("""
        SELECT * FROM associations
        WHERE municipality_id=?
        ORDER BY id DESC
    """, (muni_id,)).fetchall()

    conn.close()

    return render_template(
        "association.html",
        muni=muni,
        associations=associations
    )


# =========================
# ADD ASSOCIATION
# =========================
@association_bp.route("/add/<int:muni_id>", methods=["POST"])
def add_association(muni_id):

    name = request.form.get("name")

    if not name:
        return "Missing name", 400

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO associations (municipality_id, name)
        VALUES (?, ?)
    """, (muni_id, name))

    conn.commit()
    conn.close()

    return redirect(url_for("association.view_associations", muni_id=muni_id))


# =========================
# DELETE ASSOCIATION (WITH FARMERS CLEANUP)
# =========================
@association_bp.route("/delete/<int:id>/<int:muni_id>")
def delete_association(id, muni_id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # delete farmers first
    c.execute("""
        DELETE FROM farmers
        WHERE association_id=?
    """, (id,))

    # delete association
    c.execute("""
        DELETE FROM associations
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("association.view_associations", muni_id=muni_id))