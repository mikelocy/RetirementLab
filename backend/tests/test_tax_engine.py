import unittest
from backend.tax_engine import calculate_taxes, TaxableIncomeBreakdown
from backend.tax_config import FilingStatus

class TestTaxEngine(unittest.TestCase):
    
    def test_simple_ordinary_income(self):
        """
        Test basic scenario: $100k ordinary income, MFJ, CA.
        Should have Federal Ordinary Tax and State Tax.
        """
        breakdown = TaxableIncomeBreakdown(
            ordinary_income=100000.0,
            long_term_cap_gains=0.0,
            qualified_dividends=0.0,
            tax_exempt_income=0.0
        )
        
        result = calculate_taxes(
            year=2024,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
            state="CA",
            breakdown=breakdown
        )
        
        # Assertions
        self.assertGreater(result.total_tax, 0)
        self.assertGreater(result.federal_ordinary_tax, 0)
        self.assertEqual(result.federal_ltcg_tax, 0) # No LTCG
        self.assertGreater(result.state_tax, 0)
        
        # Check rates are sane (0% to 50%)
        self.assertGreater(result.effective_total_rate, 0.0)
        self.assertLess(result.effective_total_rate, 0.50)

    def test_ltcg_only_scenario(self):
        """
        Test scenario: $0 ordinary, $50k LTCG.
        Federal Ordinary should be 0.
        Federal LTCG should be > 0 (if bracket allows) or 0 if low enough.
        State Tax should be > 0 because CA taxes CG as ordinary.
        """
        breakdown = TaxableIncomeBreakdown(
            ordinary_income=0.0,
            long_term_cap_gains=100000.0, # High enough to hit 15% fed bracket
            qualified_dividends=0.0,
            tax_exempt_income=0.0
        )
        
        result = calculate_taxes(
            year=2024,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
            state="CA",
            breakdown=breakdown
        )
        
        self.assertEqual(result.federal_ordinary_tax, 0.0)
        self.assertGreater(result.federal_ltcg_tax, 0.0)
        self.assertGreater(result.state_tax, 0.0)

    def test_mixed_income_scenario(self):
        """
        Test mix of Ordinary, LTCG, and Exempt.
        Exempt income should lower the effective total rate.
        """
        breakdown = TaxableIncomeBreakdown(
            ordinary_income=80000.0,
            long_term_cap_gains=20000.0,
            qualified_dividends=5000.0,
            tax_exempt_income=50000.0 # Big Roth withdrawal
        )
        
        result = calculate_taxes(
            year=2024,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
            state="CA",
            breakdown=breakdown
        )
        
        self.assertGreater(result.federal_ordinary_tax, 0)
        self.assertGreater(result.state_tax, 0)
        
        # Total Gross = 80k + 20k + 5k + 50k = 155k
        # Taxable Gross = 105k
        
        # Effective Total Rate (Total Tax / 155k) should be lower than 
        # (Total Tax / 105k) - demonstrating that exempt income dilutes the rate.
        
        effective_rate_on_taxable = result.total_tax / (breakdown.ordinary_income + breakdown.long_term_cap_gains + breakdown.qualified_dividends)
        self.assertLess(result.effective_total_rate, effective_rate_on_taxable)

if __name__ == "__main__":
    unittest.main()

