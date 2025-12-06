import sys
import os
import unittest
from datetime import datetime
from sqlmodel import Session

# Add current directory to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, init_db
from backend.models import Scenario, Asset, IncomeSource, GeneralEquityDetails, TaxWrapper
from backend.simulation import run_simple_bond_simulation
from backend.tax_engine import calculate_taxes, TaxableIncomeBreakdown
from backend.tax_config import FilingStatus
from .test_helpers import cleanup_test_scenarios

class TestSimulationIntegration(unittest.TestCase):
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

    def test_simulation_tax_integration(self):
        scenario = Scenario(
            name=f"Tax Sim Test {datetime.now().isoformat()}",
            current_age=60,
            retirement_age=61,
            end_age=62, # Short run
            inflation_rate=0.0,
            bond_return_rate=0.0,
            annual_contribution_pre_retirement=0,
            annual_spending_in_retirement=100000
        )
        self.session.add(scenario)
        self.session.commit()
        self.session.refresh(scenario)

        # 1. Taxable Asset (100k value, 50k basis) -> 50% gain ratio
        asset_taxable = Asset(
            scenario_id=scenario.id,
            name="Taxable Brokerage",
            type="general_equity",
            current_balance=100000
        )
        self.session.add(asset_taxable)
        self.session.commit()
        self.session.refresh(asset_taxable)
        
        ge_detail_taxable = GeneralEquityDetails(
            asset_id=asset_taxable.id,
            account_type="taxable",
            account_balance=100000,
            tax_wrapper=TaxWrapper.TAXABLE,
            cost_basis=50000
        )
        self.session.add(ge_detail_taxable)

        # 2. Traditional IRA
        asset_ira = Asset(
            scenario_id=scenario.id,
            name="Traditional IRA",
            type="general_equity",
            current_balance=100000
        )
        self.session.add(asset_ira)
        self.session.commit()
        self.session.refresh(asset_ira)
        
        ge_detail_ira = GeneralEquityDetails(
            asset_id=asset_ira.id,
            account_type="ira",
            account_balance=100000,
            tax_wrapper=TaxWrapper.TRADITIONAL,
            cost_basis=100000
        )
        self.session.add(ge_detail_ira)

        # 3. Income Sources (Drawdowns)
        # Draw 20k from Taxable -> 10k LTCG, 10k Exempt
        # Draw 30k from IRA -> 30k Ordinary
        
        src_taxable = IncomeSource(
            scenario_id=scenario.id,
            name="Draw from Taxable",
            amount=20000,
            start_age=60,
            end_age=65,
            source_type="drawdown",
            linked_asset_id=asset_taxable.id
        )
        self.session.add(src_taxable)
        
        src_ira = IncomeSource(
            scenario_id=scenario.id,
            name="Draw from IRA",
            amount=30000,
            start_age=60,
            end_age=65,
            source_type="drawdown",
            linked_asset_id=asset_ira.id
        )
        self.session.add(src_ira)
        self.session.commit()
        
        result = run_simple_bond_simulation(self.session, scenario.id)
        
        # Analyze Year 1 (Age 60)
        idx = 0
        
        # Verify Taxes were calculated
        fed_tax = result['tax_simulation']['federal_tax'][idx]
        state_tax = result['tax_simulation']['state_tax'][idx]
        total_tax = result['tax_simulation']['total_tax'][idx]
        
        self.assertGreater(total_tax, 0)
        self.assertGreater(fed_tax, 0)
        self.assertGreater(state_tax, 0)
        
        # Verify Net Cash Flow
        net_cash_flow = result['net_cash_flow'][idx]
        expected_gross = 50000
        expected_net = expected_gross - total_tax
        
        # Floating point tolerance
        self.assertLess(abs(net_cash_flow - expected_net), 1.0)

if __name__ == "__main__":
    unittest.main()
