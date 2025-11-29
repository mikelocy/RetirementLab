from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class Scenario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    current_age: int
    retirement_age: int
    end_age: int
    inflation_rate: float
    bond_return_rate: float
    annual_contribution_pre_retirement: float
    annual_spending_in_retirement: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    assets: List["Asset"] = Relationship(back_populates="scenario")
    income_sources: List["IncomeSource"] = Relationship(back_populates="scenario")

class IncomeSource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    name: str
    amount: float
    start_age: int
    end_age: int
    appreciation_rate: float = 0.0
    
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
    
    asset: Optional[Asset] = Relationship(back_populates="real_estate_details")

class GeneralEquityDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    
    account_type: str = "taxable"  # e.g. "taxable", "ira", "roth", "401k"
    account_balance: float  # current balance in this account
    expected_return_rate: float = 0.0  # as decimal
    fee_rate: float = 0.0  # as decimal
    annual_contribution: float = 0.0  # optional, for future use
    
    asset: Optional[Asset] = Relationship(back_populates="general_equity_details")

class SpecificStockDetails(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    
    ticker: str
    shares_owned: float
    current_price: float
    assumed_appreciation_rate: float = 0.0
    dividend_yield: float = 0.0
    
    asset: Optional[Asset] = Relationship(back_populates="specific_stock_details")
