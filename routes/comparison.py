from datetime import datetime
from flask import Blueprint, render_template
from database import get_db

comparison_bp = Blueprint("comparison", __name__)


# =========================
# HELPER FUNCTIONS
# =========================
def percent_change(old, new):
    if old == 0:
        return 0 if new == 0 else None
    return round(((new - old) / old) * 100, 2)


# =========================
# COMPARISON DASHBOARD
# =========================
@comparison_bp.route("/comparison")
def comparison_dashboard():
    db = get_db()

    # Consolidated query for overall summary statistics
    summary = db.execute(
        """
        WITH 
        wet_muni AS (SELECT COUNT(*) AS count FROM wet_municipalities),
        dry_muni AS (SELECT COUNT(*) AS count FROM dry_municipalities),
        wet_assoc AS (SELECT COUNT(*) AS count FROM wet_associations),
        dry_assoc AS (SELECT COUNT(*) AS count FROM dry_associations),
        wet_farm AS (
            SELECT 
                COUNT(*) AS count,
                COALESCE(SUM(area), 0) AS area,
                COALESCE(SUM(sacks * kg), 0) / 1000.0 AS mt
            FROM wet_farmers
        ),
        dry_farm AS (
            SELECT 
                COUNT(*) AS count,
                COALESCE(SUM(area), 0) AS area,
                COALESCE(SUM(sacks * kg), 0) / 1000.0 AS mt
            FROM dry_farmers
        )
        SELECT 
            (SELECT count FROM wet_muni) AS wet_muni,
            (SELECT count FROM dry_muni) AS dry_muni,
            (SELECT count FROM wet_assoc) AS wet_assoc,
            (SELECT count FROM dry_assoc) AS dry_assoc,
            (SELECT count FROM wet_farm) AS wet_farmer,
            (SELECT count FROM dry_farm) AS dry_farmer,
            (SELECT area FROM wet_farm) AS wet_area,
            (SELECT area FROM dry_farm) AS dry_area,
            (SELECT mt FROM wet_farm) AS wet_mt,
            (SELECT mt FROM dry_farm) AS dry_mt
        """
    ).fetchone()

    # Extract Summary Values
    wet_muni = summary["wet_muni"]
    dry_muni = summary["dry_muni"]
    wet_assoc = summary["wet_assoc"]
    dry_assoc = summary["dry_assoc"]
    wet_farmer = summary["wet_farmer"]
    dry_farmer = summary["dry_farmer"]

    wet_area = round(summary["wet_area"], 2)
    dry_area = round(summary["dry_area"], 2)
    wet_mt = round(summary["wet_mt"], 2)
    dry_mt = round(summary["dry_mt"], 2)

    # Calculate Differences
    farmer_difference = dry_farmer - wet_farmer
    area_difference = round(dry_area - wet_area, 2)
    production_difference = round(dry_mt - wet_mt, 2)
    association_difference = dry_assoc - wet_assoc
    municipality_difference = dry_muni - wet_muni

    # Calculate Percentage Changes
    farmer_change = percent_change(wet_farmer, dry_farmer)
    area_change = percent_change(wet_area, dry_area)
    production_change = percent_change(wet_mt, dry_mt)

    # Average Performance Metrics
    avg_mt_per_muni_wet = round(wet_mt / wet_muni, 2) if wet_muni else 0
    avg_mt_per_muni_dry = round(dry_mt / dry_muni, 2) if dry_muni else 0

    avg_mt_per_assoc_wet = round(wet_mt / wet_assoc, 2) if wet_assoc else 0
    avg_mt_per_assoc_dry = round(dry_mt / dry_assoc, 2) if dry_assoc else 0

    avg_yield_wet = round(wet_mt / wet_area, 2) if wet_area else 0
    avg_yield_dry = round(dry_mt / dry_area, 2) if dry_area else 0

    avg_farmer_mt_wet = round(wet_mt / wet_farmer, 2) if wet_farmer else 0
    avg_farmer_mt_dry = round(dry_mt / dry_farmer, 2) if dry_farmer else 0

    # =========================
    # MUNICIPALITY DATA
    # =========================
    wet_rows = db.execute(
        """
        SELECT
            wm.name AS municipality,
            COUNT(DISTINCT wa.id) AS associations,
            COUNT(DISTINCT wf.id) AS farmers,
            COALESCE(SUM(wf.area), 0) AS area,
            COALESCE(SUM(wf.sacks * wf.kg), 0) / 1000.0 AS mt
        FROM wet_municipalities wm
        LEFT JOIN wet_associations wa ON wa.municipality_id = wm.id
        LEFT JOIN wet_farmers wf ON wf.association_id = wa.id
        GROUP BY wm.id, wm.name
        """
    ).fetchall()

    dry_rows = db.execute(
        """
        SELECT
            dm.name AS municipality,
            COUNT(DISTINCT da.id) AS associations,
            COUNT(DISTINCT df.id) AS farmers,
            COALESCE(SUM(df.area), 0) AS area,
            COALESCE(SUM(df.sacks * df.kg), 0) / 1000.0 AS mt
        FROM dry_municipalities dm
        LEFT JOIN dry_associations da ON da.municipality_id = dm.id
        LEFT JOIN dry_farmers df ON df.association_id = da.id
        GROUP BY dm.id, dm.name
        """
    ).fetchall()

    # Merge Wet and Dry Municipality Records
    municipality_map = {}

    for row in wet_rows:
        key = row["municipality"].strip().lower()
        municipality_map[key] = {
            "municipality": row["municipality"],
            "wet_assoc": row["associations"] or 0,
            "dry_assoc": 0,
            "wet_farmers": row["farmers"] or 0,
            "dry_farmers": 0,
            "wet_area": round(row["area"] or 0, 2),
            "dry_area": 0,
            "wet_mt": round(row["mt"] or 0, 2),
            "dry_mt": 0,
        }

    for row in dry_rows:
        key = row["municipality"].strip().lower()
        if key not in municipality_map:
            municipality_map[key] = {
                "municipality": row["municipality"],
                "wet_assoc": 0,
                "dry_assoc": 0,
                "wet_farmers": 0,
                "dry_farmers": 0,
                "wet_area": 0,
                "dry_area": 0,
                "wet_mt": 0,
                "dry_mt": 0,
            }

        municipality_map[key]["dry_assoc"] = row["associations"] or 0
        municipality_map[key]["dry_farmers"] = row["farmers"] or 0
        municipality_map[key]["dry_area"] = round(row["area"] or 0, 2)
        municipality_map[key]["dry_mt"] = round(row["mt"] or 0, 2)

    municipality_rows = []
    for row in municipality_map.values():
        difference = round(row["dry_mt"] - row["wet_mt"], 2)
        change = percent_change(row["wet_mt"], row["dry_mt"])
        municipality_rows.append({
            **row,
            "difference": difference,
            "change": change
        })

    # Sort Municipalities by Dry Production (Descending)
    municipality_rows.sort(key=lambda x: x["dry_mt"], reverse=True)

    # Top Performers Extraction
    if municipality_rows:
        highest_production_wet = max(municipality_rows, key=lambda x: x["wet_mt"])
        highest_production_dry = max(municipality_rows, key=lambda x: x["dry_mt"])

        highest_yield_wet = max(
            municipality_rows,
            key=lambda x: (x["wet_mt"] / x["wet_area"]) if x["wet_area"] > 0 else 0
        )
        highest_yield_dry = max(
            municipality_rows,
            key=lambda x: (x["dry_mt"] / x["dry_area"]) if x["dry_area"] > 0 else 0
        )

        largest_area_wet = max(municipality_rows, key=lambda x: x["wet_area"])
        largest_area_dry = max(municipality_rows, key=lambda x: x["dry_area"])
    else:
        empty_node = {"municipality": "-", "wet_mt": 0, "dry_mt": 0, "wet_area": 0, "dry_area": 0}
        highest_production_wet = highest_production_dry = empty_node
        highest_yield_wet = highest_yield_dry = empty_node
        largest_area_wet = largest_area_dry = empty_node

    # =========================
    # ASSOCIATION COMPARISON
    # =========================
    association_query = db.execute(
        """
        WITH wet_data AS (
            SELECT
                wa.id AS association_id,
                wm.name AS municipality,
                LOWER(TRIM(wm.name)) AS municipality_key,
                wa.name AS association,
                LOWER(TRIM(wa.name)) AS association_key,
                COUNT(wf.id) AS farmers,
                COALESCE(SUM(wf.area), 0) AS area,
                COALESCE(SUM(wf.sacks * wf.kg), 0) / 1000.0 AS mt
            FROM wet_associations wa
            JOIN wet_municipalities wm ON wm.id = wa.municipality_id
            LEFT JOIN wet_farmers wf ON wf.association_id = wa.id
            GROUP BY wa.id, wm.name, wa.name
        ),
        dry_data AS (
            SELECT
                da.id AS association_id,
                dm.name AS municipality,
                LOWER(TRIM(dm.name)) AS municipality_key,
                da.name AS association,
                LOWER(TRIM(da.name)) AS association_key,
                COUNT(df.id) AS farmers,
                COALESCE(SUM(df.area), 0) AS area,
                COALESCE(SUM(df.sacks * df.kg), 0) / 1000.0 AS mt
            FROM dry_associations da
            JOIN dry_municipalities dm ON dm.id = da.municipality_id
            LEFT JOIN dry_farmers df ON df.association_id = da.id
            GROUP BY da.id, dm.name, da.name
        )
        SELECT
            w.municipality AS municipality,
            w.association AS wet_association,
            d.association AS dry_association,
            w.farmers AS wet_farmers,
            COALESCE(d.farmers, 0) AS dry_farmers,
            w.area AS wet_area,
            COALESCE(d.area, 0) AS dry_area,
            w.mt AS wet_mt,
            COALESCE(d.mt, 0) AS dry_mt
        FROM wet_data w
        LEFT JOIN dry_data d
            ON d.municipality_key = w.municipality_key
            AND d.association_key = w.association_key

        UNION ALL

        SELECT
            d.municipality AS municipality,
            NULL AS wet_association,
            d.association AS dry_association,
            0 AS wet_farmers,
            d.farmers AS dry_farmers,
            0 AS wet_area,
            d.area AS dry_area,
            0 AS wet_mt,
            d.mt AS dry_mt
        FROM dry_data d
        LEFT JOIN wet_data w
            ON w.municipality_key = d.municipality_key
            AND w.association_key = d.association_key
        WHERE w.association_id IS NULL
        ORDER BY municipality, wet_association, dry_association
        """
    ).fetchall()

    association_rows = []
    for row in association_query:
        association_rows.append({
            "municipality": row["municipality"],
            "wet_association": row["wet_association"],
            "dry_association": row["dry_association"],
            "wet_area": round(row["wet_area"], 2),
            "dry_area": round(row["dry_area"], 2),
            "wet_yield": round(row["wet_mt"] / row["wet_area"], 2) if row["wet_area"] else 0,
            "dry_yield": round(row["dry_mt"] / row["dry_area"], 2) if row["dry_area"] else 0,
            "wet_farmers": row["wet_farmers"],
            "dry_farmers": row["dry_farmers"]
        })

    # Metric Trends Status
    production_status = "increased" if production_difference > 0 else ("decreased" if production_difference < 0 else "no change")
    area_status = "increased" if area_difference > 0 else ("decreased" if area_difference < 0 else "no change")
    farmer_status = "increased" if farmer_difference > 0 else ("decreased" if farmer_difference < 0 else "no change")

    updated_at = datetime.now().strftime("%b %d, %Y %I:%M %p")

    return render_template(
        "comparison/dashboard.html",
        # Status Flags
        production_status=production_status,
        area_status=area_status,
        farmer_status=farmer_status,

        # Raw Counts
        wet_muni=wet_muni,
        dry_muni=dry_muni,
        wet_assoc=wet_assoc,
        dry_assoc=dry_assoc,
        wet_farmer=wet_farmer,
        dry_farmer=dry_farmer,

        # Area & Production
        wet_area=wet_area,
        dry_area=dry_area,
        wet_mt=wet_mt,
        dry_mt=dry_mt,

        # Changes & Differences
        farmer_change=farmer_change,
        area_change=area_change,
        production_change=production_change,
        farmer_difference=farmer_difference,
        area_difference=area_difference,
        production_difference=production_difference,
        association_difference=association_difference,
        municipality_difference=municipality_difference,

        # Averages
        avg_mt_per_muni_wet=avg_mt_per_muni_wet,
        avg_mt_per_muni_dry=avg_mt_per_muni_dry,
        avg_mt_per_assoc_wet=avg_mt_per_assoc_wet,
        avg_mt_per_assoc_dry=avg_mt_per_assoc_dry,
        avg_yield_wet=avg_yield_wet,
        avg_yield_dry=avg_yield_dry,
        avg_farmer_mt_wet=avg_farmer_mt_wet,
        avg_farmer_mt_dry=avg_farmer_mt_dry,

        # Tables & Lists
        municipality_rows=municipality_rows,
        association_rows=association_rows,

        # Performers
        highest_production_wet=highest_production_wet,
        highest_production_dry=highest_production_dry,
        highest_yield_wet=highest_yield_wet,
        highest_yield_dry=highest_yield_dry,
        largest_area_wet=largest_area_wet,
        largest_area_dry=largest_area_dry,

        updated_at=updated_at
    )