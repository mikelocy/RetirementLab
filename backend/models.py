from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

class TaxWrapper(str, Enum):
    TAXABLE = "taxable"            # Brokerage account, individual stock account
    TRADITIONAL = "traditional"    # 401k, Traditional IRA, other pre-tax
    ROTH = "roth"                  # Roth IRA, Roth 401k
    TAX_EXEMPT_OTHER = "tax_exempt_other"  # e.g., muni bond fund

class IncomeType(str, Enum):
    ORDINARY = "ordinary"          # Fully taxable as ordinary income (pensions, wages, etc.)
    SOCIAL_SECURITY = "social_security"  # Social Security benefits (special tax treatment)
    TAX_EXEMPT = "tax_exempt"      # Not taxable (e.g., VA disability, some disability insurance)
    DISABILITY = "disability"      # Disability income (may be taxable or exempt depending on source)

# Import FilingStatus from tax_config to avoid circular imports
from .tax_config import FilingStatus

class Scenario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    current_age: int
    base_year: Optional[int] = Field(default=None)  # Calendar year corresponding to current_age (e.g., if current_age=50 and base_year=2024, then age 51 = 2025)
    retirement_age: int
    end_age: int
    inflation_rate: float
    bond_return_rate: float
    annual_contribution_pre_retirement: float
    annual_spending_in_retirement: float
    filing_status: FilingStatus = Field(default=FilingStatus.MARRIED_FILING_JOINTLY)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    assets: List["Asset"] = Relationship(back_populates="scenario")
    income_sources: List["IncomeSource"] = Relationship(back_populates="scenario")
    rsu_grant_forecasts: List["RSUGrantForecast"] = Relationship(back_populates="scenario")

class IncomeSource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    name: str
    amount: float
    start_age: int
    end_age: int
    appreciation_rate: float = 0.0
    source_type: str = "income" # "income", "drawdown", or "house_sale"
    linked_asset_id: Optional[int] = None
    income_type: IncomeType = Field(default=IncomeType.ORDINARY)  # Tax treatment type
    
    scenario: Optional[Scenario] = Relationship(back_populates="income_sources")

class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    name: str
    type: str
    current_balance: float

    scenario: Scenario = Relationship(back_populates="assets")
    real_estate_details: Optional["RealEstateDetails"] = Relationship(back_populates="asset")
    general_equity_details: Optional["GeneralEquityDetails"] = Relationship(back_populates="asset")
    specific_stock_details: Optional["SpecificStockDetails"] = Relationship(back_populates="asset")
    rsu_grant_details: Optional["RSUGrantDetails"] = Relationship(back_populates="asset")

class DepreciationMethod(str, Enum):
    NONE = "none"  # Primary residence, land, etc.
    RESIDENTIAL_27_5 = "residential_27_5"  # Residential rental property (27.5 years)
    COMMERCIAL_39 = "commercial_39"  # Commercial property (39 years)

class RealEstateDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    
    property_type: str = "rental"  # e.g. "primary", "rental", "land"
    property_value: float  # current market value
    mortgage_balance: float = 0.0
    interest_rate: float = 0.0  # as decimal, e.g. 0.04
    annual_property_tax: float = 0.0
    annual_insurance: float = 0.0
    annual_maintenance_pct: float = 0.0  # of property_value
    annual_rent: float = 0.0  # 0 if not rental
    appreciation_rate: float = 0.0  # as decimal
    
    # Mortgage specifics
    mortgage_term_years: int = 30
    mortgage_current_year: int = 1
    is_interest_only: bool = False
    
    # Tax-related fields
    purchase_price: float = 0.0  # Original acquisition cost
    land_value: float = 0.0  # Portion of purchase price that's land (not depreciable)
    depreciation_method: DepreciationMethod = Field(default=DepreciationMethod.NONE)
    depreciation_start_year: Optional[int] = None  # Year depreciation began (for tracking)
    accumulated_depreciation: float = 0.0  # Total depreciation taken to date
    
    # Primary residence tracking (for capital gains exclusion)
    primary_residence_start_age: Optional[int] = None  # Age when property became primary residence
    primary_residence_end_age: Optional[int] = None  # Age when property stopped being primary residence
    
    asset: Optional[Asset] = Relationship(back_populates="real_estate_details")

class GeneralEquityDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    
    account_type: str = "taxable"  # e.g. "taxable", "ira", "roth", "401k"
    account_balance: float  # current balance in this account
    expected_return_rate: float = 0.0  # as decimal
    fee_rate: float = 0.0  # as decimal
    annual_contribution: float = 0.0  # optional, for future use
    
    # New Tax Fields
    tax_wrapper: TaxWrapper = Field(default=TaxWrapper.TAXABLE)
    cost_basis: float = 0.0  # For taxable accounts
    
    asset: Optional[Asset] = Relationship(back_populates="general_equity_details")

class SpecificStockDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    
    ticker: str
    shares_owned: float
    current_price: float
    assumed_appreciation_rate: float = 0.0
    dividend_yield: float = 0.0

    # New Tax Fields
    tax_wrapper: TaxWrapper = Field(default=TaxWrapper.TAXABLE)
    cost_basis: float = 0.0  # For taxable accounts
    
    # RSU tracking fields
    source_type: str = "user_entered"  # "user_entered" or "rsu_vest"
    source_rsu_grant_id: Optional[int] = None  # FK to RSUGrantDetails if from RSU vesting
    
    asset: Optional[Asset] = Relationship(back_populates="specific_stock_details")

# Centralized Security/Ticker model for shared stock price/appreciation assumptions
class Security(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(unique=True)  # e.g., "KLAC"
    name: Optional[str] = None  # e.g., "KLA Corporation"
    assumed_appreciation_rate: float = 0.0  # Expected annual return (e.g., 0.07 = 7%)
    # This rate is used for RSU grants and can be overridden by SpecificStockDetails if the stock is held directly
    
# RSU Grant Details (unvested layer)
class RSUGrantDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    
    employer: Optional[str] = None
    security_id: int = Field(foreign_key="security.id")
    grant_date: datetime
    grant_value_type: str = "dollar_value"  # For now, only support dollar-based grants
    grant_value: float  # Total dollar value at grant
    grant_fmv_at_grant: float  # Fair market value per share at grant date
    shares_granted: float  # Computed: grant_value / grant_fmv_at_grant
    
    # Share withholding (mechanical only - affects net shares delivered, not taxable income)
    estimated_share_withholding_rate: float = 0.37  # Default 37% - used only to estimate net shares delivered at vesting
    
    asset: Optional[Asset] = Relationship(back_populates="rsu_grant_details")
    security: Optional["Security"] = Relationship()
    vesting_tranches: List["RSUVestingTranche"] = Relationship(back_populates="grant")

# RSU Vesting Tranche (user-defined vesting schedule)
class RSUVestingTranche(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    grant_id: int = Field(foreign_key="rsugrantdetails.id")
    vesting_date: datetime
    percentage_of_grant: float  # 0-1, e.g., 0.25 for 25%
    
    grant: Optional[RSUGrantDetails] = Relationship(back_populates="vesting_tranches")

# RSU Grant Forecast (for future grants)
class RSUGrantForecast(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    
    security_id: int = Field(foreign_key="security.id")
    first_grant_date: datetime
    grant_frequency: str = "annual"  # "annual", "quarterly", etc.
    grant_value: float  # Dollar amount per grant
    estimated_share_withholding_rate: float = 0.37  # Used only to estimate net shares delivered at vesting
    
    # Vesting template - store as JSON or reference to a pattern
    # For v1, we'll store a simple structure that can be copied to new grants
    vesting_schedule_years: int = 4  # Default 4-year vest
    vesting_cliff_years: float = 1.0  # Years until first vest (cliff)
    vesting_frequency: str = "quarterly"  # After cliff: "quarterly", "annual", etc.
    
    scenario: Optional[Scenario] = Relationship()
    security: Optional["Security"] = Relationship()
