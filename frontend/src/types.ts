export interface Scenario {
  id: number;
  name: string;
  description?: string | null;
  current_age: number;
  retirement_age: number;
  end_age: number;
  inflation_rate: number;
  bond_return_rate: number;
  annual_contribution_pre_retirement: number;
  annual_spending_in_retirement: number;
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreate {
  name: string;
  description?: string | null;
  current_age: number;
  retirement_age: number;
  end_age: number;
  inflation_rate: number;
  bond_return_rate: number;
  annual_contribution_pre_retirement: number;
  annual_spending_in_retirement: number;
}

export interface Asset {
  id: number;
  scenario_id: number;
  name: string;
  type: string;
  current_balance: number;
}

export interface AssetCreate {
  name: string;
  type: string;
  current_balance: number;
}

export interface SimpleBondSimulationResult {
  ages: number[];
  balance_nominal: number[];
  balance_real: number[];
  contribution_nominal: number[];
  spending_nominal: number[];
}

