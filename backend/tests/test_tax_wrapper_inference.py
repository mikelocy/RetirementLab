import sys
import os
import unittest
from datetime import datetime
from sqlmodel import Session

# Add current directory to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from backend.database import engine, init_db
from backend.models import Scenario, Asset, GeneralEquityDetails, TaxWrapper
from backend.crud import create_typed_asset, update_typed_asset
from backend.schemas import AssetCreate, GeneralEquityDetailsCreate
from .test_helpers import cleanup_test_scenarios

class TestTaxWrapperInference(unittest.TestCase):
    def setUp(self):
        # Initialize DB (don't delete - preserve user scenarios)
        init_db()
        self.session = Session(engine)
        # Clean up any leftover test scenarios from previous runs
        cleanup_test_scenarios(self.session)

    def tearDown(self):
        # Clean up test scenarios created during this test run
        cleanup_test_scenarios(self.session)
        self.session.close()

    def test_roth_account_type_infers_roth_tax_wrapper(self):
        """Verify that creating an asset with account_type='roth' sets tax_wrapper to ROTH"""
        scenario = Scenario(
            name=f"Test {datetime.now().isoformat()}",
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

        # Create asset with account_type="roth" but NO tax_wrapper field
        asset_data = AssetCreate(
            name="Roth IRA",
            type="general_equity",
            general_equity_details=GeneralEquityDetailsCreate(
                account_type="roth",  # Frontend sends this
                account_balance=100000,
                expected_return_rate=0.07,
                fee_rate=0.0
                # tax_wrapper NOT provided - should be inferred
            )
        )
        
        created_asset = create_typed_asset(self.session, scenario.id, asset_data)
        
        # Verify tax_wrapper was inferred correctly
        ge_detail = self.session.exec(
            select(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == created_asset.id)
        ).first()
        
        self.assertEqual(ge_detail.tax_wrapper, TaxWrapper.ROTH, 
                        "tax_wrapper should be inferred as ROTH when account_type is 'roth'")

    def test_ira_account_type_infers_traditional_tax_wrapper(self):
        """Verify that account_type='ira' sets tax_wrapper to TRADITIONAL"""
        scenario = Scenario(
            name=f"Test {datetime.now().isoformat()}",
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

        asset_data = AssetCreate(
            name="Traditional IRA",
            type="general_equity",
            general_equity_details=GeneralEquityDetailsCreate(
                account_type="ira",
                account_balance=100000
            )
        )
        
        created_asset = create_typed_asset(self.session, scenario.id, asset_data)
        ge_detail = self.session.exec(
            select(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == created_asset.id)
        ).first()
        
        self.assertEqual(ge_detail.tax_wrapper, TaxWrapper.TRADITIONAL)

if __name__ == "__main__":
    unittest.main()

