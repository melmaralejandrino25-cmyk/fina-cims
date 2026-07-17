import io
import pandas as pd
from flask import Blueprint, flash, render_template, request, redirect, url_for, send_file
from auth_utils import login_required, role_required
from database import get_db

dry_farmer_bp = Blueprint("dry_farmer", __name__)


# =========================
# LIST FARMERS
# =========================
@dry_farmer_bp.route("/<int:assoc_id>")
@login_required
def list_farmers(assoc_id):

    db = get_db()
    search = request.args.get("search", "").strip()

    association = db.execute(
        "SELECT * FROM dry_associations WHERE id = ?",
        (assoc_id,)
    ).fetchone()

    if not association:
        flash("Association not found.", "danger")
        return redirect(
            url_for("dry_municipality.list_municipalities")
        )

    if search:

        search_param = f"%{search}%"

        farmers = db.execute(
            """
            SELECT *
            FROM dry_farmers
            WHERE association_id = ?
            AND (
                rsbsa LIKE ?
                OR last_name LIKE ?
                OR first_name LIKE ?
            )
            ORDER BY last_name, first_name
            """,
            (
                assoc_id,
                search_param,
                search_param,
                search_param
            )
        ).fetchall()

    else:

        farmers = db.execute(
            """
            SELECT *
            FROM dry_farmers
            WHERE association_id = ?
            ORDER BY last_name, first_name
            """,
            (assoc_id,)
        ).fetchall()


    varieties = db.execute(
        """
        SELECT name
        FROM dry_varieties
        ORDER BY name
        """
    ).fetchall()


    return render_template(
        "dry/farmers.html",
        association=association,
        farmers=farmers,
        varieties=varieties,
        search=search
    )

