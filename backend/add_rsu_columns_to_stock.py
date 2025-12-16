"""
Migration script to add source_type and source_rsu_grant_id columns to SpecificStockDetails table.
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
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(specificstockdetails)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "source_type" not in columns:
        print("Adding source_type column...")
        cursor.execute("""
            ALTER TABLE specificstockdetails 
            ADD COLUMN source_type TEXT DEFAULT 'user_entered'
        """)
        print("Added source_type column")
    else:
        print("source_type column already exists")
    
    if "source_rsu_grant_id" not in columns:
        print("Adding source_rsu_grant_id column...")
        cursor.execute("""
            ALTER TABLE specificstockdetails 
            ADD COLUMN source_rsu_grant_id INTEGER
        """)
        print("Added source_rsu_grant_id column")
    else:
        print("source_rsu_grant_id column already exists")
    
    conn.commit()
    print("\nMigration completed successfully!")
    
except sqlite3.Error as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

