from sqlmodel import Session, select, delete
from .models import Scenario, Asset, RealEstateDetails, GeneralEquityDetails, SpecificStockDetails, IncomeSource
from .schemas import ScenarioCreate, AssetCreate, RealEstateDetailsCreate, GeneralEquityDetailsCreate, SpecificStockDetailsCreate, IncomeSourceCreate
from datetime import datetime

def get_scenarios(session: Session):
    statement = select(Scenario)
    return session.exec(statement).all()

def get_scenario(session: Session, scenario_id: int):
    return session.get(Scenario, scenario_id)

def create_scenario(session: Session, scenario_create: ScenarioCreate):
    db_scenario = Scenario.from_orm(scenario_create)
    db_scenario.created_at = datetime.utcnow()
    db_scenario.updated_at = datetime.utcnow()
    session.add(db_scenario)
    session.commit()
    session.refresh(db_scenario)
    return db_scenario

def update_scenario(session: Session, scenario_id: int, scenario_update: ScenarioCreate):
    db_scenario = session.get(Scenario, scenario_id)
    if not db_scenario:
        return None
    scenario_data = scenario_update.dict(exclude_unset=True)
    for key, value in scenario_data.items():
        setattr(db_scenario, key, value)
    db_scenario.updated_at = datetime.utcnow()
    session.add(db_scenario)
    session.commit()
    session.refresh(db_scenario)
    return db_scenario

def delete_scenario(session: Session, scenario_id: int):
    try:
        scenario = session.get(Scenario, scenario_id)
        if not scenario:
            print(f"DEBUG: Scenario {scenario_id} not found in DB")
            return None
        
        print(f"DEBUG: Found scenario {scenario_id}, deleting assets...")
        
        # Get all asset IDs for this scenario
        asset_ids = session.exec(select(Asset.id).where(Asset.scenario_id == scenario_id)).all()
        
        if asset_ids:
            # Bulk delete details
            session.exec(delete(RealEstateDetails).where(RealEstateDetails.asset_id.in_(asset_ids)))
            session.exec(delete(GeneralEquityDetails).where(GeneralEquityDetails.asset_id.in_(asset_ids)))
            session.exec(delete(SpecificStockDetails).where(SpecificStockDetails.asset_id.in_(asset_ids)))
            
            # Bulk delete assets
            session.exec(delete(Asset).where(Asset.scenario_id == scenario_id))
            
        # Bulk delete income sources
        session.exec(delete(IncomeSource).where(IncomeSource.scenario_id == scenario_id))

        print(f"DEBUG: Deleting scenario object")
        session.delete(scenario)
        session.commit()
        print(f"DEBUG: Commit successful")
        return scenario
    except Exception as e:
        print(f"DEBUG: Exception in delete_scenario: {e}")
        session.rollback()
        raise e

def create_typed_asset(session: Session, scenario_id: int, asset_data: AssetCreate) -> Asset:
    try:
        # Determine type
        asset_type = asset_data.type
        
        # ... (logic)
        
        # Initialize current_balance based on type and details
        current_balance = 0.0
        if asset_type == "real_estate":
            assert asset_data.real_estate_details is not None, "Real estate details required"
            current_balance = asset_data.real_estate_details.property_value
        elif asset_type == "general_equity":
            assert asset_data.general_equity_details is not None, "General equity details required"
            current_balance = asset_data.general_equity_details.account_balance
        elif asset_type == "specific_stock":
            assert asset_data.specific_stock_details is not None, "Specific stock details required"
            current_balance = asset_data.specific_stock_details.shares_owned * asset_data.specific_stock_details.current_price
        else:
            current_balance = 0.0

        asset = Asset(
            scenario_id=scenario_id,
            name=asset_data.name,
            type=asset_type,
            current_balance=current_balance,
        )
        session.add(asset)
        session.flush()  # ensure asset.id is populated

        if asset_type == "real_estate" and asset_data.real_estate_details:
            re_details = RealEstateDetails(
                asset_id=asset.id,
                **asset_data.real_estate_details.dict()
            )
            session.add(re_details)
        elif asset_type == "general_equity" and asset_data.general_equity_details:
            ge_details = GeneralEquityDetails(
                asset_id=asset.id,
                **asset_data.general_equity_details.dict()
            )
            session.add(ge_details)
        elif asset_type == "specific_stock" and asset_data.specific_stock_details:
            stock_details = SpecificStockDetails(
                asset_id=asset.id,
                **asset_data.specific_stock_details.dict()
            )
            session.add(stock_details)

        session.commit()
        session.refresh(asset)
        return asset
    except Exception as e:
        print(f"DEBUG: Exception in create_typed_asset: {e}")
        session.rollback()
        raise e

def update_typed_asset(session: Session, asset_id: int, asset_data: AssetCreate) -> Asset:
    db_asset = session.get(Asset, asset_id)
    if not db_asset:
        return None
    
    # Update base fields
    db_asset.name = asset_data.name
    db_asset.type = asset_data.type
    
    # Update current_balance and nested details
    if db_asset.type == "real_estate":
        if not asset_data.real_estate_details:
            return None # validation error in real app
        
        # Update balance
        db_asset.current_balance = asset_data.real_estate_details.property_value
        
        # Update or create details
        if db_asset.real_estate_details:
            for key, value in asset_data.real_estate_details.dict().items():
                setattr(db_asset.real_estate_details, key, value)
            session.add(db_asset.real_estate_details)
        else:
            re_details = RealEstateDetails(
                asset_id=db_asset.id,
                **asset_data.real_estate_details.dict()
            )
            session.add(re_details)
            
        # Remove other type details if they exist (e.g. if type changed)
        if db_asset.general_equity_details:
            session.delete(db_asset.general_equity_details)
            
    elif db_asset.type == "general_equity":
        if not asset_data.general_equity_details:
            return None
            
        db_asset.current_balance = asset_data.general_equity_details.account_balance
        
        if db_asset.general_equity_details:
            for key, value in asset_data.general_equity_details.dict().items():
                setattr(db_asset.general_equity_details, key, value)
            session.add(db_asset.general_equity_details)
        else:
            ge_details = GeneralEquityDetails(
                asset_id=db_asset.id,
                **asset_data.general_equity_details.dict()
            )
            session.add(ge_details)
            
        if db_asset.real_estate_details:
            session.delete(db_asset.real_estate_details)
        if db_asset.specific_stock_details:
            session.delete(db_asset.specific_stock_details)

    elif db_asset.type == "specific_stock":
        if not asset_data.specific_stock_details:
            return None
        
        db_asset.current_balance = asset_data.specific_stock_details.shares_owned * asset_data.specific_stock_details.current_price
        
        if db_asset.specific_stock_details:
            for key, value in asset_data.specific_stock_details.dict().items():
                setattr(db_asset.specific_stock_details, key, value)
            session.add(db_asset.specific_stock_details)
        else:
            stock_details = SpecificStockDetails(
                asset_id=db_asset.id,
                **asset_data.specific_stock_details.dict()
            )
            session.add(stock_details)
            
        if db_asset.real_estate_details:
            session.delete(db_asset.real_estate_details)
        if db_asset.general_equity_details:
            session.delete(db_asset.general_equity_details)
            
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
    return db_asset

def delete_asset(session: Session, asset_id: int, commit: bool = True):
    # Direct delete without object loading
    try:
        session.exec(delete(RealEstateDetails).where(RealEstateDetails.asset_id == asset_id))
        session.exec(delete(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == asset_id))
        session.exec(delete(SpecificStockDetails).where(SpecificStockDetails.asset_id == asset_id))
        session.exec(delete(Asset).where(Asset.id == asset_id))
        if commit:
            session.commit()
        return True
    except Exception as e:
        print(f"DEBUG: Exception in delete_asset: {e}")
        if commit:
            session.rollback()
        raise e

def create_asset(session: Session, asset_create: AssetCreate, scenario_id: int):
    return create_typed_asset(session, scenario_id, asset_create)

def get_assets_for_scenario(session: Session, scenario_id: int):
    statement = select(Asset).where(Asset.scenario_id == scenario_id)
    return session.exec(statement).all()

def create_income_source(session: Session, income_source: IncomeSourceCreate, scenario_id: int):
    db_income_source = IncomeSource(scenario_id=scenario_id, **income_source.dict())
    session.add(db_income_source)
    session.commit()
    session.refresh(db_income_source)
    return db_income_source

def get_income_sources_for_scenario(session: Session, scenario_id: int):
    statement = select(IncomeSource).where(IncomeSource.scenario_id == scenario_id)
    return session.exec(statement).all()

def delete_income_source(session: Session, income_source_id: int):
    income_source = session.get(IncomeSource, income_source_id)
    if not income_source:
        return None
    session.delete(income_source)
    session.commit()
    return income_source

def update_income_source(session: Session, income_source_id: int, income_source_update: IncomeSourceCreate):
    db_income_source = session.get(IncomeSource, income_source_id)
    if not db_income_source:
        return None
    source_data = income_source_update.dict(exclude_unset=True)
    for key, value in source_data.items():
        setattr(db_income_source, key, value)
    session.add(db_income_source)
    session.commit()
    session.refresh(db_income_source)
    return db_income_source
