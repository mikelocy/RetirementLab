"""
Minimal regression test for RSU value conservation.

This test verifies that when RSU shares vest:
1. Unvested value decreases correctly
2. Vested holdings are created and tracked
3. Total assets decrease only by taxes (not by vested amount)
4. Gross income includes RSU vesting income
"""
import unittest
from datetime import datetime
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import Scenario, Asset, Security, RSUGrantDetails, RSUVestingTranche
from backend.schemas import ScenarioCreate, AssetCreate, RSUGrantDetailsCreate, RSUVestingTrancheCreate, SecurityCreate
from backend import crud, simulation


class TestRSUValueConservation(unittest.TestCase):
    def setUp(self):
        """Set up a minimal test scenario with RSU grant."""
        self.session = next(get_session())
        
        # Create scenario
        scenario_data = ScenarioCreate(
            name="RSU Test Scenario",
            current_age=50,
            base_year=2025,
            retirement_age=65,
            end_age=55,  # Only run through 2027 (second vest year)
            inflation_rate=0.02,
            bond_return_rate=0.0,  # No growth for simplicity
            annual_contribution_pre_retirement=0,
            annual_spending_in_retirement=0,
            filing_status="MARRIED_FILING_JOINTLY"
        )
        self.scenario = crud.create_scenario(self.session, scenario_data)
        
        # Create security (KLAC)
        security_data = SecurityCreate(
            symbol="KLAC",
            name="KLA Corporation",
            assumed_appreciation_rate=0.0  # No appreciation for test
        )
        self.security = crud.create_security(self.session, security_data)
        
        # Create cash asset ($100,000)
        cash_asset = AssetCreate(
            name="Cash Account",
            type="cash",
            current_balance=100000.0,
            cash_details={"balance": 100000.0}
        )
        self.cash_asset = crud.create_typed_asset(self.session, self.scenario.id, cash_asset)
        
        # Create RSU grant
        rsu_asset = AssetCreate(
            name="KLAC RSU",
            type="rsu_grant",
            rsu_grant_details=RSUGrantDetailsCreate(
                security_id=self.security.id,
                grant_date=datetime(2025, 1, 1),
                grant_value=200000.0,
                grant_fmv_at_grant=1000.0,
                shares_granted=200.0,
                vesting_tranches=[
                    RSUVestingTrancheCreate(
                        vesting_date=datetime(2026, 1, 1),
                        percentage_of_grant=0.5
                    ),
                    RSUVestingTrancheCreate(
                        vesting_date=datetime(2027, 1, 1),
                        percentage_of_grant=0.5
                    )
                ]
            )
        )
        self.rsu_asset = crud.create_typed_asset(self.session, self.scenario.id, rsu_asset)
        
        self.session.commit()
    
    def tearDown(self):
        """Clean up test data."""
        # Delete in reverse order of dependencies
        self.session.delete(self.rsu_asset)
        self.session.delete(self.cash_asset)
        self.session.delete(self.security)
        self.session.delete(self.scenario)
        self.session.commit()
        self.session.close()
    
    def test_rsu_value_conservation(self):
        """Test that RSU value is conserved through vesting."""
        # Run simulation with debug enabled
        result = simulation.run_simple_bond_simulation(
            self.session, 
            self.scenario.id, 
            debug=True
        )
        
        self.assertIsNotNone(result)
        self.assertIn("debug_trace", result)
        
        debug_trace = result["debug_trace"]
        self.assertGreater(len(debug_trace), 0)
        
        # Find RSU asset ID in trace
        rsu_asset_id = self.rsu_asset.id
        
        # Year 2025 (Age 50) - Before first vest
        year_2025 = next((t for t in debug_trace if t["year"] == 2025), None)
        self.assertIsNotNone(year_2025)
        self.assertIn(rsu_asset_id, year_2025["rsu"])
        
        rsu_2025 = year_2025["rsu"][rsu_asset_id]
        self.assertEqual(rsu_2025["unvested_shares_start"], 200.0)
        self.assertEqual(rsu_2025["unvested_value_start"], 200000.0)  # 200 shares * $1000
        self.assertEqual(rsu_2025["shares_vested_this_year"], 0.0)
        self.assertEqual(rsu_2025["vested_holding_value_end"], 0.0)
        
        # Year 2026 (Age 51) - First vest (50%)
        year_2026 = next((t for t in debug_trace if t["year"] == 2026), None)
        self.assertIsNotNone(year_2026)
        self.assertIn(rsu_asset_id, year_2026["rsu"])
        
        rsu_2026 = year_2026["rsu"][rsu_asset_id]
        self.assertEqual(rsu_2026["shares_vested_this_year"], 100.0)  # 50% of 200
        self.assertEqual(rsu_2026["fmv_at_vest"], 1000.0)  # No appreciation
        self.assertEqual(rsu_2026["vested_value_this_year"], 100000.0)  # 100 shares * $1000
        self.assertEqual(rsu_2026["unvested_shares_end"], 100.0)  # 200 - 100
        
        # Check that unvested value decreased
        unvested_drop = rsu_2025["unvested_value_start"] - rsu_2026["unvested_value_end"]
        self.assertAlmostEqual(unvested_drop, 100000.0, delta=1.0)
        
        # After 2026: vested holdings should have 100 shares worth $100,000 (FMV at vest, no appreciation)
        self.assertEqual(rsu_2026["vested_holding_shares_end"], 100.0, 
                        "Vested holdings should have 100 shares after first vest")
        self.assertAlmostEqual(rsu_2026["vested_holding_value_end"], 100000.0, delta=1.0,
                              msg="Vested holdings should be worth $100k (100 shares * $1000 FMV at vest)")
        
        # Check income includes RSU vesting
        self.assertEqual(year_2026["income"]["rsu_ordinary_income"], 100000.0)
        self.assertEqual(year_2026["income"]["gross_income_total"], 100000.0)
        
        # Check that total assets decreased only by taxes (not by full vested amount)
        # Total assets should be: cash + unvested_RSU + vested_holdings - taxes_paid
        # Start: $100k cash + $200k RSU = $300k
        # End: $100k cash - taxes + $100k unvested_RSU + $100k vested = $300k - taxes
        assets_start = year_2026["asset_totals"]["total_assets_start"]
        assets_end = year_2026["asset_totals"]["total_assets_end"]
        asset_change = assets_start - assets_end
        taxes_paid = year_2026["tax"]["total_tax"]
        
        # Asset change should be approximately equal to taxes only (within tolerance)
        # The vested value should transfer from RSU to holdings, so only taxes reduce total assets
        self.assertAlmostEqual(asset_change, taxes_paid, delta=100.0,
                              msg=f"Assets should decrease only by taxes. Change: ${asset_change:,.2f}, Taxes: ${taxes_paid:,.2f}")
        
        # Year 2027 (Age 52) - Second vest (remaining 50%)
        year_2027 = next((t for t in debug_trace if t["year"] == 2027), None)
        self.assertIsNotNone(year_2027)
        self.assertIn(rsu_asset_id, year_2027["rsu"])
        
        rsu_2027 = year_2027["rsu"][rsu_asset_id]
        self.assertEqual(rsu_2027["shares_vested_this_year"], 100.0)
        self.assertEqual(rsu_2027["unvested_shares_end"], 0.0)  # All vested
        
        # Check income includes RSU vesting
        self.assertEqual(year_2027["income"]["rsu_ordinary_income"], 100000.0)
        self.assertEqual(year_2027["income"]["gross_income_total"], 100000.0)
        
        # After both vests, unvested should be 0
        self.assertEqual(rsu_2027["unvested_value_end"], 0.0)
        
        # After 2027: vested holdings should have 200 shares worth $200,000 (FMV at vest, no appreciation)
        self.assertEqual(rsu_2027["vested_holding_shares_end"], 200.0,
                        "Vested holdings should have 200 shares after second vest")
        self.assertAlmostEqual(rsu_2027["vested_holding_value_end"], 200000.0, delta=1.0,
                              msg="Vested holdings should be worth $200k (200 shares * $1000 FMV at vest)")
        
        print("\n=== Test Results ===")
        print(f"Year 2025: Unvested start = ${rsu_2025['unvested_value_start']:,.2f}")
        print(f"Year 2026: Vested this year = ${rsu_2026['vested_value_this_year']:,.2f}, "
              f"Unvested end = ${rsu_2026['unvested_value_end']:,.2f}, "
              f"Vested holding = ${rsu_2026['vested_holding_value_end']:,.2f}")
        print(f"Year 2027: Vested this year = ${rsu_2027['vested_value_this_year']:,.2f}, "
              f"Unvested end = ${rsu_2027['unvested_value_end']:,.2f}, "
              f"Vested holding = ${rsu_2027['vested_holding_value_end']:,.2f}")
        print(f"Year 2026 Income: Gross = ${year_2026['income']['gross_income_total']:,.2f}, "
              f"RSU = ${year_2026['income']['rsu_ordinary_income']:,.2f}")
        print(f"Year 2026 Taxes: Total = ${year_2026['tax']['total_tax']:,.2f}")
        print(f"Year 2026 Assets: Start = ${year_2026['asset_totals']['total_assets_start']:,.2f}, "
              f"End = ${year_2026['asset_totals']['total_assets_end']:,.2f}, "
              f"Change = ${year_2026['asset_totals']['total_assets_start'] - year_2026['asset_totals']['total_assets_end']:,.2f}")


if __name__ == "__main__":
    unittest.main()

