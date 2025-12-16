"""
Migration script to add assumed_appreciation_rate column to Security table.
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
    # Check if column already exists
    cursor.execute("PRAGMA table_info(security)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "assumed_appreciation_rate" not in columns:
        print("Adding assumed_appreciation_rate column...")
        cursor.execute("""
            ALTER TABLE security 
            ADD COLUMN assumed_appreciation_rate REAL DEFAULT 0.0
        """)
        print("Added assumed_appreciation_rate column")
    else:
        print("assumed_appreciation_rate column already exists")
    
    conn.commit()
    print("\nMigration completed successfully!")
    
except sqlite3.Error as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

