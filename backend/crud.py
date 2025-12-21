from typing import Optional
from sqlmodel import Session, select, delete
from sqlalchemy.orm import Query
from .models import Scenario, Asset, RealEstateDetails, GeneralEquityDetails, SpecificStockDetails, IncomeSource, TaxWrapper, IncomeType, Security, RSUGrantDetails, RSUVestingTranche, RSUGrantForecast
from .schemas import ScenarioCreate, AssetCreate, RealEstateDetailsCreate, GeneralEquityDetailsCreate, SpecificStockDetailsCreate, IncomeSourceCreate
from datetime import datetime

def infer_tax_wrapper_from_account_type(account_type: str, current_tax_wrapper: TaxWrapper = TaxWrapper.TAXABLE) -> TaxWrapper:
    """
    Infer tax_wrapper from account_type if tax_wrapper wasn't explicitly set.
    This handles cases where the frontend only sends account_type (e.g., "roth", "ira").
    """
    # Only infer if tax_wrapper is still at default (TAXABLE)
    # This allows explicit tax_wrapper values to override account_type
    if current_tax_wrapper != TaxWrapper.TAXABLE:
        return current_tax_wrapper
    
    account_type_lower = account_type.lower() if account_type else ""
    
    if account_type_lower in ("roth", "roth ira", "roth 401k"):
        return TaxWrapper.ROTH
    elif account_type_lower in ("ira", "traditional ira", "401k", "401(k)", "403b", "457", "traditional"):
        return TaxWrapper.TRADITIONAL
    elif account_type_lower in ("taxable", "brokerage", "individual"):
        return TaxWrapper.TAXABLE
    else:
        # Default to TAXABLE if unknown
        return TaxWrapper.TAXABLE

def get_scenarios(session: Session):
    statement = select(Scenario)
    return session.exec(statement).all()

def get_scenario(session: Session, scenario_id: int):
    return session.get(Scenario, scenario_id)

