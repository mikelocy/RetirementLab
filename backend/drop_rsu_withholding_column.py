"""
Migration script to drop estimated_share_withholding_rate column from RSU grant tables.
SQLite doesn't support DROP COLUMN directly, so we recreate the tables without the column.
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
    # Check if column exists in rsugrantdetails
    cursor.execute("PRAGMA table_info(rsugrantdetails)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "estimated_share_withholding_rate" in columns:
        print("Dropping estimated_share_withholding_rate column from rsugrantdetails...")
        
        # SQLite doesn't support DROP COLUMN, so we need to recreate the table
        # First, get the current table structure
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='rsugrantdetails'")
        old_sql = cursor.fetchone()
        
        # Create new table without the column
        cursor.execute("""
            CREATE TABLE rsugrantdetails_new (
                id INTEGER PRIMARY KEY,
                asset_id INTEGER NOT NULL,
                employer TEXT,
                security_id INTEGER NOT NULL,
                grant_date TIMESTAMP NOT NULL,
                grant_value_type TEXT NOT NULL DEFAULT 'dollar_value',
                grant_value REAL NOT NULL,
                grant_fmv_at_grant REAL NOT NULL,
                shares_granted REAL NOT NULL,
                FOREIGN KEY(asset_id) REFERENCES asset(id),
                FOREIGN KEY(security_id) REFERENCES security(id)
            )
        """)
        
        # Copy data (excluding the dropped column)
        cursor.execute("""
            INSERT INTO rsugrantdetails_new 
            (id, asset_id, employer, security_id, grant_date, grant_value_type, grant_value, grant_fmv_at_grant, shares_granted)
            SELECT id, asset_id, employer, security_id, grant_date, grant_value_type, grant_value, grant_fmv_at_grant, shares_granted
            FROM rsugrantdetails
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE rsugrantdetails")
        cursor.execute("ALTER TABLE rsugrantdetails_new RENAME TO rsugrantdetails")
        
        print("Dropped column from rsugrantdetails")
    else:
        print("estimated_share_withholding_rate column not found in rsugrantdetails (may have been migrated already)")
    
    # Check RSUGrantForecast table
    cursor.execute("PRAGMA table_info(rsugrantforecast)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "estimated_share_withholding_rate" in columns:
        print("Dropping estimated_share_withholding_rate column from rsugrantforecast...")
        
        # Create new table without the column
        cursor.execute("""
            CREATE TABLE rsugrantforecast_new (
                id INTEGER PRIMARY KEY,
                scenario_id INTEGER NOT NULL,
                security_id INTEGER NOT NULL,
                first_grant_date TIMESTAMP NOT NULL,
                grant_frequency TEXT NOT NULL DEFAULT 'annual',
                grant_value REAL NOT NULL,
                vesting_schedule_years INTEGER NOT NULL DEFAULT 4,
                vesting_cliff_years REAL NOT NULL DEFAULT 1.0,
                vesting_frequency TEXT NOT NULL DEFAULT 'quarterly',
                FOREIGN KEY(scenario_id) REFERENCES scenario(id),
                FOREIGN KEY(security_id) REFERENCES security(id)
            )
        """)
        
        # Copy data (excluding the dropped column)
        cursor.execute("""
            INSERT INTO rsugrantforecast_new 
            (id, scenario_id, security_id, first_grant_date, grant_frequency, grant_value, vesting_schedule_years, vesting_cliff_years, vesting_frequency)
            SELECT id, scenario_id, security_id, first_grant_date, grant_frequency, grant_value, vesting_schedule_years, vesting_cliff_years, vesting_frequency
            FROM rsugrantforecast
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE rsugrantforecast")
        cursor.execute("ALTER TABLE rsugrantforecast_new RENAME TO rsugrantforecast")
        
        print("Dropped column from rsugrantforecast")
    else:
        print("estimated_share_withholding_rate column not found in rsugrantforecast (may have been migrated already)")
    
    conn.commit()
    print("\nMigration completed successfully!")
    
except sqlite3.Error as e:
    print(f"Error: {e}")
    conn.rollback()
    raise
finally:
    conn.close()

