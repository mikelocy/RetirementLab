from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum
import json

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

class DepreciationMethod(str, Enum):
    NONE = "none"
    RESIDENTIAL_27_5 = "residential_27_5"
    COMMERCIAL_39 = "commercial_39"

class TaxFundingSource(str, Enum):
    CASH = "CASH"
    TAXABLE_BROKERAGE = "TAXABLE_BROKERAGE"
    TRADITIONAL_RETIREMENT = "TRADITIONAL_RETIREMENT"
    ROTH = "ROTH"

class InsufficientFundsBehavior(str, Enum):
    FAIL_WITH_SHORTFALL = "FAIL_WITH_SHORTFALL"
    LIQUIDATE_ALL_AVAILABLE = "LIQUIDATE_ALL_AVAILABLE"

class TaxTableIndexingPolicy(str, Enum):
    CONSTANT_NOMINAL = "CONSTANT_NOMINAL"
    SCENARIO_INFLATION = "SCENARIO_INFLATION"
    CUSTOM_RATE = "CUSTOM_RATE"

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
    tax_funding_settings: Optional["TaxFundingSettings"] = Relationship(back_populates="scenario", sa_relationship_kwargs={"uselist": False})
    tax_tables: List["TaxTable"] = Relationship(back_populates="scenario", sa_relationship_kwargs={"lazy": "select"})

class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    name: str
    type: str  # "general_equity", "specific_stock", "real_estate", "rsu_grant", "cash"
    current_balance: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    scenario: Optional[Scenario] = Relationship(back_populates="assets")
    general_equity_details: Optional["GeneralEquityDetails"] = Relationship(back_populates="asset", sa_relationship_kwargs={"uselist": False})
    specific_stock_details: Optional["SpecificStockDetails"] = Relationship(back_populates="asset", sa_relationship_kwargs={"uselist": False})
    real_estate_details: Optional["RealEstateDetails"] = Relationship(back_populates="asset", sa_relationship_kwargs={"uselist": False})
    rsu_grant_details: Optional["RSUGrantDetails"] = Relationship(back_populates="asset", sa_relationship_kwargs={"uselist": False})
    cash_details: Optional["CashDetails"] = Relationship(back_populates="asset", sa_relationship_kwargs={"uselist": False})

class GeneralEquityDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", unique=True)
    expected_return_rate: float
    fee_rate: float = Field(default=0.0)
    annual_contribution: float = Field(default=0.0)
    tax_wrapper: TaxWrapper = Field(default=TaxWrapper.TAXABLE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    asset: Optional[Asset] = Relationship(back_populates="general_equity_details")

class SpecificStockDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", unique=True)
    security_id: int = Field(foreign_key="security.id")
    shares_owned: float
    average_cost_basis: float
    appreciation_rate: Optional[float] = None  # Override security's assumed_appreciation_rate if set
    tax_wrapper: TaxWrapper = Field(default=TaxWrapper.TAXABLE)
    source_type: Optional[str] = Field(default="user_entered") # "user_entered" or "rsu_vesting"
    source_rsu_grant_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    asset: Optional[Asset] = Relationship(back_populates="specific_stock_details")

class RealEstateDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", unique=True)
    property_value: float
    mortgage_balance: Optional[float] = None
    mortgage_term_years: int = Field(default=30)
    mortgage_current_year: int = Field(default=1)
    interest_rate: float = Field(default=0.0)
    is_interest_only: bool = Field(default=False)
    purchase_price: Optional[float] = None
    land_value: Optional[float] = None
    depreciation_method: Optional[str] = None  # DepreciationMethod enum as string
    depreciation_start_year: Optional[int] = None
    accumulated_depreciation: Optional[float] = None
    property_type: str = Field(default="rental")  # "rental" or "primary_residence"
    primary_residence_start_age: Optional[int] = None
    primary_residence_end_age: Optional[int] = None
    appreciation_rate: float = Field(default=0.03)
    annual_rent: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    asset: Optional[Asset] = Relationship(back_populates="real_estate_details")

class RSUGrantDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", unique=True)
    employer: Optional[str] = None
    security_id: int = Field(foreign_key="security.id")
    grant_date: datetime
    grant_value_type: str  # "dollar_value" or "shares"
    grant_value: float  # Dollar value if grant_value_type == "dollar_value", else number of shares
    grant_fmv_at_grant: float  # Fair market value per share at grant date
    shares_granted: float  # Total shares granted (calculated or provided)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    asset: Optional[Asset] = Relationship(back_populates="rsu_grant_details")
    vesting_tranches: List["RSUVestingTranche"] = Relationship(back_populates="rsu_grant")

class RSUVestingTranche(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rsu_grant_id: int = Field(foreign_key="rsugrantdetails.id")
    vesting_date: datetime
    percentage_of_grant: float  # e.g., 0.25 for 25%
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    rsu_grant: Optional[RSUGrantDetails] = Relationship(back_populates="vesting_tranches")

class CashDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", unique=True)
    balance: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    asset: Optional[Asset] = Relationship(back_populates="cash_details")

class Security(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(unique=True)
    name: Optional[str] = None
    assumed_appreciation_rate: float = Field(default=0.07)  # Default 7% annual return
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class IncomeSource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    name: str
    income_type: IncomeType
    start_age: int
    end_age: Optional[int] = None
    annual_amount: float
    inflation_adjusted: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    scenario: Optional[Scenario] = Relationship(back_populates="income_sources")

class RSUGrantForecast(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    employer: Optional[str] = None
    security_id: int = Field(foreign_key="security.id")
    grant_date: datetime
    grant_value_type: str  # "dollar_value" or "shares"
    grant_value: float
    grant_fmv_at_grant: float
    shares_granted: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    scenario: Optional[Scenario] = Relationship(back_populates="rsu_grant_forecasts")

class TaxFundingSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id", unique=True)
    
    # Tax funding order as JSON string (array of TaxFundingSource enums)
    # Default: ["CASH", "TAXABLE_BROKERAGE", "TRADITIONAL_RETIREMENT", "ROTH"]
    tax_funding_order_json: str = Field(default='["CASH", "TAXABLE_BROKERAGE", "TRADITIONAL_RETIREMENT", "ROTH"]')
    
    allow_retirement_withdrawals_for_taxes: bool = Field(default=True)
    if_insufficient_funds_behavior: InsufficientFundsBehavior = Field(default=InsufficientFundsBehavior.FAIL_WITH_SHORTFALL)
    
    # Tax table indexing policy
    tax_table_indexing_policy: TaxTableIndexingPolicy = Field(default=TaxTableIndexingPolicy.CONSTANT_NOMINAL)
    tax_table_custom_index_rate: Optional[float] = Field(default=None)  # Used only when CUSTOM_RATE (as decimal, e.g., 0.03 for 3%)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    scenario: Optional[Scenario] = Relationship(back_populates="tax_funding_settings")

class TaxTable(SQLModel, table=True):
    """
    Stores editable tax tables (brackets and standard deductions) for a scenario.
    Each record represents one jurisdiction (FED or CA) for one filing status.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    
    jurisdiction: str = Field(default="FED")  # "FED" or "CA"
    filing_status: FilingStatus = Field(default=FilingStatus.MARRIED_FILING_JOINTLY)
    year_base: int  # Base year the thresholds represent (typically scenario start year)
    
    # Store brackets as JSON: [{"up_to": float, "rate": float}, ...]
    brackets_json: str
    
    standard_deduction: float
    
    # Metadata
    schema_version: str = Field(default="1.0")
    notes: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    scenario: Optional[Scenario] = Relationship(back_populates="tax_tables")
    
    def get_brackets(self) -> List[dict]:
        """Parse brackets_json into a list of dicts."""
        return json.loads(self.brackets_json)
    
    def set_brackets(self, brackets: List[dict]):
        """Set brackets from a list of dicts."""
        self.brackets_json = json.dumps(brackets)
