from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

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

class AssetBase(BaseModel):
    name: str
    type: str
    current_balance: float

class AssetCreate(AssetBase):
    pass

class AssetRead(AssetBase):
    id: int
    scenario_id: int

