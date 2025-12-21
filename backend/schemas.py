from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from sqlmodel import SQLModel

from .models import TaxWrapper, IncomeType, DepreciationMethod, TaxFundingSource, InsufficientFundsBehavior
from .tax_config import FilingStatus

class ScenarioBase(BaseModel):
    name: str
    description: Optional[str] = None
    current_age: int
    base_year: Optional[int] = None  # Calendar year corresponding to current_age
    retirement_age: int
    end_age: int
    inflation_rate: float
    bond_return_rate: float
    annual_contribution_pre_retirement: float
    annual_spending_in_retirement: float
    filing_status: FilingStatus = FilingStatus.MARRIED_FILING_JOINTLY

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
    income_type: IncomeType = IncomeType.ORDINARY

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
    # Tax-related fields
    purchase_price: float = 0.0
    land_value: float = 0.0
    depreciation_method: DepreciationMethod = DepreciationMethod.NONE
    depreciation_start_year: Optional[int] = None
    accumulated_depreciation: float = 0.0
    # Primary residence tracking (for capital gains exclusion)
    primary_residence_start_age: Optional[int] = None
    primary_residence_end_age: Optional[int] = None

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
    tax_wrapper: TaxWrapper = TaxWrapper.TAXABLE
    cost_basis: float = 0.0

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
    tax_wrapper: TaxWrapper = TaxWrapper.TAXABLE
    cost_basis: float = 0.0
    source_type: str = "user_entered"
    source_rsu_grant_id: Optional[int] = None

class SpecificStockDetailsCreate(SpecificStockDetailsBase):
    pass

class SpecificStockDetailsRead(SpecificStockDetailsBase):
    id: int
    asset_id: int

class AssetBase(BaseModel):
    name: str
    type: str
    current_balance: float

# Security/Ticker schemas
class SecurityBase(SQLModel):
    symbol: str
    name: Optional[str] = None
    assumed_appreciation_rate: float = 0.0  # Expected annual return (e.g., 0.07 = 7%)

class SecurityCreate(SecurityBase):
    pass

class SecurityRead(SecurityBase):
    id: int

# RSU Grant schemas
class RSUVestingTrancheBase(SQLModel):
    vesting_date: datetime
    percentage_of_grant: float  # 0-1

class RSUVestingTrancheCreate(RSUVestingTrancheBase):
    pass

class RSUVestingTrancheRead(RSUVestingTrancheBase):
    id: int
    grant_id: int

class RSUGrantDetailsBase(SQLModel):
    employer: Optional[str] = None
    security_id: int
    grant_date: datetime
    grant_value_type: str = "dollar_value"
    grant_value: float
    grant_fmv_at_grant: float
    shares_granted: float

class RSUGrantDetailsCreate(SQLModel):
    employer: Optional[str] = None
    security_id: int
    grant_date: datetime
    grant_value_type: str = "dollar_value"
    grant_value: float
    grant_fmv_at_grant: float
    shares_granted: Optional[float] = None  # Optional - will be calculated if not provided
    vesting_tranches: List[RSUVestingTrancheCreate] = []

class RSUGrantDetailsRead(RSUGrantDetailsBase):
    id: int
    asset_id: int
    vesting_tranches: List[RSUVestingTrancheRead] = []

# RSU Grant Forecast schemas
class RSUGrantForecastBase(SQLModel):
    security_id: int
    first_grant_date: datetime
    grant_frequency: str = "annual"
    grant_value: float
    vesting_schedule_years: int = 4
    vesting_cliff_years: float = 1.0
    vesting_frequency: str = "quarterly"

class RSUGrantForecastCreate(RSUGrantForecastBase):
    pass

class RSUGrantForecastRead(RSUGrantForecastBase):
    id: int
    scenario_id: int

# Tax Funding Settings schemas
class TaxFundingSettingsBase(SQLModel):
    tax_funding_order: List[TaxFundingSource]  # Array of funding sources in priority order
    allow_retirement_withdrawals_for_taxes: bool = True
    if_insufficient_funds_behavior: InsufficientFundsBehavior = InsufficientFundsBehavior.FAIL_WITH_SHORTFALL

class TaxFundingSettingsCreate(TaxFundingSettingsBase):
    pass

class TaxFundingSettingsRead(TaxFundingSettingsBase):
    id: int
    scenario_id: int
    created_at: datetime
    updated_at: datetime

class AssetCreate(SQLModel):
    name: str
    type: str  # "cash", "real_estate", "general_equity", "specific_stock", or "rsu_grant"
    current_balance: Optional[float] = None  # For cash assets, this is required
    real_estate_details: Optional[RealEstateDetailsCreate] = None
    general_equity_details: Optional[GeneralEquityDetailsCreate] = None
    specific_stock_details: Optional[SpecificStockDetailsCreate] = None
    rsu_grant_details: Optional[RSUGrantDetailsCreate] = None

class AssetRead(AssetBase):
    id: int
    scenario_id: int
    real_estate_details: Optional[RealEstateDetailsRead] = None
    general_equity_details: Optional[GeneralEquityDetailsRead] = None
    specific_stock_details: Optional[SpecificStockDetailsRead] = None
    rsu_grant_details: Optional[RSUGrantDetailsRead] = None
