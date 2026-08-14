from database import get_db


conn = get_db()
c = conn.cursor()


print("=== DRY ASSOCIATIONS ===")

for row in c.execute("""
    SELECT 
        da.id,
        da.name AS association,
        dm.name AS municipality
    FROM dry_associations da
    LEFT JOIN dry_municipalities dm
    ON dm.id = da.municipality_id
"""):
    print(dict(row))



print("\n=== DRY FARMERS COUNT PER ASSOCIATION ===")

for row in c.execute("""
    SELECT 
        da.id,
        da.name AS association,
        dm.name AS municipality,
        COUNT(df.id) AS farmers
    FROM dry_associations da
    LEFT JOIN dry_municipalities dm
    ON dm.id = da.municipality_id
    LEFT JOIN dry_farmers df
    ON df.association_id = da.id
    GROUP BY da.id, da.name, dm.name
"""):
    print(dict(row))



print("\n=== DRY FARMERS SAMPLE ===")

for row in c.execute("""
    SELECT *
    FROM dry_farmers
    LIMIT 5
"""):
    print(dict(row))


conn.close()
