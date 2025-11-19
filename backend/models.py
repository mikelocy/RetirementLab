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

class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    name: str
    type: str
    current_balance: float

    scenario: Scenario = Relationship(back_populates="assets")

