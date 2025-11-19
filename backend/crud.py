from sqlmodel import Session, select
from .models import Scenario, Asset
from .schemas import ScenarioCreate, AssetCreate
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

def create_asset(session: Session, asset_create: AssetCreate, scenario_id: int):
    db_asset = Asset(**asset_create.dict(), scenario_id=scenario_id)
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
    return db_asset

def get_assets_for_scenario(session: Session, scenario_id: int):
    statement = select(Asset).where(Asset.scenario_id == scenario_id)
    return session.exec(statement).all()

