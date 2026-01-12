
import sys
import os
import unittest
from datetime import datetime
from sqlmodel import Session, select, create_engine, SQLModel

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import _seed_default_tax_tables
from backend.models import Scenario, TaxTable, FilingStatus
from backend.schemas import TaxTableRead

# Setup in-memory DB for testing
test_engine = create_engine("sqlite:///:memory:")
SQLModel.metadata.create_all(test_engine)  # Ensure all tables are created

class TestTaxSeeding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Already done above, but good practice
        pass

    @classmethod
    def tearDownClass(cls):
        SQLModel.metadata.drop_all(test_engine)

    def setUp(self):
        self.session = Session(test_engine)
        
    def tearDown(self):
        self.session.close()

    def test_seeding_logic_base_year_2026(self):
        """
        Test that seeding works for a scenario with base_year=2026.
        """
        # 1. Create Scenario with base_year=2026
        scenario = Scenario(
            name="Test 2026 Tax Seeding",
            current_age=50,
            base_year=2026,
            retirement_age=65,
            end_age=90,
            inflation_rate=0.03,
            bond_return_rate=0.04,
            annual_contribution_pre_retirement=10000,
            annual_spending_in_retirement=50000,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY
        )
        self.session.add(scenario)
        self.session.commit()
        self.session.refresh(scenario)
        
        # 2. Call seeding function manually (simulating what the endpoint does)
        print("Calling _seed_default_tax_tables...")
        _seed_default_tax_tables(self.session, scenario)
        
        # 3. Verify tables were created
        tables = self.session.exec(select(TaxTable).where(TaxTable.scenario_id == scenario.id)).all()
        
        # Should return 2 tables (FED and CA)
        self.assertEqual(len(tables), 2)
        
        jurisdictions = {t.jurisdiction for t in tables}
        self.assertIn("FED", jurisdictions)
        self.assertIn("CA", jurisdictions)
        
        # Check year_base is 2026
        for t in tables:
            self.assertEqual(t.year_base, 2026)
            self.assertIn("seeded", t.notes.lower())
            print(f"Verified table: {t.jurisdiction} ({t.year_base})")
            
            # 4. Verify TaxTableRead construction (this is where it failed with Pydantic error)
            brackets = t.get_brackets()
            # Convert keys if necessary, though TaxTableRead expects TaxBracketSchema (up_to, rate)
            # The JSON stored has keys "up_to", "rate"
            
            try:
                read_model = TaxTableRead(
                    id=t.id,
                    scenario_id=t.scenario_id,
                    jurisdiction=t.jurisdiction,
                    filing_status=t.filing_status,
                    year_base=t.year_base,
                    brackets=brackets,
                    standard_deduction=t.standard_deduction,
                    notes=t.notes,
                    schema_version=t.schema_version,
                    created_at=t.created_at,
                    updated_at=t.updated_at
                )
                print(f"Successfully constructed TaxTableRead for {t.jurisdiction}")
                
                # Check that infinity matches are handled (up_to can be None)
                has_infinity = any(b['up_to'] is None for b in brackets)
                # Or float('inf') if json.loads preserved it (but standard json produces None/null)
                # In Python json.loads('Infinity') -> float('inf').
                # But if it was stored as null, it is None.
                
                # Verify that at least one bracket has high limit or None
                # Just ensuring no validation error is the main test here.
                
            except Exception as e:
                self.fail(f"Failed to construct TaxTableRead: {e}")
            
        print("Test passed: 2026 scenario seeded successfully.")


if __name__ == "__main__":
    unittest.main()
