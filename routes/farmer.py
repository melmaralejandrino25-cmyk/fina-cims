from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
import pandas as pd

farmer_bp = Blueprint("farmer", __name__)

DB = "database.db"


# =========================
# DB CONNECTION
# =========================
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# LIST FARMERS
# =========================
@farmer_bp.route("/<int:assoc_id>")
def list_farmers(assoc_id):

    conn = get_db()
    c = conn.cursor()

    search = request.args.get("search", "").strip()

    association = c.execute("""
        SELECT *
        FROM associations
        WHERE id=?
    """, (assoc_id,)).fetchone()

    if search:
        farmers = c.execute("""
            SELECT *
            FROM farmers
            WHERE association_id=?
            AND (
                rsbsa LIKE ?
                OR last_name LIKE ?
                OR first_name LIKE ?
            )
            ORDER BY last_name, first_name
        """, (
            assoc_id,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()
    else:
        farmers = c.execute("""
            SELECT *
            FROM farmers
            WHERE association_id=?
            ORDER BY last_name, first_name
        """, (assoc_id,)).fetchall()

    varieties = c.execute("""
        SELECT name
        FROM varieties
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "farmers.html",
        association=association,
        farmers=farmers,
        varieties=varieties
    )


# =========================
# ADD FARMER
# =========================
@farmer_bp.route("/add/<int:assoc_id>", methods=["POST"])
def add_farmer(assoc_id):

    data = request.form

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO farmers(
            association_id,
            rsbsa,
            last_name,
            first_name,
            middle_name,
            suffix,
            area,
            variety,
            sacks,
            kg
        )
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        assoc_id,
        data["rsbsa"],
        data["last_name"],
        data["first_name"],
        data["middle_name"],
        data["suffix"],
        data["area"],
        data["variety"],
        data["sacks"],
        data["kg"]
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("farmer.list_farmers", assoc_id=assoc_id))
# =========================
# EDIT FARMER
# =========================
@farmer_bp.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_farmer(id):

    conn = get_db()
    c = conn.cursor()

    farmer = c.execute("""
        SELECT * FROM farmers WHERE id=?
    """, (id,)).fetchone()

    if not farmer:
        conn.close()
        return "Not found", 404

    if request.method == "POST":

        c.execute("""
            UPDATE farmers
            SET rsbsa=?,
                last_name=?,
                first_name=?,
                middle_name=?,
                suffix=?,
                area=?,
                variety=?,
                sacks=?,
                kg=?
            WHERE id=?
        """, (
            request.form["rsbsa"],
            request.form["last_name"],
            request.form["first_name"],
            request.form["middle_name"],
            request.form["suffix"],
            request.form["area"],
            request.form["variety"],
            request.form["sacks"],
            request.form["kg"],
            id
        ))

        conn.commit()

        assoc_id = farmer["association_id"]
        conn.close()

        return redirect(url_for("farmer.list_farmers", assoc_id=assoc_id))

    conn.close()

    return render_template("edit_farmer.html", farmer=farmer)


# =========================
# DELETE FARMER
# =========================
@farmer_bp.route("/delete/<int:id>")
def delete_farmer(id):

    conn = get_db()
    c = conn.cursor()

    farmer = c.execute("""
        SELECT association_id
        FROM farmers
        WHERE id=?
    """, (id,)).fetchone()

    if not farmer:
        conn.close()
        return "Not found", 404

    assoc_id = farmer["association_id"]

    c.execute("""
        DELETE FROM farmers
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("farmer.list_farmers", assoc_id=assoc_id))
# =========================
# UPLOAD EXCEL
# =========================
@farmer_bp.route("/upload_excel/<int:assoc_id>", methods=["POST"])
def upload_excel(assoc_id):

    file = request.files.get("file")

    if not file:
        return "No file uploaded", 400

    if file.filename.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    df.columns = df.columns.str.strip().str.lower()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    inserted = 0

    for _, row in df.iterrows():

        last_name = row.get("last name") or row.get("lastname")
        first_name = row.get("first name") or row.get("firstname")

        if not last_name and not first_name:
            continue

        c.execute("""
            INSERT INTO farmers(
                association_id,
                rsbsa,
                last_name,
                first_name,
                middle_name,
                suffix,
                area,
                variety,
                sacks,
                kg
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (
            assoc_id,
            row.get("rsbsa"),
            last_name,
            first_name,
            row.get("middle name") or "",
            row.get("suffix") or "",
            row.get("area") or 0,
            row.get("variety") or "",
            row.get("sacks") or 0,
            row.get("kg") or 0
        ))

        inserted += 1

    conn.commit()
    conn.close()

    print("INSERTED:", inserted)

    return redirect(url_for("farmer.list_farmers", assoc_id=assoc_id))


# =========================
# PRODUCTION DASHBOARD PER ASSOCIATION
# =========================
@farmer_bp.route("/dashboard/<int:assoc_id>")
def association_dashboard(assoc_id):

    conn = get_db()
    c = conn.cursor()

    association = c.execute("""
        SELECT * FROM associations
        WHERE id=?
    """, (assoc_id,)).fetchone()

    farmers = c.execute("""
        SELECT * FROM farmers
        WHERE association_id=?
    """, (assoc_id,)).fetchall()

    total_farmers = len(farmers)
    total_area = sum((f["area"] or 0) for f in farmers)
    total_kg = sum((f["sacks"] or 0) * (f["kg"] or 0) for f in farmers)
    total_mt = total_kg / 1000 if total_kg else 0

    variety_map = {}

    for f in farmers:
        variety = f["variety"] or "Unknown"
        kg = (f["sacks"] or 0) * (f["kg"] or 0)
        variety_map[variety] = variety_map.get(variety, 0) + kg

    top_variety = None
    top_value = 0

    for variety, value in variety_map.items():
        if value > top_value:
            top_variety = variety
            top_value = value

    conn.close()

    return render_template(
        "association_dashboard.html",
        association=association,
        total_farmers=total_farmers,
        total_area=total_area,
        total_kg=total_kg,
        total_mt=total_mt,
        top_variety=top_variety,
        top_value=top_value
    )