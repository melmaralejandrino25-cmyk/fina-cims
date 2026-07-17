from flask import Blueprint, render_template
from database import get_db

wet_bp = Blueprint("wet", __name__)


# ==========================
# WET DASHBOARD
# ==========================
@wet_bp.route("/")
def wet_dashboard():
    db = get_db()

    # Get overall counts for wet season
    total_municipalities = db.execute(
        "SELECT COUNT(*) FROM wet_municipalities"
    ).fetchone()[0]

    total_associations = db.execute(
        "SELECT COUNT(*) FROM wet_associations"
    ).fetchone()[0]

    # Aggregated production metrics for wet season
    totals = db.execute(
        """
        SELECT 
            COUNT(f.id) AS total_farmers,
            COALESCE(SUM(f.area), 0) AS total_area,
            COALESCE(SUM(f.sacks), 0) AS total_sacks,
            COALESCE(SUM(f.sacks * f.kg), 0) AS total_kg
        FROM wet_farmers f
        """
    ).fetchone()

    total_farmers = totals["total_farmers"]
    total_area = round(totals["total_area"], 2)
    total_sacks = round(totals["total_sacks"], 2)
    total_kg = round(totals["total_kg"], 2)
    total_mt = round(total_kg / 1000.0, 2)

    return render_template(
        "wet/dashboard.html",
        total_municipalities=total_municipalities,
        total_associations=total_associations,
        total_farmers=total_farmers,
        total_area=total_area,
        total_sacks=total_sacks,
        total_kg=total_kg,
        total_mt=total_mt
    )


# ==========================
# WET MUNICIPALITY
# ==========================
@wet_bp.route("/municipality")
def wet_municipality():
    db = get_db()

    municipalities = db.execute(
        """
        SELECT 
            m.id, 
            m.name, 
            COUNT(DISTINCT a.id) AS assoc_count,
            COUNT(f.id) AS farmer_count
        FROM wet_municipalities m
        LEFT JOIN wet_associations a ON m.id = a.municipality_id
        LEFT JOIN wet_farmers f ON a.id = f.association_id
        GROUP BY m.id, m.name
        ORDER BY m.name ASC
        """
    ).fetchall()

    return render_template(
        "wet/municipalities.html",
        municipalities=municipalities
    )


# ==========================
# WET ASSOCIATION
# ==========================
@wet_bp.route("/association")
def wet_association():
    db = get_db()

    associations = db.execute(
        """
        SELECT 
            a.id, 
            a.name, 
            m.name AS municipality_name,
            COUNT(f.id) AS farmer_count
        FROM wet_associations a
        LEFT JOIN wet_municipalities m ON a.municipality_id = m.id
        LEFT JOIN wet_farmers f ON a.id = f.association_id
        GROUP BY a.id, a.name, m.name
        ORDER BY a.name ASC
        """
    ).fetchall()

    return render_template(
        "wet/association.html",
        associations=associations
    )


# ==========================
# WET FARMERS
# ==========================
@wet_bp.route("/farmers")
def wet_farmers():
    db = get_db()

    farmers = db.execute(
        """
        SELECT 
            f.*, 
            a.name AS association_name,
            m.name AS municipality_name
        FROM wet_farmers f
        LEFT JOIN wet_associations a ON f.association_id = a.id
        LEFT JOIN wet_municipalities m ON a.municipality_id = m.id
        ORDER BY f.last_name ASC, f.first_name ASC
        LIMIT 100
        """
    ).fetchall()

    return render_template(
        "wet/farmers.html",
        farmers=farmers
    )