# =========================
# ADD FARMER
# =========================
@dry_farmer_bp.route("/add/<int:assoc_id>", methods=["POST"])
@login_required
@role_required("admin","encoder")
def add_farmer(assoc_id):
    data = request.form
    db = get_db()

    db.execute(
        """
        INSERT INTO dry_farmers (
            association_id, rsbsa, last_name, first_name, middle_name,
            suffix, area, variety, sacks, kg
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assoc_id,
            data.get("rsbsa", "").strip(),
            data.get("last_name", "").strip(),
            data.get("first_name", "").strip(),
            data.get("middle_name", "").strip(),
            data.get("suffix", "").strip(),
            float(data.get("area", 0) or 0),
            data.get("variety", "").strip(),
            float(data.get("sacks", 0) or 0),
            float(data.get("kg", 0) or 0)
        )
    )
    db.commit()
    flash("Farmer successfully added.", "success")

    return redirect(url_for("dry_farmer.list_farmers", assoc_id=assoc_id))


# =========================
# EDIT FARMER
# =========================
@dry_farmer_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin","encoder")
def edit_farmer(id):
    db = get_db()

    farmer = db.execute("SELECT * FROM dry_farmers WHERE id = ?", (id,)).fetchone()
    if not farmer:
        return "Farmer not found", 404

    if request.method == "POST":
        db.execute(
            """
            UPDATE dry_farmers
            SET rsbsa = ?, last_name = ?, first_name = ?, middle_name = ?,
                suffix = ?, area = ?, variety = ?, sacks = ?, kg = ?
            WHERE id = ?
            """,
            (
                request.form.get("rsbsa", "").strip(),
                request.form.get("last_name", "").strip(),
                request.form.get("first_name", "").strip(),
                request.form.get("middle_name", "").strip(),
                request.form.get("suffix", "").strip(),
                float(request.form.get("area", 0) or 0),
                request.form.get("variety", "").strip(),
                float(request.form.get("sacks", 0) or 0),
                float(request.form.get("kg", 0) or 0),
                id
            )
        )
        db.commit()
        flash("Farmer information updated.", "info")

        return redirect(url_for("dry_farmer.list_farmers", assoc_id=farmer["association_id"]))

    return render_template("dry/edit_farmer.html", farmer=farmer)


# =========================
# DELETE FARMER
# =========================
@dry_farmer_bp.route("/delete/<int:id>")
@login_required
@role_required("admin")
def delete_farmer(id):
    db = get_db()

    farmer = db.execute("SELECT association_id FROM dry_farmers WHERE id = ?", (id,)).fetchone()
    if not farmer:
        return "Farmer not found", 404

    assoc_id = farmer["association_id"]

    db.execute("DELETE FROM dry_farmers WHERE id = ?", (id,))
    db.commit()
    flash("Farmer record deleted.", "warning")

    return redirect(url_for("dry_farmer.list_farmers", assoc_id=assoc_id))


# =========================
# UPLOAD EXCEL / CSV
# =========================
@dry_farmer_bp.route("/upload_excel/<int:assoc_id>", methods=["POST"])
@login_required
@role_required("admin","encoder")
def upload_excel(assoc_id):
    file = request.files.get("file")

    if not file or not file.filename:
        flash("No file selected for upload.", "danger")
        return redirect(url_for("dry_farmer.list_farmers", assoc_id=assoc_id))

    # Parse file type
    if file.filename.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file, sheet_name="NRP DISTRIBUTION", engine="calamine")
        except Exception:
            file.seek(0)
            df = pd.read_excel(file, engine="calamine")

    # Normalize headers
    df.columns = df.columns.astype(str).str.strip().str.lower()

    required_columns = [
        "ffrs rsbsa number", "farmer last name", "farmer first name",
        "farmer middle name", "farmer ext name", "farm address (province)",
        "farm address (municipality)", "seed variety claimed", "claimed area (ha)",
        "claimed seeds (kg)", "lot series", "sex", "birthdate", "contact number",
        "crop establishment", "eco-system", "eco-system source", "date of sowing",
        "average weight per bag (kg) - for all variety(ies)",
        "total production (no. of bags) - for all variety(ies)",
        "average area harvested (ha)", "seed variety planted",
        "seed class (hybrid, inbred, etc.)"
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        missing_fmt = "<br>• " + "<br>• ".join(missing)
        return f"<strong>Invalid Excel Template.</strong><br><br>Missing Columns:{missing_fmt}", 400

    db = get_db()
    inserted = 0
    duplicates = 0

    for _, row in df.iterrows():
        last_name = str(row.get("farmer last name") or "").strip()
        first_name = str(row.get("farmer first name") or "").strip()

        if not last_name and not first_name:
            continue

        raw_rsbsa = row.get("ffrs rsbsa number")
        rsbsa = "" if pd.isna(raw_rsbsa) else str(raw_rsbsa).strip()

        # Check RSBSA duplicate
        if rsbsa:
            duplicate = db.execute(
    """
    SELECT 1 
    FROM dry_farmers
    WHERE association_id = ?
    AND LOWER(TRIM(rsbsa)) = LOWER(TRIM(?))
    LIMIT 1
    """,
    (assoc_id, rsbsa)
).fetchone()

            if duplicate:
                duplicates += 1
                continue

        # Extract numeric values securely
        area = pd.to_numeric(row.get("claimed area (ha)"), errors="coerce")
        sacks = pd.to_numeric(row.get("total production (no. of bags) - for all variety(ies)"), errors="coerce")
        kg = pd.to_numeric(row.get("average weight per bag (kg) - for all variety(ies)"), errors="coerce")

        area = 0.0 if pd.isna(area) else float(area)
        sacks = 0.0 if pd.isna(sacks) else float(sacks)
        kg = 0.0 if pd.isna(kg) else float(kg)

        variety = (
            row.get("seed variety claimed") or 
            row.get("seed variety planted") or ""
        )

        db.execute(
            """
            INSERT INTO dry_farmers (
                association_id, rsbsa, last_name, first_name, middle_name,
                suffix, area, variety, sacks, kg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assoc_id, rsbsa, last_name, first_name,
                str(row.get("farmer middle name") or "").strip(),
                str(row.get("farmer ext name") or "").strip(),
                area, str(variety).strip(), sacks, kg
            )
        )
        inserted += 1

    db.commit()

    if duplicates > 0:
        flash(
            f"Dry Season upload complete: {inserted} farmer(s) imported; {duplicates} duplicate(s) skipped.",
            "warning"
        )
    else:
        flash(f"Dry Season upload complete: {inserted} farmer(s) imported successfully.", "success")

    return redirect(url_for("dry_farmer.list_farmers", assoc_id=assoc_id))


