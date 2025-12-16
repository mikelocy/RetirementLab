"""
Migration script to add base_year column to Scenario table.
Run this once to update the existing database schema.
"""
import sqlite3
import os
from datetime import datetime

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
    cursor.execute("PRAGMA table_info(scenario)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "base_year" not in columns:
        print("Adding base_year column...")
        current_year = datetime.now().year
        cursor.execute(f"""
            ALTER TABLE scenario 
            ADD COLUMN base_year INTEGER DEFAULT {current_year}
        """)
        # Update existing rows to have current year as default
        cursor.execute(f"""
            UPDATE scenario 
            SET base_year = {current_year} 
            WHERE base_year IS NULL
        """)
        print(f"Added base_year column with default value {current_year}")
    else:
        print("base_year column already exists")
        # Update any NULL values to current year
        current_year = datetime.now().year
        cursor.execute(f"""
            UPDATE scenario 
            SET base_year = {current_year} 
            WHERE base_year IS NULL
        """)
        updated = cursor.rowcount
        if updated > 0:
            print(f"Updated {updated} scenarios with NULL base_year to {current_year}")
    
    conn.commit()
    print("\nMigration completed successfully!")
    
except sqlite3.Error as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

