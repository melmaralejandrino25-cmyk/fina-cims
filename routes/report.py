import math
from flask import Blueprint, render_template, request
from database import get_db

report_bp = Blueprint("report", __name__)

@report_bp.route("/report")
def report():
    db = get_db()
    
    # ============================
    # 1. PARSE QUERY PARAMETERS
    # ============================
    season = request.args.get("season", "all").lower()        # 'all', 'wet', or 'dry'
    municipality = request.args.get("municipality", "").strip()
    search = request.args.get("search", "").strip()
    
    # Pagination parameters
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    
    per_page = 15
    offset = (page - 1) * per_page

    # ============================
    # 2. DYNAMIC QUERY BUILDING
    # ============================
    # Gagamit ng UNION query kung 'all', o i-target ang tiyak na table
    base_queries = []
    params = []

    if season in ["all", "wet"]:
        base_queries.append("""
            SELECT 'Wet' AS season, id, farmer_name, municipality, association, 
                   area_hectares, estimated_yield_tons, status 
            FROM wet_farmers
            WHERE 1=1
        """)
    
    if season in ["all", "dry"]:
        base_queries.append("""
            SELECT 'Dry' AS season, id, farmer_name, municipality, association, 
                   area_hectares, estimated_yield_tons, status 
            FROM dry_farmers
            WHERE 1=1
        """)

    # Combine queries using UNION ALL
    full_subquery = " UNION ALL ".join(base_queries)
    
    # Main filtering wrapper
    where_clauses = []
    wrapper_params = []

    if municipality:
        where_clauses.append("municipality LIKE ?")
        wrapper_params.append(f"%{municipality}%")

    if search:
        where_clauses.append("(farmer_name LIKE ? OR association LIKE ?)")
        wrapper_params.extend([f"%{search}%", f"%{search}%"])

    filter_sql = ""
    if where_clauses:
        filter_sql = " WHERE " + " AND ".join(where_clauses)

    # Final Combined Query
    combined_query = f"SELECT * FROM ({full_subquery}){filter_sql}"

    # ============================
    # 3. STATS & COUNTERS
    # ============================
    stats_sql = f"""
        SELECT 
            COUNT(*) AS total_records,
            COALESCE(SUM(area_hectares), 0) AS total_area,
            COALESCE(SUM(estimated_yield_tons), 0) AS total_yield
        FROM ({combined_query})
    """
    stats_row = db.execute(stats_sql, wrapper_params).fetchone()
    
    total_records = stats_row["total_records"] if stats_row else 0
    total_area = round(stats_row["total_area"], 2) if stats_row else 0.0
    total_yield = round(stats_row["total_yield"], 2) if stats_row else 0.0

    # ============================
    # 4. PAGINATED DATA FETCHING
    # ============================
    data_sql = combined_query + " ORDER BY farmer_name ASC LIMIT ? OFFSET ?"
    data_params = wrapper_params + [per_page, offset]
    
    records = db.execute(data_sql, data_params).fetchall()
    
    # Calculate total pages
    total_pages = math.ceil(total_records / per_page) if total_records > 0 else 1

    # Fetch Municipalities list for Filter Dropdown
    muni_sql = """
        SELECT DISTINCT name FROM (
            SELECT municipality AS name FROM wet_farmers
            UNION
            SELECT municipality AS name FROM dry_farmers
        ) WHERE name IS NOT NULL AND name != '' ORDER BY name ASC
    """
    municipalities_list = [row["name"] for row in db.execute(muni_sql).fetchall()]

    # ============================
    # 5. RENDER TEMPLATE
    # ============================
    return render_template(
        "report.html",
        records=records,
        stats={
            "total_records": total_records,
            "total_area": total_area,
            "total_yield": total_yield
        },
        pagination={
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_records": total_records,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        filters={
            "season": season,
            "municipality": municipality,
            "search": search
        },
        municipalities_list=municipalities_list
    )