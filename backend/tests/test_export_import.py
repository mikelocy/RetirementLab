import sys
import os
import unittest
import json
from datetime import datetime
from sqlmodel import Session, select

# Add current directory to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, init_db
from backend.models import Scenario, Asset, IncomeSource, RealEstateDetails, GeneralEquityDetails, TaxWrapper
from backend.export_import import export_scenario, import_scenario

class TestExportImport(unittest.TestCase):
    def setUp(self):
        # Use a separate test DB or re-initialize
        # For simplicity in this setup, we'll just init_db.
        # In a real app, use a dedicated test db file or in-memory sqlite.
        
        # FORCE DELETE DB
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "retirement_lab_v3.db")
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                pass
        init_db()
        self.session = Session(engine)

    def tearDown(self):
        self.session.close()

    def test_export_import_flow(self):
        # 1. Create Test Scenario
        scenario = Scenario(
            name=f"Export Test {datetime.now().isoformat()}",
            current_age=50,
            retirement_age=65,
            end_age=90,
            inflation_rate=0.03,
            bond_return_rate=0.04,
            annual_contribution_pre_retirement=10000,
            annual_spending_in_retirement=50000
        )
        self.session.add(scenario)
        self.session.commit()
        self.session.refresh(scenario)

        # 2. Create Assets
        # Asset A: Real Estate (no tax wrapper)
        asset_re = Asset(
            scenario_id=scenario.id,
            name="Test House",
            type="real_estate",
            current_balance=500000
        )
        self.session.add(asset_re)
        self.session.commit()
        self.session.refresh(asset_re)
        
        re_detail = RealEstateDetails(
            asset_id=asset_re.id,
            property_value=500000,
            property_type="primary"
        )
        self.session.add(re_detail)

        # Asset B: General Equity (Taxable Brokerage)
        asset_ge = Asset(
            scenario_id=scenario.id,
            name="Taxable Brokerage",
            type="general_equity",
            current_balance=100000
        )
        self.session.add(asset_ge)
        self.session.commit()
        self.session.refresh(asset_ge)

        ge_detail = GeneralEquityDetails(
            asset_id=asset_ge.id,
            account_type="taxable",
            account_balance=100000,
            tax_wrapper=TaxWrapper.TAXABLE,
            cost_basis=80000  # $20k unrealized gains
        )
        self.session.add(ge_detail)

        # Asset C: General Equity (Roth IRA)
        asset_roth = Asset(
            scenario_id=scenario.id,
            name="Roth IRA",
            type="general_equity",
            current_balance=50000
        )
        self.session.add(asset_roth)
        self.session.commit()
        self.session.refresh(asset_roth)

        roth_detail = GeneralEquityDetails(
            asset_id=asset_roth.id,
            account_type="roth",
            account_balance=50000,
            tax_wrapper=TaxWrapper.ROTH,
            cost_basis=50000
        )
        self.session.add(roth_detail)
        self.session.commit()

        # 4. Export
        export_data = export_scenario(self.session, scenario.id)
        
        # 4b. SIMULATE JSON ROUNDTRIP (Convert Datetimes to Strings)
        # This mimics what happens in the FastAPI route: Pydantic -> JSON -> Dict
        # Pydantic's .dict() kept datetimes as objects, but the API would serialize them.
        # To test the import fix, we must ensure created_at/updated_at are strings in the input dict.
        
        # We can also just use json dumps/loads with a default serializer for datetime
        json_str = json.dumps(export_data, default=str)
        import_data = json.loads(json_str)

        # Verify export data structure
        self.assertEqual(len(import_data["assets"]), 3)
        
        # 5. Import
        new_name = f"Imported Copy {datetime.now().isoformat()}"
        new_id = import_scenario(self.session, import_data, new_name=new_name)
        
        # 6. Verify Import
        new_scenario = self.session.get(Scenario, new_id)
        self.assertIsNotNone(new_scenario)
        self.assertIsNotNone(new_scenario.created_at)
        self.assertIsNotNone(new_scenario.updated_at)
        # Ensure the new timestamps are valid datetime objects (SQLModel default behavior)
        self.assertIsInstance(new_scenario.created_at, datetime)

        new_assets = self.session.exec(select(Asset).where(Asset.scenario_id == new_id)).all()
        self.assertEqual(len(new_assets), 3)
        
        # Verify Taxable Asset
        new_ge = next(a for a in new_assets if a.name == "Taxable Brokerage")
        new_ge_details = self.session.exec(select(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == new_ge.id)).first()
        self.assertEqual(new_ge_details.tax_wrapper, TaxWrapper.TAXABLE)
        self.assertEqual(new_ge_details.cost_basis, 80000)
        
        # Verify Roth Asset
        new_roth = next(a for a in new_assets if a.name == "Roth IRA")
        new_roth_details = self.session.exec(select(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == new_roth.id)).first()
        self.assertEqual(new_roth_details.tax_wrapper, TaxWrapper.ROTH)

if __name__ == "__main__":
    unittest.main()