def create_scenario(session: Session, scenario_create: ScenarioCreate):
    db_scenario = Scenario.from_orm(scenario_create)
    # If base_year is not provided, default to current year
    if db_scenario.base_year is None:
        db_scenario.base_year = datetime.utcnow().year
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
        if asset_type == "cash":
            # Cash assets use current_balance directly from AssetCreate
            assert asset_data.current_balance is not None, "Cash balance required for cash assets"
            current_balance = asset_data.current_balance
        elif asset_type == "real_estate":
            assert asset_data.real_estate_details is not None, "Real estate details required"
            current_balance = asset_data.real_estate_details.property_value
        elif asset_type == "general_equity":
            assert asset_data.general_equity_details is not None, "General equity details required"
            current_balance = asset_data.general_equity_details.account_balance
        elif asset_type == "specific_stock":
            assert asset_data.specific_stock_details is not None, "Specific stock details required"
            current_balance = asset_data.specific_stock_details.shares_owned * asset_data.specific_stock_details.current_price
        elif asset_type == "rsu_grant":
            assert asset_data.rsu_grant_details is not None, "RSU grant details required"
            # For RSU grants, use the grant_value as the current balance (represents unvested value at grant date)
            current_balance = asset_data.rsu_grant_details.grant_value
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
                **asset_data.real_estate_details.dict(exclude_unset=False)
            )
            session.add(re_details)
        elif asset_type == "general_equity" and asset_data.general_equity_details:
            # Use model_dump() for Pydantic v2, fallback to dict() for v1
            try:
                ge_data = asset_data.general_equity_details.model_dump(exclude_unset=False)
            except AttributeError:
                ge_data = asset_data.general_equity_details.dict(exclude_unset=False)
            
            # Infer tax_wrapper from account_type if not explicitly set or still at default
            # This handles cases where frontend only sends account_type (e.g., "roth", "ira")
            if "tax_wrapper" not in ge_data:
                # tax_wrapper not provided - infer from account_type
                account_type = ge_data.get("account_type", "taxable")
                ge_data["tax_wrapper"] = infer_tax_wrapper_from_account_type(account_type, TaxWrapper.TAXABLE)
            elif ge_data.get("tax_wrapper") == TaxWrapper.TAXABLE and "account_type" in ge_data:
                # tax_wrapper is default TAXABLE but account_type suggests otherwise - infer from account_type
                account_type = ge_data.get("account_type", "taxable")
                inferred = infer_tax_wrapper_from_account_type(account_type, TaxWrapper.TAXABLE)
                if inferred != TaxWrapper.TAXABLE:
                    ge_data["tax_wrapper"] = inferred
            
            ge_details = GeneralEquityDetails(
                asset_id=asset.id,
                **ge_data
            )
            session.add(ge_details)
        elif asset_type == "specific_stock" and asset_data.specific_stock_details:
            stock_details = SpecificStockDetails(
                asset_id=asset.id,
                **asset_data.specific_stock_details.dict()
            )
            session.add(stock_details)
        elif asset_type == "rsu_grant" and asset_data.rsu_grant_details:
            rsu_data = asset_data.rsu_grant_details.dict(exclude_unset=False)
            vesting_tranches_data = rsu_data.pop("vesting_tranches", [])
            
            # Validate vesting tranches sum to 100%
            total_percentage = sum(t.get("percentage_of_grant", 0) for t in vesting_tranches_data)
            if abs(total_percentage - 1.0) > 0.001:
                raise ValueError(f"Vesting tranches must sum to 100%, got {total_percentage * 100}%")
            
            # Calculate shares_granted if not provided
            if "shares_granted" not in rsu_data or rsu_data["shares_granted"] == 0:
                if rsu_data.get("grant_fmv_at_grant", 0) > 0:
                    rsu_data["shares_granted"] = rsu_data["grant_value"] / rsu_data["grant_fmv_at_grant"]
                else:
                    raise ValueError("grant_fmv_at_grant must be provided to calculate shares_granted")
            
            rsu_grant = RSUGrantDetails(
                asset_id=asset.id,
                **rsu_data
            )
            session.add(rsu_grant)
            session.flush()  # Ensure rsu_grant.id is populated
            
            # Create vesting tranches
            for tranche_data in vesting_tranches_data:
                tranche = RSUVestingTranche(
                    grant_id=rsu_grant.id,
                    **tranche_data
                )
                session.add(tranche)

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
    if db_asset.type == "cash":
        # Cash assets - just update balance
        if asset_data.current_balance is not None:
            db_asset.current_balance = asset_data.current_balance
        
        # Remove other type details if they exist (e.g. if type changed)
        if db_asset.real_estate_details:
            session.delete(db_asset.real_estate_details)
        if db_asset.general_equity_details:
            session.delete(db_asset.general_equity_details)
        if db_asset.specific_stock_details:
            session.delete(db_asset.specific_stock_details)
        if db_asset.rsu_grant_details:
            session.delete(db_asset.rsu_grant_details)
            
    elif db_asset.type == "real_estate":
        if not asset_data.real_estate_details:
            return None # validation error in real app
        
        # Update balance
        db_asset.current_balance = asset_data.real_estate_details.property_value
        
        # Update or create details
        if db_asset.real_estate_details:
            # Use dict(exclude_unset=False) to include all fields, even if None
            for key, value in asset_data.real_estate_details.dict(exclude_unset=False).items():
                setattr(db_asset.real_estate_details, key, value)
            session.add(db_asset.real_estate_details)
        else:
            re_details = RealEstateDetails(
                asset_id=db_asset.id,
                **asset_data.real_estate_details.dict(exclude_unset=False)
            )
            session.add(re_details)
            
        # Remove other type details if they exist (e.g. if type changed)
        if db_asset.general_equity_details:
            session.delete(db_asset.general_equity_details)
            
    elif db_asset.type == "general_equity":
        if not asset_data.general_equity_details:
            return None
            
        db_asset.current_balance = asset_data.general_equity_details.account_balance
        
        ge_data = asset_data.general_equity_details.dict()
        # Infer tax_wrapper from account_type if not explicitly set or still at default
        # This handles cases where frontend only sends account_type (e.g., "roth", "ira")
        if "tax_wrapper" not in ge_data:
            # tax_wrapper not provided - infer from account_type
            account_type = ge_data.get("account_type", "taxable")
            ge_data["tax_wrapper"] = infer_tax_wrapper_from_account_type(account_type, TaxWrapper.TAXABLE)
        elif ge_data.get("tax_wrapper") == TaxWrapper.TAXABLE and "account_type" in ge_data:
            # tax_wrapper is default TAXABLE but account_type suggests otherwise - infer from account_type
            account_type = ge_data.get("account_type", "taxable")
            inferred = infer_tax_wrapper_from_account_type(account_type, TaxWrapper.TAXABLE)
            if inferred != TaxWrapper.TAXABLE:
                ge_data["tax_wrapper"] = inferred
        
        if db_asset.general_equity_details:
            for key, value in ge_data.items():
                setattr(db_asset.general_equity_details, key, value)
            session.add(db_asset.general_equity_details)
        else:
            ge_details = GeneralEquityDetails(
                asset_id=db_asset.id,
                **ge_data
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
        if db_asset.rsu_grant_details:
            session.delete(db_asset.rsu_grant_details)

    elif db_asset.type == "rsu_grant":
        if not asset_data.rsu_grant_details:
            return None
        
        # For RSU grants, update balance based on current unvested value
        db_asset.current_balance = asset_data.rsu_grant_details.grant_value
        
        rsu_data = asset_data.rsu_grant_details.dict(exclude_unset=False)
        vesting_tranches_data = rsu_data.pop("vesting_tranches", [])
        
        # Validate vesting tranches sum to 100%
        total_percentage = sum(t.get("percentage_of_grant", 0) for t in vesting_tranches_data)
        if abs(total_percentage - 1.0) > 0.001:
            raise ValueError(f"Vesting tranches must sum to 100%, got {total_percentage * 100}%")
        
        # Calculate shares_granted if not provided
        if "shares_granted" not in rsu_data or rsu_data["shares_granted"] == 0:
            if rsu_data.get("grant_fmv_at_grant", 0) > 0:
                rsu_data["shares_granted"] = rsu_data["grant_value"] / rsu_data["grant_fmv_at_grant"]
            else:
                raise ValueError("grant_fmv_at_grant must be provided to calculate shares_granted")
        
        if db_asset.rsu_grant_details:
            # Update existing grant
            for key, value in rsu_data.items():
                setattr(db_asset.rsu_grant_details, key, value)
            session.add(db_asset.rsu_grant_details)
            
            # Delete existing tranches and recreate
            existing_tranches = session.exec(
                select(RSUVestingTranche).where(RSUVestingTranche.grant_id == db_asset.rsu_grant_details.id)
            ).all()
            for tranche in existing_tranches:
                session.delete(tranche)
            
            # Create new tranches
            for tranche_data in vesting_tranches_data:
                tranche = RSUVestingTranche(
                    grant_id=db_asset.rsu_grant_details.id,
                    **tranche_data
                )
                session.add(tranche)
        else:
            # Create new grant details
            rsu_grant = RSUGrantDetails(
                asset_id=db_asset.id,
                **rsu_data
            )
            session.add(rsu_grant)
            session.flush()
            
            for tranche_data in vesting_tranches_data:
                tranche = RSUVestingTranche(
                    grant_id=rsu_grant.id,
                    **tranche_data
                )
                session.add(tranche)
        
        # Remove other type details if they exist
        if db_asset.real_estate_details:
            session.delete(db_asset.real_estate_details)
        if db_asset.general_equity_details:
            session.delete(db_asset.general_equity_details)
        if db_asset.specific_stock_details:
            session.delete(db_asset.specific_stock_details)
            
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
    return db_asset

def delete_asset(session: Session, asset_id: int, commit: bool = True):
    # Direct delete without object loading
    try:
        # First, delete vesting tranches if this is an RSU grant
        rsu_grant = session.exec(
            select(RSUGrantDetails).where(RSUGrantDetails.asset_id == asset_id)
        ).first()
        if rsu_grant:
            session.exec(delete(RSUVestingTranche).where(RSUVestingTranche.grant_id == rsu_grant.id))
            session.exec(delete(RSUGrantDetails).where(RSUGrantDetails.asset_id == asset_id))
        
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
    assets = session.exec(statement).all()
    
    # Eagerly load detail relationships to avoid lazy loading issues during serialization
    for asset in assets:
        if asset.type == "real_estate":
            _ = session.exec(select(RealEstateDetails).where(RealEstateDetails.asset_id == asset.id)).first()
        elif asset.type == "general_equity":
            _ = session.exec(select(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == asset.id)).first()
        elif asset.type == "specific_stock":
            _ = session.exec(select(SpecificStockDetails).where(SpecificStockDetails.asset_id == asset.id)).first()
        elif asset.type == "rsu_grant":
            rsu_grant = session.exec(select(RSUGrantDetails).where(RSUGrantDetails.asset_id == asset.id)).first()
            if rsu_grant:
                # Also load vesting tranches
                _ = session.exec(select(RSUVestingTranche).where(RSUVestingTranche.grant_id == rsu_grant.id)).all()
    
    return assets

# Security CRUD helpers
def get_or_create_security(session: Session, symbol: str, name: Optional[str] = None, assumed_appreciation_rate: Optional[float] = None) -> Security:
    """Get existing security by symbol, or create if it doesn't exist. Updates appreciation rate if provided."""
    existing = session.exec(select(Security).where(Security.symbol == symbol)).first()
    if existing:
        # Update appreciation rate if provided
        if assumed_appreciation_rate is not None:
            existing.assumed_appreciation_rate = assumed_appreciation_rate
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return existing
    
    security = Security(
        symbol=symbol, 
        name=name,
        assumed_appreciation_rate=assumed_appreciation_rate if assumed_appreciation_rate is not None else 0.0
    )
    session.add(security)
    session.commit()
    session.refresh(security)
    return security

def get_security(session: Session, security_id: int) -> Optional[Security]:
    """Get security by ID."""
    return session.get(Security, security_id)

def get_security_by_symbol(session: Session, symbol: str) -> Optional[Security]:
    """Get security by symbol."""
    return session.exec(select(Security).where(Security.symbol == symbol)).first()

def create_income_source(session: Session, income_source: IncomeSourceCreate, scenario_id: int):
    source_data = income_source.dict()
    # Ensure income_type is properly set (handle string to enum conversion)
    if "income_type" in source_data:
        income_type_val = source_data["income_type"]
        if isinstance(income_type_val, str):
            try:
                source_data["income_type"] = IncomeType(income_type_val.lower())
            except ValueError:
                source_data["income_type"] = IncomeType.ORDINARY  # Default if invalid
    else:
        source_data["income_type"] = IncomeType.ORDINARY  # Default if not provided
    
    db_income_source = IncomeSource(scenario_id=scenario_id, **source_data)
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
    
    # Handle income_type conversion if present
    if "income_type" in source_data:
        income_type_val = source_data["income_type"]
        if isinstance(income_type_val, str):
            try:
                source_data["income_type"] = IncomeType(income_type_val.lower())
            except ValueError:
                source_data["income_type"] = IncomeType.ORDINARY  # Default if invalid
    
    for key, value in source_data.items():
        setattr(db_income_source, key, value)
    session.add(db_income_source)
    session.commit()
    session.refresh(db_income_source)
    return db_income_source
