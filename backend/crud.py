from sqlmodel import Session, select
from .models import Scenario, Asset, RealEstateDetails, GeneralEquityDetails
from .schemas import ScenarioCreate, AssetCreate, RealEstateDetailsCreate, GeneralEquityDetailsCreate
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

def create_typed_asset(session: Session, scenario_id: int, asset_data: AssetCreate) -> Asset:
    # Determine type
    asset_type = asset_data.type

    # Initialize current_balance based on type and details
    current_balance = 0.0

    if asset_type == "real_estate":
        assert asset_data.real_estate_details is not None, "Real estate details required"
        current_balance = asset_data.real_estate_details.property_value
    elif asset_type == "general_equity":
        assert asset_data.general_equity_details is not None, "General equity details required"
        current_balance = asset_data.general_equity_details.account_balance
    else:
        # fallback for unknown types (for now, just 0)
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

    session.commit()
    session.refresh(asset)
    return asset

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
            
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
    return db_asset

def delete_asset(session: Session, asset_id: int):
    asset = session.get(Asset, asset_id)
    if not asset:
        return None
    
    # Cascade delete should happen if configured in DB, but SQLModel/SQLAlchemy 
    # usually needs explicit deletion or cascade configuration. 
    # For simplicity, we'll manually delete children if cascade isn't set up in SQL.
    if asset.real_estate_details:
        session.delete(asset.real_estate_details)
    if asset.general_equity_details:
        session.delete(asset.general_equity_details)
        
    session.delete(asset)
    session.commit()
    return asset

def create_asset(session: Session, asset_create: AssetCreate, scenario_id: int):
    return create_typed_asset(session, scenario_id, asset_create)

def get_assets_for_scenario(session: Session, scenario_id: int):
    statement = select(Asset).where(Asset.scenario_id == scenario_id)
    return session.exec(statement).all()