# =========================
# ASSOCIATION DASHBOARD
# =========================
@dry_farmer_bp.route("/dashboard/<int:assoc_id>")
@login_required
def association_dashboard(assoc_id):
    db = get_db()

    association = db.execute(
        "SELECT * FROM dry_associations WHERE id = ?", (assoc_id,)
    ).fetchone()

    if not association:
        flash("Association not found.", "danger")
        return redirect(url_for("dry_municipality.list_municipalities"))

    # Direct SQL aggregation for efficiency
    stats = db.execute(
        """
        SELECT 
            COUNT(*) as total_farmers,
            COALESCE(SUM(area), 0) as total_area,
            COALESCE(SUM(sacks), 0) as total_sacks,
            COALESCE(SUM(sacks * kg), 0) as total_kg
        FROM dry_farmers
        WHERE association_id = ?
        """,
        (assoc_id,)
    ).fetchone()

    total_farmers = stats["total_farmers"]
    total_area = round(stats["total_area"], 2)
    total_sacks = round(stats["total_sacks"], 2)
    total_kg = round(stats["total_kg"], 2)
    total_mt = round(total_kg / 1000.0, 2)

    average_yield = round(total_mt / total_area, 2) if total_area > 0 else 0.0

    return render_template(
        "dry/association_dashboard.html",
        association=association,
        total_farmers=total_farmers,
        total_area=total_area,
        total_sacks=total_sacks,
        total_kg=total_kg,
        total_mt=total_mt,
        average_yield=average_yield
    )


# =========================
# EXPORT FARMERS TO EXCEL
# =========================
@dry_farmer_bp.route("/export/<int:assoc_id>")
@login_required
@role_required("admin","encoder")
def export_farmers(assoc_id):
    db = get_db()

    farmers = db.execute(
        """
        SELECT rsbsa, last_name, first_name, middle_name, suffix, area, variety, sacks, kg
        FROM dry_farmers
        WHERE association_id = ?
        ORDER BY last_name, first_name
        """,
        (assoc_id,)
    ).fetchall()

    rows = []
    for f in farmers:
        rows.append({
            "FFRS RSBSA Number": f["rsbsa"],
            "Farmer Last Name": f["last_name"],
            "Farmer First Name": f["first_name"],
            "Farmer Middle Name": f["middle_name"],
            "Farmer Ext Name": f["suffix"],
            "Farm Address (Province)": "",
            "Farm Address (Municipality)": "",
            "Seed Variety Claimed": f["variety"],
            "Claimed Area (ha)": f["area"],
            "Claimed seeds (kg)": "",
            "Lot Series": "",
            "Sex": "",
            "Birthdate": "",
            "Contact Number": "",
            "Crop Establishment": "",
            "Eco-System": "",
            "Eco-System Source": "",
            "Date of Sowing": "",
            "Average Weight per Bag (kg) - for all variety(ies)": f["kg"],
            "Total Production (no. of bags) - for all variety(ies)": f["sacks"],
            "Average Area Harvested (ha)": f["area"],
            "Seed Variety Planted": f["variety"],
            "Seed Class (Hybrid, Inbred, etc.)": ""
        })

    df = pd.DataFrame(rows)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="NRP DISTRIBUTION")

    output.seek(0)

    return send_file(
        output,
        download_name=f"dry_farmers_assoc_{assoc_id}.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )