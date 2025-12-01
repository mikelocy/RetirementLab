from typing import Dict, Any, List, Optional
from sqlmodel import Session, select
from .models import Scenario, Asset, IncomeSource, RealEstateDetails, GeneralEquityDetails, SpecificStockDetails

def export_scenario(session: Session, scenario_id: int) -> Dict[str, Any]:
    """
    Export a scenario and all its related data to a dictionary.
    """
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        raise ValueError(f"Scenario with ID {scenario_id} not found")

    # 1. Export Scenario Core
    scenario_data = scenario.dict()
    
    # 2. Export Assets
    # We need to fetch assets and their specific details
    assets_data = []
    assets = session.exec(select(Asset).where(Asset.scenario_id == scenario_id)).all()
    
    for asset in assets:
        asset_dict = asset.dict()
        
        # Fetch details based on type
        if asset.type == "real_estate":
            if asset.real_estate_details:
                asset_dict["real_estate_details"] = asset.real_estate_details.dict()
        elif asset.type == "general_equity":
            if asset.general_equity_details:
                asset_dict["general_equity_details"] = asset.general_equity_details.dict()
        elif asset.type == "specific_stock":
            if asset.specific_stock_details:
                asset_dict["specific_stock_details"] = asset.specific_stock_details.dict()
                
        assets_data.append(asset_dict)

    # 3. Export Income Sources
    income_sources_data = []
    income_sources = session.exec(select(IncomeSource).where(IncomeSource.scenario_id == scenario_id)).all()
    for source in income_sources:
        income_sources_data.append(source.dict())

    return {
        "version": "1.0",
        "scenario": scenario_data,
        "assets": assets_data,
        "income_sources": income_sources_data
    }

def import_scenario(session: Session, data: Dict[str, Any], new_name: Optional[str] = None) -> int:
    """
    Import a scenario from a dictionary.
    Returns the ID of the newly created scenario.
    """
    scenario_data = data.get("scenario", {})
    
    # remove ID to ensure new creation
    if "id" in scenario_data:
        del scenario_data["id"]
        
    if new_name:
        scenario_data["name"] = new_name
        
    # Create Scenario
    # Filter out unknown fields for forward compatibility
    valid_scenario_fields = Scenario.__fields__.keys()
    filtered_scenario_data = {k: v for k, v in scenario_data.items() if k in valid_scenario_fields}
    
    # Remove datetime fields so SQLModel can set defaults
    for ts_field in ("created_at", "updated_at"):
        filtered_scenario_data.pop(ts_field, None)
    
    new_scenario = Scenario(**filtered_scenario_data)
    session.add(new_scenario)
    session.commit()
    session.refresh(new_scenario)
    
    new_scenario_id = new_scenario.id
    
    # Track ID mapping for relationships
    # old_asset_id -> new_asset_id
    asset_id_map = {}
    
    # Import Assets
    assets_list = data.get("assets", [])
    for asset_raw in assets_list:
        old_id = asset_raw.get("id")
        
        # Prepare base asset data
        valid_asset_fields = Asset.__fields__.keys()
        filtered_asset_data = {k: v for k, v in asset_raw.items() if k in valid_asset_fields and k != "id"}
        filtered_asset_data["scenario_id"] = new_scenario_id
        
        new_asset = Asset(**filtered_asset_data)
        session.add(new_asset)
        session.commit()
        session.refresh(new_asset)
        
        if old_id is not None:
            asset_id_map[old_id] = new_asset.id
            
        # Import Details
        asset_type = new_asset.type
        
        if asset_type == "real_estate" and "real_estate_details" in asset_raw:
            details_data = asset_raw["real_estate_details"]
            if details_data:
                valid_fields = RealEstateDetails.__fields__.keys()
                filtered_details = {k: v for k, v in details_data.items() if k in valid_fields and k != "id"}
                filtered_details["asset_id"] = new_asset.id
                
                details = RealEstateDetails(**filtered_details)
                session.add(details)
                
        elif asset_type == "general_equity" and "general_equity_details" in asset_raw:
            details_data = asset_raw["general_equity_details"]
            if details_data:
                valid_fields = GeneralEquityDetails.__fields__.keys()
                filtered_details = {k: v for k, v in details_data.items() if k in valid_fields and k != "id"}
                filtered_details["asset_id"] = new_asset.id
                
                details = GeneralEquityDetails(**filtered_details)
                session.add(details)

        elif asset_type == "specific_stock" and "specific_stock_details" in asset_raw:
            details_data = asset_raw["specific_stock_details"]
            if details_data:
                valid_fields = SpecificStockDetails.__fields__.keys()
                filtered_details = {k: v for k, v in details_data.items() if k in valid_fields and k != "id"}
                filtered_details["asset_id"] = new_asset.id
                
                details = SpecificStockDetails(**filtered_details)
                session.add(details)
        
        session.commit()

    # Import Income Sources
    income_list = data.get("income_sources", [])
    for income_raw in income_list:
        valid_income_fields = IncomeSource.__fields__.keys()
        filtered_income = {k: v for k, v in income_raw.items() if k in valid_income_fields and k != "id"}
        filtered_income["scenario_id"] = new_scenario_id
        
        # Fix linked_asset_id
        old_linked_id = filtered_income.get("linked_asset_id")
        if old_linked_id is not None:
            if old_linked_id in asset_id_map:
                filtered_income["linked_asset_id"] = asset_id_map[old_linked_id]
            else:
                # Asset not found (maybe wasn't exported or ID mismatch), unlink it to be safe
                filtered_income["linked_asset_id"] = None
        
        new_income = IncomeSource(**filtered_income)
        session.add(new_income)
    
    session.commit()
    
    return new_scenario_id
