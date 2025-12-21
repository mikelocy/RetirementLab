from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from typing import List, Dict, Any, Optional

from .database import init_db, get_session
from .models import Scenario, Asset, Security, RSUGrantForecast, TaxFundingSettings, TaxFundingSource, InsufficientFundsBehavior
# Import all models to ensure they're registered with SQLModel for table creation
from . import models  # noqa: F401
from .schemas import (
    ScenarioCreate, ScenarioRead, AssetCreate, AssetRead, IncomeSourceCreate, IncomeSourceRead,
    SecurityCreate, SecurityRead, RSUGrantForecastCreate, RSUGrantForecastRead,
    TaxFundingSettingsCreate, TaxFundingSettingsRead
)
from . import crud, simulation
from .export_import import export_scenario, import_scenario

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

@app.post("/api/scenarios/import")
def import_scenario_endpoint(
    data: Dict[str, Any] = Body(...),
    new_name: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Import a scenario from a JSON export. 
    Creates a new scenario with all related assets and income sources.
    """
    try:
        new_id = import_scenario(session, data, new_name)
        return {"new_scenario_id": new_id, "status": "imported"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@app.get("/api/scenarios/{scenario_id}", response_model=ScenarioRead)
def read_scenario(scenario_id: int, session: Session = Depends(get_session)):
    try:
        scenario = crud.get_scenario(session, scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return scenario
    except Exception as e:
        import traceback
        print(f"Error reading scenario: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error reading scenario: {str(e)}")

@app.get("/api/scenarios/{scenario_id}/export")
def export_scenario_endpoint(scenario_id: int, session: Session = Depends(get_session)):
    """
    Export a scenario and all related data to a JSON-compatible format.
    """
    try:
        return export_scenario(session, scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.put("/api/scenarios/{scenario_id}", response_model=ScenarioRead)
def update_scenario(scenario_id: int, scenario: ScenarioCreate, session: Session = Depends(get_session)):
    updated_scenario = crud.update_scenario(session, scenario_id, scenario)
    if not updated_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return updated_scenario

@app.delete("/api/scenarios/{scenario_id}")
def delete_scenario(scenario_id: int, session: Session = Depends(get_session)):
    print(f"DEBUG: Received delete request for scenario {scenario_id}")
    try:
        deleted_scenario = crud.delete_scenario(session, scenario_id)
        if not deleted_scenario:
            print(f"DEBUG: Scenario {scenario_id} not found or delete failed")
            raise HTTPException(status_code=404, detail="Scenario not found")
        print(f"DEBUG: Scenario {scenario_id} deleted successfully")
        return {"status": "deleted", "id": scenario_id}
    except Exception as e:
        print(f"DEBUG: Error deleting scenario: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# Tax Funding Settings endpoints
@app.get("/api/scenarios/{scenario_id}/settings", response_model=TaxFundingSettingsRead)
def get_tax_funding_settings(scenario_id: int, session: Session = Depends(get_session)):
    """Get tax funding settings for a scenario. Creates default if not exists."""
    # Check if scenario exists
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Get or create settings
    from sqlmodel import select
    settings = session.exec(select(TaxFundingSettings).where(TaxFundingSettings.scenario_id == scenario_id)).first()
    if not settings:
        # Create default settings
        import json
        default_order = [TaxFundingSource.CASH, TaxFundingSource.TAXABLE_BROKERAGE, 
                        TaxFundingSource.TRADITIONAL_RETIREMENT, TaxFundingSource.ROTH]
        settings = TaxFundingSettings(
            scenario_id=scenario_id,
            tax_funding_order_json=json.dumps([s.value for s in default_order]),
            allow_retirement_withdrawals_for_taxes=True,
            if_insufficient_funds_behavior=InsufficientFundsBehavior.FAIL_WITH_SHORTFALL
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)
    
    # Parse JSON and return
    import json
    tax_funding_order = [TaxFundingSource(s) for s in json.loads(settings.tax_funding_order_json)]
    return TaxFundingSettingsRead(
        id=settings.id,
        scenario_id=settings.scenario_id,
        tax_funding_order=tax_funding_order,
        allow_retirement_withdrawals_for_taxes=settings.allow_retirement_withdrawals_for_taxes,
        if_insufficient_funds_behavior=settings.if_insufficient_funds_behavior,
        created_at=settings.created_at,
        updated_at=settings.updated_at
    )

@app.put("/api/scenarios/{scenario_id}/settings", response_model=TaxFundingSettingsRead)
def update_tax_funding_settings(
    scenario_id: int, 
    settings_data: TaxFundingSettingsCreate,
    session: Session = Depends(get_session)
):
    """Update tax funding settings for a scenario."""
    # Check if scenario exists
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Validate tax_funding_order
    if not settings_data.tax_funding_order:
        raise HTTPException(status_code=400, detail="tax_funding_order must contain at least one source")
    
    # Check for duplicates
    if len(settings_data.tax_funding_order) != len(set(settings_data.tax_funding_order)):
        raise HTTPException(status_code=400, detail="tax_funding_order contains duplicate entries")
    
    # Validate all are known enums
    valid_sources = {TaxFundingSource.CASH, TaxFundingSource.TAXABLE_BROKERAGE, 
                     TaxFundingSource.TRADITIONAL_RETIREMENT, TaxFundingSource.ROTH}
    for source in settings_data.tax_funding_order:
        if source not in valid_sources:
            raise HTTPException(status_code=400, detail=f"Unknown tax funding source: {source}")
    
    # Get or create settings
    from sqlmodel import select
    settings = session.exec(select(TaxFundingSettings).where(TaxFundingSettings.scenario_id == scenario_id)).first()
    import json
    from datetime import datetime
    
    if settings:
        # Update existing
        settings.tax_funding_order_json = json.dumps([s.value for s in settings_data.tax_funding_order])
        settings.allow_retirement_withdrawals_for_taxes = settings_data.allow_retirement_withdrawals_for_taxes
        settings.if_insufficient_funds_behavior = settings_data.if_insufficient_funds_behavior
        settings.updated_at = datetime.utcnow()
    else:
        # Create new
        settings = TaxFundingSettings(
            scenario_id=scenario_id,
            tax_funding_order_json=json.dumps([s.value for s in settings_data.tax_funding_order]),
            allow_retirement_withdrawals_for_taxes=settings_data.allow_retirement_withdrawals_for_taxes,
            if_insufficient_funds_behavior=settings_data.if_insufficient_funds_behavior
        )
        session.add(settings)
    
    session.commit()
    session.refresh(settings)
    
    # Return updated settings
    tax_funding_order = [TaxFundingSource(s) for s in json.loads(settings.tax_funding_order_json)]
    return TaxFundingSettingsRead(
        id=settings.id,
        scenario_id=settings.scenario_id,
        tax_funding_order=tax_funding_order,
        allow_retirement_withdrawals_for_taxes=settings.allow_retirement_withdrawals_for_taxes,
        if_insufficient_funds_behavior=settings.if_insufficient_funds_behavior,
        created_at=settings.created_at,
        updated_at=settings.updated_at
    )

@app.get("/api/scenarios/{scenario_id}/assets", response_model=List[AssetRead])
def read_assets(scenario_id: int, session: Session = Depends(get_session)):
    from sqlmodel import select
    from .models import RealEstateDetails, GeneralEquityDetails, SpecificStockDetails, RSUGrantDetails, RSUVestingTranche
    from .schemas import RealEstateDetailsRead, GeneralEquityDetailsRead, SpecificStockDetailsRead, RSUGrantDetailsRead, RSUVestingTrancheRead
    
    assets = crud.get_assets_for_scenario(session, scenario_id)
    
    # Manually construct AssetRead objects to ensure relationships are properly serialized
    result = []
    for asset in assets:
        asset_dict = {
            "id": asset.id,
            "scenario_id": asset.scenario_id,
            "name": asset.name,
            "type": asset.type,
            "current_balance": asset.current_balance,
            "real_estate_details": None,
            "general_equity_details": None,
            "specific_stock_details": None,
            "rsu_grant_details": None
        }
        
        if asset.type == "real_estate":
            re_detail = session.exec(select(RealEstateDetails).where(RealEstateDetails.asset_id == asset.id)).first()
            if re_detail:
                asset_dict["real_estate_details"] = RealEstateDetailsRead.model_validate(re_detail)
        elif asset.type == "general_equity":
            ge_detail = session.exec(select(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == asset.id)).first()
            if ge_detail:
                asset_dict["general_equity_details"] = GeneralEquityDetailsRead.model_validate(ge_detail)
        elif asset.type == "specific_stock":
            stock_detail = session.exec(select(SpecificStockDetails).where(SpecificStockDetails.asset_id == asset.id)).first()
            if stock_detail:
                asset_dict["specific_stock_details"] = SpecificStockDetailsRead.model_validate(stock_detail)
        elif asset.type == "rsu_grant":
            rsu_grant = session.exec(select(RSUGrantDetails).where(RSUGrantDetails.asset_id == asset.id)).first()
            if rsu_grant:
                # Load vesting tranches
                tranches = session.exec(select(RSUVestingTranche).where(RSUVestingTranche.grant_id == rsu_grant.id)).all()
                # Create RSUGrantDetailsRead with tranches
                grant_dict = {
                    "id": rsu_grant.id,
                    "asset_id": rsu_grant.asset_id,
                    "employer": rsu_grant.employer,
                    "security_id": rsu_grant.security_id,
                    "grant_date": rsu_grant.grant_date,
                    "grant_value_type": rsu_grant.grant_value_type,
                    "grant_value": rsu_grant.grant_value,
                    "grant_fmv_at_grant": rsu_grant.grant_fmv_at_grant,
                    "shares_granted": rsu_grant.shares_granted,
                    "vesting_tranches": [RSUVestingTrancheRead.model_validate(t) for t in tranches]
                }
                asset_dict["rsu_grant_details"] = RSUGrantDetailsRead(**grant_dict)
        
        result.append(AssetRead(**asset_dict))
    
    return result

@app.post("/api/scenarios/{scenario_id}/assets", response_model=AssetRead)
def create_asset(scenario_id: int, asset: AssetCreate, session: Session = Depends(get_session)):
    from sqlmodel import select
    from .models import RealEstateDetails, GeneralEquityDetails, SpecificStockDetails, RSUGrantDetails, RSUVestingTranche
    from .schemas import RealEstateDetailsRead, GeneralEquityDetailsRead, SpecificStockDetailsRead, RSUGrantDetailsRead, RSUVestingTrancheRead
    
    scenario = crud.get_scenario(session, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    try:
        created_asset = crud.create_typed_asset(session, scenario_id, asset)
        
        # Manually construct AssetRead to ensure relationships are properly serialized
        asset_dict = {
            "id": created_asset.id,
            "scenario_id": created_asset.scenario_id,
            "name": created_asset.name,
            "type": created_asset.type,
            "current_balance": created_asset.current_balance,
            "real_estate_details": None,
            "general_equity_details": None,
            "specific_stock_details": None,
            "rsu_grant_details": None
        }
        
        if created_asset.type == "real_estate":
            re_detail = session.exec(select(RealEstateDetails).where(RealEstateDetails.asset_id == created_asset.id)).first()
            if re_detail:
                asset_dict["real_estate_details"] = RealEstateDetailsRead.model_validate(re_detail)
        elif created_asset.type == "general_equity":
            ge_detail = session.exec(select(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == created_asset.id)).first()
            if ge_detail:
                asset_dict["general_equity_details"] = GeneralEquityDetailsRead.model_validate(ge_detail)
        elif created_asset.type == "specific_stock":
            stock_detail = session.exec(select(SpecificStockDetails).where(SpecificStockDetails.asset_id == created_asset.id)).first()
            if stock_detail:
                asset_dict["specific_stock_details"] = SpecificStockDetailsRead.model_validate(stock_detail)
        elif created_asset.type == "rsu_grant":
            rsu_grant = session.exec(select(RSUGrantDetails).where(RSUGrantDetails.asset_id == created_asset.id)).first()
            if rsu_grant:
                # Load vesting tranches
                tranches = session.exec(select(RSUVestingTranche).where(RSUVestingTranche.grant_id == rsu_grant.id)).all()
                grant_dict = {
                    "id": rsu_grant.id,
                    "asset_id": rsu_grant.asset_id,
                    "employer": rsu_grant.employer,
                    "security_id": rsu_grant.security_id,
                    "grant_date": rsu_grant.grant_date,
                    "grant_value_type": rsu_grant.grant_value_type,
                    "grant_value": rsu_grant.grant_value,
                    "grant_fmv_at_grant": rsu_grant.grant_fmv_at_grant,
                    "shares_granted": rsu_grant.shares_granted,
                    "vesting_tranches": [RSUVestingTrancheRead.model_validate(t) for t in tranches]
                }
                asset_dict["rsu_grant_details"] = RSUGrantDetailsRead(**grant_dict)
        
        return AssetRead(**asset_dict)
    except Exception as e:
        import traceback
        print(f"Error creating asset: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error creating asset: {str(e)}")

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

@app.post("/api/scenarios/{scenario_id}/income_sources", response_model=IncomeSourceRead)
def create_income_source(scenario_id: int, income_source: IncomeSourceCreate, session: Session = Depends(get_session)):
    scenario = crud.get_scenario(session, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return crud.create_income_source(session, income_source, scenario_id)

@app.get("/api/scenarios/{scenario_id}/income_sources", response_model=List[IncomeSourceRead])
def read_income_sources(scenario_id: int, session: Session = Depends(get_session)):
    return crud.get_income_sources_for_scenario(session, scenario_id)

@app.put("/api/income_sources/{id}", response_model=IncomeSourceRead)
def update_income_source(id: int, income_source: IncomeSourceCreate, session: Session = Depends(get_session)):
    updated = crud.update_income_source(session, id, income_source)
    if not updated:
        raise HTTPException(status_code=404, detail="Income source not found")
    return updated

@app.delete("/api/income_sources/{id}")
def delete_income_source(id: int, session: Session = Depends(get_session)):
    deleted = crud.delete_income_source(session, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Income source not found")
    return {"status": "deleted", "id": id}

@app.get("/api/scenarios/{scenario_id}/simulate/simple-bond")
def run_simulation(scenario_id: int, debug: bool = False, session: Session = Depends(get_session)):
    try:
        result = simulation.run_simple_bond_simulation(session, scenario_id, debug=debug)
        if not result:
            raise HTTPException(status_code=404, detail="Scenario not found or simulation failed")
        return result
    except Exception as e:
        import traceback
        print(f"Error running simulation: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

# Security/Ticker endpoints
@app.get("/api/securities", response_model=List[SecurityRead])
def read_securities(session: Session = Depends(get_session)):
    """Get all securities."""
    from sqlmodel import select
    return session.exec(select(Security)).all()

@app.get("/api/securities/{security_id}", response_model=SecurityRead)
def read_security(security_id: int, session: Session = Depends(get_session)):
    """Get a security by ID."""
    security = crud.get_security(session, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")
    return security

@app.get("/api/securities/symbol/{symbol}", response_model=SecurityRead)
def read_security_by_symbol(symbol: str, session: Session = Depends(get_session)):
    """Get a security by symbol (ticker)."""
    security = crud.get_security_by_symbol(session, symbol.upper())
    if not security:
        raise HTTPException(status_code=404, detail=f"Security with symbol {symbol} not found")
    return security

@app.post("/api/securities", response_model=SecurityRead)
def create_or_get_security(security: SecurityCreate, session: Session = Depends(get_session)):
    """Create a security or get existing one by symbol (get-or-create pattern). Updates appreciation rate if provided."""
    return crud.get_or_create_security(
        session, 
        security.symbol.upper(), 
        security.name,
        security.assumed_appreciation_rate
    )

# RSU Grant Forecast endpoints
@app.get("/api/scenarios/{scenario_id}/rsu_forecasts", response_model=List[RSUGrantForecastRead])
def read_rsu_forecasts(scenario_id: int, session: Session = Depends(get_session)):
    """Get all RSU grant forecasts for a scenario."""
    from sqlmodel import select
    forecasts = session.exec(
        select(RSUGrantForecast).where(RSUGrantForecast.scenario_id == scenario_id)
    ).all()
    return forecasts

@app.post("/api/scenarios/{scenario_id}/rsu_forecasts", response_model=RSUGrantForecastRead)
def create_rsu_forecast(
    scenario_id: int,
    forecast: RSUGrantForecastCreate,
    session: Session = Depends(get_session)
):
    """Create a new RSU grant forecast."""
    scenario = crud.get_scenario(session, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    rsu_forecast = RSUGrantForecast(
        scenario_id=scenario_id,
        **forecast.dict()
    )
    session.add(rsu_forecast)
    session.commit()
    session.refresh(rsu_forecast)
    return rsu_forecast

@app.put("/api/rsu_forecasts/{forecast_id}", response_model=RSUGrantForecastRead)
def update_rsu_forecast(
    forecast_id: int,
    forecast: RSUGrantForecastCreate,
    session: Session = Depends(get_session)
):
    """Update an RSU grant forecast."""
    db_forecast = session.get(RSUGrantForecast, forecast_id)
    if not db_forecast:
        raise HTTPException(status_code=404, detail="RSU forecast not found")
    
    for key, value in forecast.dict().items():
        setattr(db_forecast, key, value)
    
    session.add(db_forecast)
    session.commit()
    session.refresh(db_forecast)
    return db_forecast

@app.delete("/api/rsu_forecasts/{forecast_id}")
def delete_rsu_forecast(forecast_id: int, session: Session = Depends(get_session)):
    """Delete an RSU grant forecast."""
    db_forecast = session.get(RSUGrantForecast, forecast_id)
    if not db_forecast:
        raise HTTPException(status_code=404, detail="RSU forecast not found")
    
    session.delete(db_forecast)
    session.commit()
    return {"status": "deleted", "id": forecast_id}

# RSU Grant details endpoint (with unvested/vested breakdown)
@app.get("/api/assets/{asset_id}/rsu_details")
def get_rsu_grant_details(asset_id: int, session: Session = Depends(get_session)):
    """Get detailed RSU grant information including unvested/vested breakdown."""
    from sqlmodel import select
    from .models import RSUGrantDetails, RSUVestingTranche, SpecificStockDetails
    from datetime import datetime
    
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if asset.type != "rsu_grant":
        raise HTTPException(status_code=400, detail="Asset is not an RSU grant")
    
    rsu_grant = session.exec(
        select(RSUGrantDetails).where(RSUGrantDetails.asset_id == asset_id)
    ).first()
    
    if not rsu_grant:
        raise HTTPException(status_code=404, detail="RSU grant details not found")
    
    # Get vesting tranches
    tranches = session.exec(
        select(RSUVestingTranche).where(RSUVestingTranche.grant_id == rsu_grant.id)
        .order_by(RSUVestingTranche.vesting_date)
    ).all()
    
    # Get security info
    security = session.get(Security, rsu_grant.security_id)
    
    # Get vested lots (SpecificStockDetails with source_rsu_grant_id)
    vested_lots = session.exec(
        select(SpecificStockDetails).where(
            SpecificStockDetails.source_rsu_grant_id == rsu_grant.id
        )
    ).all()
    
    # Calculate unvested shares (total granted - sum of tranche percentages that have vested)
    # For simplicity, we'll calculate based on tranches with vesting_date <= today
    today = datetime.now().date()
    total_vested_percentage = sum(
        t.percentage_of_grant for t in tranches
        if hasattr(t.vesting_date, 'date') and t.vesting_date.date() <= today
    )
    unvested_percentage = 1.0 - total_vested_percentage
    unvested_shares = rsu_grant.shares_granted * unvested_percentage
    
    # Calculate current estimated value (simplified - would need current stock price)
    # For now, use grant FMV as placeholder
    current_estimated_value = rsu_grant.shares_granted * rsu_grant.grant_fmv_at_grant
    
    return {
        "grant": {
            "id": rsu_grant.id,
            "employer": rsu_grant.employer,
            "security": {
                "id": security.id if security else None,
                "symbol": security.symbol if security else None,
                "name": security.name if security else None,
                "assumed_appreciation_rate": security.assumed_appreciation_rate if security else 0.0
            },
            "grant_date": rsu_grant.grant_date,
            "grant_value": rsu_grant.grant_value,
            "grant_fmv_at_grant": rsu_grant.grant_fmv_at_grant,
            "shares_granted": rsu_grant.shares_granted
        },
        "vesting_schedule": [
            {
                "id": t.id,
                "vesting_date": t.vesting_date,
                "percentage_of_grant": t.percentage_of_grant,
                "shares_vesting": rsu_grant.shares_granted * t.percentage_of_grant
            }
            for t in tranches
        ],
        "unvested": {
            "shares": unvested_shares,
            "percentage": unvested_percentage,
            "estimated_value": unvested_shares * rsu_grant.grant_fmv_at_grant
        },
        "vested_lots": [
            {
                "id": lot.id,
                "asset_id": lot.asset_id,
                "vesting_date": getattr(lot, 'vesting_date', None),  # Would need to track this
                "shares_held": lot.shares_owned,
                "basis_per_share": lot.cost_basis / lot.shares_owned if lot.shares_owned > 0 else 0,
                "basis_total": lot.cost_basis,
                "current_price": lot.current_price,
                "current_value": lot.shares_owned * lot.current_price,
                "unrealized_gain": (lot.shares_owned * lot.current_price) - lot.cost_basis
            }
            for lot in vested_lots
        ]
    }
