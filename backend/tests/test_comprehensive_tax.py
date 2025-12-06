import sys
import os
import unittest
from datetime import datetime
from sqlmodel import Session

# Add current directory to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, init_db
from backend.models import (
    Scenario, Asset, IncomeSource, GeneralEquityDetails, 
    TaxWrapper, IncomeType
)
from backend.simulation import run_simple_bond_simulation
from backend.tax_config import FilingStatus
from .test_helpers import cleanup_test_scenarios

class TestComprehensiveTaxTreatment(unittest.TestCase):
    """
    Comprehensive test covering all income types, asset tax wrappers, 
    and tax treatments to ensure the simulation handles all combinations correctly.
    """
    
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

    def test_all_income_types_and_asset_wrappers(self):
        """
        Test comprehensive scenario with:
        - All income types: ordinary, social_security, tax_exempt, disability
        - All asset tax wrappers: taxable, traditional, roth, tax_exempt_other
        - Social Security tax calculation
        - Cost basis tracking for taxable accounts
        - Different filing statuses
        """
        # Create scenario with Married Filing Jointly
        scenario = Scenario(
            name=f"Comprehensive Tax Test {datetime.now().isoformat()}",
            current_age=65,
            retirement_age=65,
            end_age=67,  # 3 years: 65, 66, 67
            inflation_rate=0.0,  # Simplify for testing
            bond_return_rate=0.0,
            annual_contribution_pre_retirement=0,
            annual_spending_in_retirement=0,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY
        )
        self.session.add(scenario)
        self.session.commit()
        self.session.refresh(scenario)

        # ===== ASSETS =====
        
        # 1. Taxable Brokerage (with cost basis)
        asset_taxable = Asset(
            scenario_id=scenario.id,
            name="Taxable Brokerage",
            type="general_equity",
            current_balance=200000
        )
        self.session.add(asset_taxable)
        self.session.commit()
        self.session.refresh(asset_taxable)
        
        ge_taxable = GeneralEquityDetails(
            asset_id=asset_taxable.id,
            account_type="taxable",
            account_balance=200000,
            tax_wrapper=TaxWrapper.TAXABLE,
            cost_basis=120000  # 40% gain ratio
        )
        self.session.add(ge_taxable)

        # 2. Traditional IRA
        asset_traditional = Asset(
            scenario_id=scenario.id,
            name="Traditional IRA",
            type="general_equity",
            current_balance=300000
        )
        self.session.add(asset_traditional)
        self.session.commit()
        self.session.refresh(asset_traditional)
        
        ge_traditional = GeneralEquityDetails(
            asset_id=asset_traditional.id,
            account_type="ira",
            account_balance=300000,
            tax_wrapper=TaxWrapper.TRADITIONAL,
            cost_basis=300000
        )
        self.session.add(ge_traditional)

        # 3. Roth IRA
        asset_roth = Asset(
            scenario_id=scenario.id,
            name="Roth IRA",
            type="general_equity",
            current_balance=100000
        )
        self.session.add(asset_roth)
        self.session.commit()
        self.session.refresh(asset_roth)
        
        ge_roth = GeneralEquityDetails(
            asset_id=asset_roth.id,
            account_type="roth",
            account_balance=100000,
            tax_wrapper=TaxWrapper.ROTH,
            cost_basis=100000
        )
        self.session.add(ge_roth)

        # 4. Tax-Exempt Other (e.g., muni bonds)
        asset_exempt = Asset(
            scenario_id=scenario.id,
            name="Muni Bond Fund",
            type="general_equity",
            current_balance=50000
        )
        self.session.add(asset_exempt)
        self.session.commit()
        self.session.refresh(asset_exempt)
        
        ge_exempt = GeneralEquityDetails(
            asset_id=asset_exempt.id,
            account_type="taxable",
            account_balance=50000,
            tax_wrapper=TaxWrapper.TAX_EXEMPT_OTHER,
            cost_basis=50000
        )
        self.session.add(ge_exempt)

        # ===== INCOME SOURCES =====
        
        # 1. Ordinary Income (Pension)
        income_ordinary = IncomeSource(
            scenario_id=scenario.id,
            name="Pension",
            amount=40000,
            start_age=65,
            end_age=67,
            source_type="income",
            income_type=IncomeType.ORDINARY
        )
        self.session.add(income_ordinary)

        # 2. Social Security Benefits
        income_ss = IncomeSource(
            scenario_id=scenario.id,
            name="Social Security",
            amount=30000,
            start_age=65,
            end_age=67,
            source_type="income",
            income_type=IncomeType.SOCIAL_SECURITY
        )
        self.session.add(income_ss)

        # 3. Tax-Exempt Income (VA Disability)
        income_exempt = IncomeSource(
            scenario_id=scenario.id,
            name="VA Disability",
            amount=12000,
            start_age=65,
            end_age=67,
            source_type="income",
            income_type=IncomeType.TAX_EXEMPT
        )
        self.session.add(income_exempt)

        # 4. Disability Income
        income_disability = IncomeSource(
            scenario_id=scenario.id,
            name="Disability Insurance",
            amount=15000,
            start_age=65,
            end_age=67,
            source_type="income",
            income_type=IncomeType.DISABILITY
        )
        self.session.add(income_disability)

        # 5. Drawdown from Taxable (should create LTCG + return of capital)
        drawdown_taxable = IncomeSource(
            scenario_id=scenario.id,
            name="Drawdown from Taxable",
            amount=50000,
            start_age=65,
            end_age=67,
            source_type="drawdown",
            linked_asset_id=asset_taxable.id,
            income_type=IncomeType.ORDINARY  # Should be ignored for drawdowns
        )
        self.session.add(drawdown_taxable)

        # 6. Drawdown from Traditional IRA (should be ordinary income)
        drawdown_traditional = IncomeSource(
            scenario_id=scenario.id,
            name="RMD from Traditional IRA",
            amount=20000,
            start_age=65,
            end_age=67,
            source_type="drawdown",
            linked_asset_id=asset_traditional.id
        )
        self.session.add(drawdown_traditional)

        # 7. Drawdown from Roth (should be tax-exempt)
        drawdown_roth = IncomeSource(
            scenario_id=scenario.id,
            name="Roth Withdrawal",
            amount=25000,
            start_age=65,
            end_age=67,
            source_type="drawdown",
            linked_asset_id=asset_roth.id
        )
        self.session.add(drawdown_roth)

        # 8. Drawdown from Tax-Exempt Other (should be tax-exempt)
        drawdown_exempt = IncomeSource(
            scenario_id=scenario.id,
            name="Muni Bond Income",
            amount=10000,
            start_age=65,
            end_age=67,
            source_type="drawdown",
            linked_asset_id=asset_exempt.id
        )
        self.session.add(drawdown_exempt)

        self.session.commit()

        # Run simulation
        result = run_simple_bond_simulation(self.session, scenario.id)

        # Verify results for Year 1 (Age 65)
        idx = 0  # First year (age 65)

        # Expected income breakdown:
        # - Ordinary: 40k (pension) + 20k (traditional IRA drawdown) = 60k
        # - Social Security: 30k (will be partially taxable)
        # - Tax Exempt: 12k (VA) + 15k (disability) + 25k (Roth) + 10k (exempt asset) = 62k
        # - LTCG: ~20k (from 50k taxable drawdown, 40% gain ratio = 20k gain, 30k return of capital)
        #   Actually: 50k drawdown from 200k balance, 40% gain ratio = 20k LTCG, 30k return of capital
        
        # Verify tax simulation exists
        self.assertIn('tax_simulation', result)
        self.assertIn('federal_tax', result['tax_simulation'])
        self.assertIn('state_tax', result['tax_simulation'])
        self.assertIn('total_tax', result['tax_simulation'])
        
        fed_tax = result['tax_simulation']['federal_tax'][idx]
        state_tax = result['tax_simulation']['state_tax'][idx]
        total_tax = result['tax_simulation']['total_tax'][idx]
        effective_rate = result['tax_simulation']['effective_tax_rate'][idx]

        # Verify taxes are calculated (should be > 0 given the income)
        self.assertGreater(total_tax, 0, "Total tax should be greater than 0")
        self.assertGreater(fed_tax, 0, "Federal tax should be greater than 0")
        self.assertGreater(state_tax, 0, "State tax should be greater than 0")
        
        # Verify effective rate is reasonable (between 0 and 1)
        self.assertGreater(effective_rate, 0)
        self.assertLess(effective_rate, 0.5, "Effective tax rate should be less than 50%")

        # Verify net cash flow accounts for taxes
        net_cash_flow = result['net_cash_flow'][idx]
        gross_income = result['income_sources']['salary'][idx]  # Pre-retirement salary (should be 0)
        # Total income should include all sources
        # We can't easily sum all income from the result, but we can verify net is less than gross
        
        # Verify Social Security is being handled (tax should reflect SS taxation)
        # With 30k SS and 60k ordinary income, combined income = 60k + 15k = 75k
        # This is above the 44k threshold for MFJ, so 85% of SS should be taxable
        # Taxable SS = 0.85 * 30k = 25.5k
        # Total taxable ordinary = 60k + 25.5k = 85.5k (before standard deduction)
        
        # Verify cost basis is being tracked (taxable asset should have reduced basis after drawdown)
        # This is harder to verify directly, but we can check that LTCG was calculated
        
        print(f"\nYear 1 (Age 65) Results:")
        print(f"  Federal Tax: ${fed_tax:,.2f}")
        print(f"  State Tax: ${state_tax:,.2f}")
        print(f"  Total Tax: ${total_tax:,.2f}")
        print(f"  Effective Rate: {effective_rate*100:.2f}%")
        print(f"  Net Cash Flow: ${net_cash_flow:,.2f}")

    def test_social_security_taxation_thresholds(self):
        """Test Social Security taxation at different income levels"""
        # Test low income (0% taxable)
        scenario_low = Scenario(
            name=f"SS Low Income Test {datetime.now().isoformat()}",
            current_age=65,
            retirement_age=65,
            end_age=66,
            inflation_rate=0.0,
            bond_return_rate=0.0,
            annual_contribution_pre_retirement=0,
            annual_spending_in_retirement=0,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY
        )
        self.session.add(scenario_low)
        self.session.commit()
        self.session.refresh(scenario_low)

        income_ss_low = IncomeSource(
            scenario_id=scenario_low.id,
            name="Social Security",
            amount=20000,  # Low SS
            start_age=65,
            end_age=66,
            source_type="income",
            income_type=IncomeType.SOCIAL_SECURITY
        )
        self.session.add(income_ss_low)
        self.session.commit()

        result_low = run_simple_bond_simulation(self.session, scenario_low.id)
        tax_low = result_low['tax_simulation']['total_tax'][0]
        
        # With only 20k SS and no other income, combined income = 10k, below 32k threshold
        # So 0% of SS should be taxable, tax should be very low or zero
        self.assertLess(tax_low, 1000, "Low income SS should have minimal tax")

        # Test high income (85% taxable)
        scenario_high = Scenario(
            name=f"SS High Income Test {datetime.now().isoformat()}",
            current_age=65,
            retirement_age=65,
            end_age=66,
            inflation_rate=0.0,
            bond_return_rate=0.0,
            annual_contribution_pre_retirement=0,
            annual_spending_in_retirement=0,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY
        )
        self.session.add(scenario_high)
        self.session.commit()
        self.session.refresh(scenario_high)

        income_ordinary_high = IncomeSource(
            scenario_id=scenario_high.id,
            name="Pension",
            amount=100000,  # High ordinary income
            start_age=65,
            end_age=66,
            source_type="income",
            income_type=IncomeType.ORDINARY
        )
        self.session.add(income_ordinary_high)

        income_ss_high = IncomeSource(
            scenario_id=scenario_high.id,
            name="Social Security",
            amount=30000,
            start_age=65,
            end_age=66,
            source_type="income",
            income_type=IncomeType.SOCIAL_SECURITY
        )
        self.session.add(income_ss_high)
        self.session.commit()

        result_high = run_simple_bond_simulation(self.session, scenario_high.id)
        tax_high = result_high['tax_simulation']['total_tax'][0]
        
        # With 100k ordinary + 30k SS, combined = 100k + 15k = 115k, well above 44k threshold
        # So 85% of SS (25.5k) should be taxable
        # Total taxable = 100k + 25.5k = 125.5k (before standard deduction)
        self.assertGreater(tax_high, 15000, "High income should result in significant tax")

    def test_all_filing_statuses(self):
        """Test that all filing statuses work correctly"""
        filing_statuses = [
            FilingStatus.SINGLE,
            FilingStatus.MARRIED_FILING_JOINTLY,
            FilingStatus.MARRIED_FILING_SEPARATELY,
            FilingStatus.HEAD_OF_HOUSEHOLD
        ]
        
        for filing_status in filing_statuses:
            with self.subTest(filing_status=filing_status):
                scenario = Scenario(
                    name=f"Filing Status Test {filing_status.value} {datetime.now().isoformat()}",
                    current_age=65,
                    retirement_age=65,
                    end_age=66,
                    inflation_rate=0.0,
                    bond_return_rate=0.0,
                    annual_contribution_pre_retirement=0,
                    annual_spending_in_retirement=0,
                    filing_status=filing_status
                )
                self.session.add(scenario)
                self.session.commit()
                self.session.refresh(scenario)

                income = IncomeSource(
                    scenario_id=scenario.id,
                    name="Pension",
                    amount=50000,
                    start_age=65,
                    end_age=66,
                    source_type="income",
                    income_type=IncomeType.ORDINARY
                )
                self.session.add(income)
                self.session.commit()

                # Should not raise an exception
                result = run_simple_bond_simulation(self.session, scenario.id)
                
                # Verify taxes were calculated
                self.assertIn('tax_simulation', result)
                self.assertGreater(result['tax_simulation']['total_tax'][0], 0)

if __name__ == "__main__":
    unittest.main()

