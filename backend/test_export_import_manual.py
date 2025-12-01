import sys
import os

# Add current directory to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.database import engine, init_db
from backend.models import Scenario, Asset, IncomeSource, RealEstateDetails
from backend.export_import import export_scenario, import_scenario
from datetime import datetime

def run_test():
    print("Initializing DB...")
    init_db()
    
    with Session(engine) as session:
        # 1. Create Test Scenario
        print("Creating Test Scenario...")
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
        session.add(scenario)
        session.commit()
        session.refresh(scenario)
        print(f"Created Scenario ID: {scenario.id}")

        # 2. Create Asset
        asset = Asset(
            scenario_id=scenario.id,
            name="Test House",
            type="real_estate",
            current_balance=500000
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        
        re_detail = RealEstateDetails(
            asset_id=asset.id,
            property_value=500000,
            property_type="primary"
        )
        session.add(re_detail)
        
        # 3. Create Income Source linked to Asset
        income = IncomeSource(
            scenario_id=scenario.id,
            name="Rental Income",
            amount=12000,
            start_age=50,
            end_age=90,
            source_type="drawdown",
            linked_asset_id=asset.id
        )
        session.add(income)
        session.commit()
        
        print("Scenario populated.")

        # 4. Export
        print("Exporting...")
        export_data = export_scenario(session, scenario.id)
        # print("Export Data:", export_data)
        
        assert export_data["scenario"]["name"] == scenario.name
        assert len(export_data["assets"]) == 1
        assert len(export_data["income_sources"]) == 1
        assert export_data["income_sources"][0]["linked_asset_id"] == asset.id
        
        # 5. Import
        print("Importing copy...")
        new_name = f"Imported Copy {datetime.now().isoformat()}"
        new_id = import_scenario(session, export_data, new_name=new_name)
        print(f"Imported Scenario ID: {new_id}")
        
        # 6. Verify
        new_scenario = session.get(Scenario, new_id)
        assert new_scenario.name == new_name
        
        new_assets = session.exec(select(Asset).where(Asset.scenario_id == new_id)).all()
        assert len(new_assets) == 1
        new_asset = new_assets[0]
        assert new_asset.name == "Test House"
        assert new_asset.id != asset.id
        
        new_incomes = session.exec(select(IncomeSource).where(IncomeSource.scenario_id == new_id)).all()
        assert len(new_incomes) == 1
        new_income = new_incomes[0]
        
        # Verify ID mapping worked
        assert new_income.linked_asset_id == new_asset.id
        assert new_income.linked_asset_id != asset.id
        
        print("SUCCESS: Export/Import verified relationships preserved.")

if __name__ == "__main__":
    run_test()

