from flask import Blueprint, render_template, flash, redirect, url_for
from database import get_db

dry_bp = Blueprint("dry", __name__)


# ==========================
# DRY DASHBOARD
# ==========================
@dry_bp.route("/")
def dry_dashboard():
    db = get_db()

    # Get overall counts
    total_municipalities = db.execute(
        "SELECT COUNT(*) FROM dry_municipalities"
    ).fetchone()[0]

    total_associations = db.execute(
        "SELECT COUNT(*) FROM dry_associations"
    ).fetchone()[0]

    # Aggregated production metrics
    totals = db.execute(
        """
        SELECT 
            COUNT(f.id) AS total_farmers,
            COALESCE(SUM(f.area), 0) AS total_area,
            COALESCE(SUM(f.sacks), 0) AS total_sacks,
            COALESCE(SUM(f.sacks * f.kg), 0) AS total_kg
        FROM dry_farmers f
        """
    ).fetchone()

    total_farmers = totals["total_farmers"]
    total_area = round(totals["total_area"], 2)
    total_sacks = round(totals["total_sacks"], 2)
    total_kg = round(totals["total_kg"], 2)
    total_mt = round(total_kg / 1000.0, 2)

    return render_template(
        "dry/dashboard.html",
        total_municipalities=total_municipalities,
        total_associations=total_associations,
        total_farmers=total_farmers,
        total_area=total_area,
        total_sacks=total_sacks,
        total_kg=total_kg,
        total_mt=total_mt
    )


# ==========================
# DRY MUNICIPALITY
# ==========================
@dry_bp.route("/municipality/")
def dry_municipality():
    db = get_db()
    
    municipalities = db.execute(
        """
        SELECT 
            m.id, 
            m.name, 
            COUNT(DISTINCT a.id) AS assoc_count,
            COUNT(f.id) AS farmer_count
        FROM dry_municipalities m
        LEFT JOIN dry_associations a ON m.id = a.municipality_id
        LEFT JOIN dry_farmers f ON a.id = f.association_id
        GROUP BY m.id, m.name
        ORDER BY m.name ASC
        """
    ).fetchall()

    return render_template(
        "dry/municipalities.html",
        municipalities=municipalities
    )


# ==========================
# DRY ASSOCIATION
# ==========================
@dry_bp.route("/association/")
def dry_association():
    db = get_db()

    associations = db.execute(
        """
        SELECT 
            a.id, 
            a.name, 
            m.name AS municipality_name,
            COUNT(f.id) AS farmer_count
        FROM dry_associations a
        LEFT JOIN dry_municipalities m ON a.municipality_id = m.id
        LEFT JOIN dry_farmers f ON a.id = f.association_id
        GROUP BY a.id, a.name, m.name
        ORDER BY a.name ASC
        """
    ).fetchall()

    return render_template(
        "dry/association.html",
        associations=associations
    )


# ==========================
# DRY FARMERS
# ==========================
@dry_bp.route("/farmers/")
def dry_farmers():
    db = get_db()

    farmers = db.execute(
        """
        SELECT 
            f.*, 
            a.name AS association_name,
            m.name AS municipality_name
        FROM dry_farmers f
        LEFT JOIN dry_associations a ON f.association_id = a.id
        LEFT JOIN dry_municipalities m ON a.municipality_id = m.id
        ORDER BY f.last_name ASC, f.first_name ASC
        LIMIT 100
        """
    ).fetchall()

    return render_template(
        "dry/farmers.html",
        farmers=farmers
    )