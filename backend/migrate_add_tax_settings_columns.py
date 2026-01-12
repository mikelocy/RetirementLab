"""
Migration script to add tax_table_indexing_policy and tax_table_custom_index_rate columns
to the taxfundingsettings table.

SQLite doesn't support ALTER TABLE ADD COLUMN in all versions, so we use a workaround:
1. Create new table with new columns
2. Copy data from old table
3. Drop old table
4. Rename new table to old name
"""

import sqlite3
import os

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
    cursor.execute("PRAGMA table_info(taxfundingsettings)")
    columns = [row[1] for row in cursor.fetchall()]
    
    has_indexing_policy = "tax_table_indexing_policy" in columns
    has_custom_rate = "tax_table_custom_index_rate" in columns
    
    if has_indexing_policy and has_custom_rate:
        print("Columns already exist. Migration not needed.")
        conn.close()
        exit(0)
    
    print("Adding missing columns to taxfundingsettings table...")
    
    # SQLite 3.25.0+ supports ALTER TABLE ADD COLUMN
    # Try the simple approach first
    try:
        if not has_indexing_policy:
            cursor.execute("ALTER TABLE taxfundingsettings ADD COLUMN tax_table_indexing_policy TEXT DEFAULT 'CONSTANT_NOMINAL'")
            print("Added tax_table_indexing_policy column")
        
        if not has_custom_rate:
            cursor.execute("ALTER TABLE taxfundingsettings ADD COLUMN tax_table_custom_index_rate REAL")
            print("Added tax_table_custom_index_rate column")
        
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
            cursor.execute("SELECT * FROM taxfundingsettings")
            rows = cursor.fetchall()
            old_columns = [desc[0] for desc in cursor.description]
            
            # Create new table with all columns
            cursor.execute("""
                CREATE TABLE taxfundingsettings_new (
                    id INTEGER PRIMARY KEY,
                    scenario_id INTEGER UNIQUE,
                    tax_funding_order_json TEXT,
                    allow_retirement_withdrawals_for_taxes BOOLEAN,
                    if_insufficient_funds_behavior TEXT,
                    tax_table_indexing_policy TEXT DEFAULT 'CONSTANT_NOMINAL',
                    tax_table_custom_index_rate REAL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY(scenario_id) REFERENCES scenario(id)
                )
            """)
            
            # Copy data
            for row in rows:
                row_dict = dict(zip(old_columns, row))
                cursor.execute("""
                    INSERT INTO taxfundingsettings_new 
                    (id, scenario_id, tax_funding_order_json, allow_retirement_withdrawals_for_taxes, 
                     if_insufficient_funds_behavior, tax_table_indexing_policy, tax_table_custom_index_rate, 
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row_dict.get('id'),
                    row_dict.get('scenario_id'),
                    row_dict.get('tax_funding_order_json'),
                    row_dict.get('allow_retirement_withdrawals_for_taxes'),
                    row_dict.get('if_insufficient_funds_behavior'),
                    'CONSTANT_NOMINAL',  # Default value
                    None,  # Default value
                    row_dict.get('created_at'),
                    row_dict.get('updated_at')
                ))
            
            # Replace old table
            cursor.execute("DROP TABLE taxfundingsettings")
            cursor.execute("ALTER TABLE taxfundingsettings_new RENAME TO taxfundingsettings")
            conn.commit()
            print("Migration completed successfully (via table recreation)!")

except Exception as e:
    print(f"Migration failed: {e}")
    conn.rollback()
    raise
finally:
    conn.close()

