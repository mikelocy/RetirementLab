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

class TestRothTaxTreatment(unittest.TestCase):
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

    def test_roth_withdrawals_are_tax_free(self):
        """Verify that ROTH IRA withdrawals result in $0 tax liability"""
        scenario = Scenario(
            name=f"Roth Test {datetime.now().isoformat()}",
            current_age=60,
            retirement_age=60,  # Already retired
            end_age=61,
            inflation_rate=0.0,
            bond_return_rate=0.0,
            annual_contribution_pre_retirement=0,
            annual_spending_in_retirement=0  # No spending, just withdrawals
        )
        self.session.add(scenario)
        self.session.commit()
        self.session.refresh(scenario)

        # Create ROTH IRA asset
        asset_roth = Asset(
            scenario_id=scenario.id,
            name="Roth IRA",
            type="general_equity",
            current_balance=100000
        )
        self.session.add(asset_roth)
        self.session.commit()
        self.session.refresh(asset_roth)
        
        ge_detail_roth = GeneralEquityDetails(
            asset_id=asset_roth.id,
            account_type="roth",
            account_balance=100000,
            tax_wrapper=TaxWrapper.ROTH,
            cost_basis=100000
        )
        self.session.add(ge_detail_roth)

        # Create drawdown from ROTH
        src_roth = IncomeSource(
            scenario_id=scenario.id,
            name="Roth Withdrawal",
            amount=50000,  # $50k withdrawal
            start_age=60,
            end_age=65,
            source_type="drawdown",
            linked_asset_id=asset_roth.id
        )
        self.session.add(src_roth)
        self.session.commit()
        
        # Run simulation
        result = run_simple_bond_simulation(self.session, scenario.id)
        
        # Check Year 1 (Age 60)
        idx = 0
        
        # Verify taxes are ZERO
        fed_tax = result['tax_simulation']['federal_tax'][idx]
        state_tax = result['tax_simulation']['state_tax'][idx]
        total_tax = result['tax_simulation']['total_tax'][idx]
        
        self.assertEqual(fed_tax, 0.0, "Federal tax should be $0 for ROTH withdrawal")
        self.assertEqual(state_tax, 0.0, "State tax should be $0 for ROTH withdrawal")
        self.assertEqual(total_tax, 0.0, "Total tax should be $0 for ROTH withdrawal")
        
        # Verify net cash flow equals gross (no tax deducted)
        net_cash_flow = result['net_cash_flow'][idx]
        # Net should equal gross since tax is 0
        # Gross = 50k (ROTH withdrawal), Net = 50k - 0 = 50k
        self.assertEqual(net_cash_flow, 50000.0, "Net cash flow should equal gross for tax-free ROTH withdrawal")

    def test_roth_mixed_with_taxable_income(self):
        """Verify that ROTH withdrawals don't increase tax when mixed with taxable income"""
        # Test: $30k Traditional IRA + $20k ROTH = should only tax the $30k
        
        breakdown = TaxableIncomeBreakdown(
            ordinary_income=30000.0,  # Traditional IRA withdrawal
            long_term_cap_gains=0.0,
            qualified_dividends=0.0,
            tax_exempt_income=20000.0  # ROTH withdrawal
        )
        
        tax_result = calculate_taxes(
            year=2024,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
            state="CA",
            breakdown=breakdown
        )
        
        # Tax should only be on the $30k ordinary income, NOT on the $20k ROTH
        # $30k - $29.2k standard deduction = $800 taxable
        # Should have some tax (even if small)
        self.assertGreater(tax_result.total_tax, 0, "Should have tax on the $30k traditional withdrawal")
        
        # Now test with ONLY the $30k (no ROTH) - tax should be the SAME
        breakdown_no_roth = TaxableIncomeBreakdown(
            ordinary_income=30000.0,
            long_term_cap_gains=0.0,
            qualified_dividends=0.0,
            tax_exempt_income=0.0
        )
        
        tax_result_no_roth = calculate_taxes(
            year=2024,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
            state="CA",
            breakdown=breakdown_no_roth
        )
        
        # Tax should be IDENTICAL whether ROTH is included or not
        self.assertEqual(tax_result.total_tax, tax_result_no_roth.total_tax, 
                        "Tax should be identical - ROTH withdrawal should not affect tax calculation")

if __name__ == "__main__":
    unittest.main()
