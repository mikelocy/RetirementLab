import unittest
from backend.tax_config import (
    get_federal_ordinary_tax_table,
    get_federal_ltcg_tax_table,
    get_state_tax_table,
    FilingStatus,
    TaxTable
)

class TestTaxConfig(unittest.TestCase):
    
    def test_federal_ordinary_mfj_2024(self):
        """Test retrieving Federal Ordinary MFJ table for 2024"""
        table = get_federal_ordinary_tax_table(2024, FilingStatus.MARRIED_FILING_JOINTLY)
        self.assertIsInstance(table, TaxTable)
        self.assertGreater(table.standard_deduction, 0)
        self.assertGreater(len(table.brackets), 0)
        self.assertEqual(table.brackets[0].rate, 0.10)

    def test_federal_ltcg_mfj_2024(self):
        """Test retrieving Federal LTCG MFJ table for 2024"""
        table = get_federal_ltcg_tax_table(2024, FilingStatus.MARRIED_FILING_JOINTLY)
        self.assertIsInstance(table, TaxTable)
        # LTCG table defined with 0 standard deduction in config
        self.assertEqual(table.standard_deduction, 0.0) 
        self.assertGreater(len(table.brackets), 0)
        self.assertEqual(table.brackets[0].rate, 0.00)

    def test_state_ca_mfj_2024(self):
        """Test retrieving CA State table for 2024"""
        table = get_state_tax_table("CA", 2024, FilingStatus.MARRIED_FILING_JOINTLY)
        self.assertIsInstance(table, TaxTable)
        self.assertGreater(table.standard_deduction, 0)
        self.assertGreater(len(table.brackets), 0)

    def test_year_fallback(self):
        """Test that requesting a future year falls back to the latest configured year (2024)"""
        # Requesting 2030, should return 2024 data
        table_2030 = get_federal_ordinary_tax_table(2030, FilingStatus.MARRIED_FILING_JOINTLY)
        table_2024 = get_federal_ordinary_tax_table(2024, FilingStatus.MARRIED_FILING_JOINTLY)
        
        self.assertEqual(table_2030.standard_deduction, table_2024.standard_deduction)
        self.assertEqual(table_2030.brackets[0].up_to, table_2024.brackets[0].up_to)

    def test_unsupported_state(self):
        """Test that requesting an unsupported state raises NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            get_state_tax_table("NY", 2024, FilingStatus.MARRIED_FILING_JOINTLY)

    def test_unsupported_filing_status(self):
        """Test that all filing statuses are now supported"""
        # All filing statuses should work now
        for status in FilingStatus:
            table = get_state_tax_table("CA", 2024, status)
            self.assertIsNotNone(table)
            self.assertGreater(len(table.brackets), 0)

if __name__ == "__main__":
    unittest.main()

