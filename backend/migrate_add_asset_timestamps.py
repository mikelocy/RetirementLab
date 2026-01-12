"""
Migration script to add created_at and updated_at columns to the asset table.

SQLite doesn't support ALTER TABLE ADD COLUMN in all versions, so we use a workaround:
1. Create new table with new columns
2. Copy data from old table
3. Drop old table
4. Rename new table to old name
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

try:
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(asset)")
    columns = [row[1] for row in cursor.fetchall()]
    
    has_created_at = "created_at" in columns
    has_updated_at = "updated_at" in columns
    
    if has_created_at and has_updated_at:
        print("Columns already exist. Migration not needed.")
        conn.close()
        exit(0)
    
    print("Adding created_at and updated_at columns to asset table...")
    
    # SQLite 3.25.0+ supports ALTER TABLE ADD COLUMN
    # Try the simple approach first
    try:
        if not has_created_at:
            cursor.execute("ALTER TABLE asset ADD COLUMN created_at TIMESTAMP")
            print("Added created_at column")
        
        if not has_updated_at:
            cursor.execute("ALTER TABLE asset ADD COLUMN updated_at TIMESTAMP")
            print("Added updated_at column")
        
        # Set default values for existing rows
        default_time = datetime.utcnow().isoformat()
        cursor.execute("UPDATE asset SET created_at = ? WHERE created_at IS NULL", (default_time,))
        cursor.execute("UPDATE asset SET updated_at = ? WHERE updated_at IS NULL", (default_time,))
        
        conn.commit()
        print("Migration completed successfully!")
        
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Columns already exist (detected via error). Migration not needed.")
        else:
            print(f"ALTER TABLE failed: {e}")
            print("Trying table recreation method...")
            
            # Fallback: recreate table
            # Get all existing data
            cursor.execute("SELECT * FROM asset")
            rows = cursor.fetchall()
            old_columns = [desc[0] for desc in cursor.description]
            
            # Create new table with all columns
            cursor.execute("""
                CREATE TABLE asset_new (
                    id INTEGER PRIMARY KEY,
                    scenario_id INTEGER,
                    name TEXT,
                    type TEXT,
                    current_balance REAL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY(scenario_id) REFERENCES scenario(id)
                )
            """)
            
            # Copy data
            default_time = datetime.utcnow().isoformat()
            for row in rows:
                row_dict = dict(zip(old_columns, row))
                cursor.execute("""
                    INSERT INTO asset_new 
                    (id, scenario_id, name, type, current_balance, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row_dict.get('id'),
                    row_dict.get('scenario_id'),
                    row_dict.get('name'),
                    row_dict.get('type'),
                    row_dict.get('current_balance'),
                    default_time,  # Default value
                    default_time   # Default value
                ))
            
            # Replace old table
            cursor.execute("DROP TABLE asset")
            cursor.execute("ALTER TABLE asset_new RENAME TO asset")
            conn.commit()
            print("Migration completed successfully (via table recreation)!")

except Exception as e:
    print(f"Migration failed: {e}")
    conn.rollback()
    raise
finally:
    conn.close()

