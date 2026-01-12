"""
Migration script to add created_at and updated_at columns to detail tables.

This adds the columns to:
- rsugrantdetails
- rsuvestingtranche
- generalequitydetails
- specificstockdetails
- realestatedetails
- cashdetails

SQLite doesn't support ALTER TABLE ADD COLUMN in all versions, so we use a workaround.
"""

import sqlite3
import os
from datetime import datetime

# Get database path
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
db_path = os.path.join(project_root, "retirement_lab_v3.db")

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}. It will be created on next server start.")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tables that need created_at and updated_at columns
tables_to_migrate = [
    "rsugrantdetails",
    "rsuvestingtranche",
    "generalequitydetails",
    "specificstockdetails",
    "realestatedetails",
    "cashdetails"
]

default_time = datetime.utcnow().isoformat()

for table_name in tables_to_migrate:
    try:
        # Check if columns already exist
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        has_created_at = "created_at" in columns
        has_updated_at = "updated_at" in columns
        
        if has_created_at and has_updated_at:
            print(f"{table_name}: Columns already exist. Skipping.")
            continue
        
        print(f"Adding created_at and updated_at columns to {table_name} table...")
        
        # SQLite 3.25.0+ supports ALTER TABLE ADD COLUMN
        try:
            if not has_created_at:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN created_at TIMESTAMP")
                print(f"  Added created_at column")
            
            if not has_updated_at:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TIMESTAMP")
                print(f"  Added updated_at column")
            
            # Set default values for existing rows
            if not has_created_at:
                cursor.execute(f"UPDATE {table_name} SET created_at = ? WHERE created_at IS NULL", (default_time,))
            if not has_updated_at:
                cursor.execute(f"UPDATE {table_name} SET updated_at = ? WHERE updated_at IS NULL", (default_time,))
            
            print(f"{table_name}: Migration completed successfully!")
            
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"{table_name}: Columns already exist (detected via error). Skipping.")
            else:
                print(f"{table_name}: ALTER TABLE failed: {e}")
                print(f"  Skipping {table_name} - you may need to recreate the table manually")
    
    except Exception as e:
        print(f"Error migrating {table_name}: {e}")
        continue

try:
    conn.commit()
    print("\nAll migrations completed!")
except Exception as e:
    print(f"\nError committing changes: {e}")
    conn.rollback()
finally:
    conn.close()

