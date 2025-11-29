from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from sqlmodel import SQLModel

class ScenarioBase(BaseModel):
    name: str
    description: Optional[str] = None
    current_age: int
    retirement_age: int
    end_age: int
    inflation_rate: float
    bond_return_rate: float
    annual_contribution_pre_retirement: float
    annual_spending_in_retirement: float

class ScenarioCreate(ScenarioBase):
    pass

class ScenarioRead(ScenarioBase):
    id: int
    created_at: datetime
    updated_at: datetime

class IncomeSourceBase(SQLModel):
    name: str
    amount: float
    start_age: int
    end_age: int
    appreciation_rate: float = 0.0
    source_type: str = "income"
    linked_asset_id: Optional[int] = None

class IncomeSourceCreate(IncomeSourceBase):
    pass

class IncomeSourceRead(IncomeSourceBase):
    id: int
    scenario_id: int

class RealEstateDetailsBase(SQLModel):
    property_type: str = "rental"
    property_value: float
    mortgage_balance: float = 0.0
    interest_rate: float = 0.0
    annual_property_tax: float = 0.0
    annual_insurance: float = 0.0
    annual_maintenance_pct: float = 0.0
    annual_rent: float = 0.0
    appreciation_rate: float = 0.0
    mortgage_term_years: int = 30
    mortgage_current_year: int = 1
    is_interest_only: bool = False

class RealEstateDetailsCreate(RealEstateDetailsBase):
    pass

class RealEstateDetailsRead(RealEstateDetailsBase):
    id: int
    asset_id: int

class GeneralEquityDetailsBase(SQLModel):
    account_type: str = "taxable"
    account_balance: float
    expected_return_rate: float = 0.0
    fee_rate: float = 0.0
    annual_contribution: float = 0.0

class GeneralEquityDetailsCreate(GeneralEquityDetailsBase):
    pass

class GeneralEquityDetailsRead(GeneralEquityDetailsBase):
    id: int
    asset_id: int

class SpecificStockDetailsBase(SQLModel):
    ticker: str
    shares_owned: float
    current_price: float
    assumed_appreciation_rate: float = 0.0
    dividend_yield: float = 0.0

class SpecificStockDetailsCreate(SpecificStockDetailsBase):
    pass

class SpecificStockDetailsRead(SpecificStockDetailsBase):
    id: int
    asset_id: int

class AssetBase(BaseModel):
    name: str
    type: str
    current_balance: float

class AssetCreate(SQLModel):
    name: str
    type: str  # "real_estate", "general_equity", or "specific_stock"
    real_estate_details: Optional[RealEstateDetailsCreate] = None
    general_equity_details: Optional[GeneralEquityDetailsCreate] = None
    specific_stock_details: Optional[SpecificStockDetailsCreate] = None

class AssetRead(AssetBase):
    id: int
    scenario_id: int
    real_estate_details: Optional[RealEstateDetailsRead] = None
    general_equity_details: Optional[GeneralEquityDetailsRead] = None
    specific_stock_details: Optional[SpecificStockDetailsRead] = None
