import json
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, init_db
from sqlmodel import Session, text
from backend.export_import import import_scenario

# Check if filing_status column exists, if not add it
print("Checking database schema...")
session = Session(engine)
try:
    # Check if column exists
    result = session.exec(text("PRAGMA table_info(scenario)"))
    columns = [row[1] for row in result]
    
    if 'filing_status' not in columns:
        print("Adding filing_status column to scenario table...")
        session.exec(text("ALTER TABLE scenario ADD COLUMN filing_status TEXT DEFAULT 'MARRIED_FILING_JOINTLY'"))
        session.commit()
        print("Column added successfully")
    else:
        print("filing_status column already exists")
finally:
    session.close()

# Ensure all other tables exist
init_db()

# Read the export file
with open('scenario_export.json', 'r') as f:
    export_data = json.load(f)

# Add filing_status to scenario if it doesn't exist
if 'filing_status' not in export_data['scenario']:
    export_data['scenario']['filing_status'] = 'married_filing_jointly'
    print("Added filing_status: married_filing_jointly to scenario")

# Import the scenario
session = Session(engine)
try:
    new_id = import_scenario(session, export_data)
    print(f"Successfully imported scenario with new ID: {new_id}")
    session.commit()
except Exception as e:
    print(f"Error importing scenario: {e}")
    session.rollback()
    raise
finally:
    session.close()

