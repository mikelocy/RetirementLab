"""
Migration script to rename tax_withholding_rate to estimated_share_withholding_rate
in RSU grant tables.
Run this once to update the existing database schema.
"""
import sqlite3
import os

# Get the project root directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
db_file = os.path.join(project_root, "retirement_lab_v3.db")

if not os.path.exists(db_file):
    print(f"Database file not found: {db_file}")
    exit(1)

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

try:
    # Check if old column exists and new column doesn't
    cursor.execute("PRAGMA table_info(rsugrantdetails)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "tax_withholding_rate" in columns and "estimated_share_withholding_rate" not in columns:
        print("Renaming tax_withholding_rate to estimated_share_withholding_rate in rsugrantdetails...")
        cursor.execute("""
            ALTER TABLE rsugrantdetails 
            RENAME COLUMN tax_withholding_rate TO estimated_share_withholding_rate
        """)
        print("Renamed column in rsugrantdetails")
    elif "estimated_share_withholding_rate" in columns:
        print("estimated_share_withholding_rate column already exists in rsugrantdetails")
    else:
        print("tax_withholding_rate column not found in rsugrantdetails (may have been migrated already)")
    
    # Check RSUGrantForecast table
    cursor.execute("PRAGMA table_info(rsugrantforecast)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "tax_withholding_rate" in columns and "estimated_share_withholding_rate" not in columns:
        print("Renaming tax_withholding_rate to estimated_share_withholding_rate in rsugrantforecast...")
        cursor.execute("""
            ALTER TABLE rsugrantforecast 
            RENAME COLUMN tax_withholding_rate TO estimated_share_withholding_rate
        """)
        print("Renamed column in rsugrantforecast")
    elif "estimated_share_withholding_rate" in columns:
        print("estimated_share_withholding_rate column already exists in rsugrantforecast")
    else:
        print("tax_withholding_rate column not found in rsugrantforecast (may have been migrated already)")
    
    conn.commit()
    print("\nMigration completed successfully!")
    
except sqlite3.Error as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

