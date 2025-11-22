from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from typing import List

from .database import init_db, get_session
from .models import Scenario, Asset
from .schemas import ScenarioCreate, ScenarioRead, AssetCreate, AssetRead
from . import crud, simulation

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/scenarios", response_model=List[ScenarioRead])
def read_scenarios(session: Session = Depends(get_session)):
    return crud.get_scenarios(session)

@app.post("/api/scenarios", response_model=ScenarioRead)
def create_scenario(scenario: ScenarioCreate, session: Session = Depends(get_session)):
    return crud.create_scenario(session, scenario)

@app.get("/api/scenarios/{scenario_id}", response_model=ScenarioRead)
def read_scenario(scenario_id: int, session: Session = Depends(get_session)):
    scenario = crud.get_scenario(session, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario

@app.put("/api/scenarios/{scenario_id}", response_model=ScenarioRead)
def update_scenario(scenario_id: int, scenario: ScenarioCreate, session: Session = Depends(get_session)):
    updated_scenario = crud.update_scenario(session, scenario_id, scenario)
    if not updated_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return updated_scenario

@app.get("/api/scenarios/{scenario_id}/assets", response_model=List[AssetRead])
def read_assets(scenario_id: int, session: Session = Depends(get_session)):
    return crud.get_assets_for_scenario(session, scenario_id)

@app.post("/api/scenarios/{scenario_id}/assets", response_model=AssetRead)
def create_asset(scenario_id: int, asset: AssetCreate, session: Session = Depends(get_session)):
    scenario = crud.get_scenario(session, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return crud.create_typed_asset(session, scenario_id, asset)

@app.put("/api/assets/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: int, asset: AssetCreate, session: Session = Depends(get_session)):
    updated_asset = crud.update_typed_asset(session, asset_id, asset)
    if not updated_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return updated_asset

@app.delete("/api/assets/{asset_id}")
def delete_asset(asset_id: int, session: Session = Depends(get_session)):
    deleted_asset = crud.delete_asset(session, asset_id)
    if not deleted_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"status": "deleted", "id": asset_id}

@app.get("/api/scenarios/{scenario_id}/simulate/simple-bond")
def run_simulation(scenario_id: int, session: Session = Depends(get_session)):
    result = simulation.run_simple_bond_simulation(session, scenario_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scenario not found or simulation failed")
    return result
