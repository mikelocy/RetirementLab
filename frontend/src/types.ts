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

export type AssetType = "real_estate" | "general_equity";

export interface RealEstateDetailsCreate {
  property_type?: string; // e.g. "primary" | "rental" | "land"
  property_value: number;
  mortgage_balance?: number;
  interest_rate?: number;
  annual_property_tax?: number;
  annual_insurance?: number;
  annual_maintenance_pct?: number;
  annual_rent?: number;
  appreciation_rate?: number;
  mortgage_term_years?: number;
  mortgage_current_year?: number;
  is_interest_only?: boolean;
}

export interface GeneralEquityDetailsCreate {
  account_type?: string; // e.g. "taxable" | "ira" | "roth" | "401k"
  account_balance: number;
  expected_return_rate?: number;
  fee_rate?: number;
  annual_contribution?: number;
}

export interface RealEstateDetailsRead extends RealEstateDetailsCreate {
  id: number;
  asset_id: number;
}

export interface GeneralEquityDetailsRead extends GeneralEquityDetailsCreate {
  id: number;
  asset_id: number;
}

export interface Asset {
  id: number;
  scenario_id: number;
  name: string;
  type: string; // effectively AssetType
  current_balance: number;
  real_estate_details?: RealEstateDetailsRead;
  general_equity_details?: GeneralEquityDetailsRead;
}

export interface AssetCreate {
  name: string;
  type: AssetType;
  real_estate_details?: RealEstateDetailsCreate;
  general_equity_details?: GeneralEquityDetailsCreate;
}

export interface SimpleBondSimulationResult {
  ages: number[];
  balance_nominal: number[];
  balance_real: number[];
  contribution_nominal: number[];
  spending_nominal: number[];
  asset_values: { [assetId: number]: number[] };
  asset_names: { [assetId: number]: string };
  debt_values: { [assetId: number]: number[] };
  debt_names: { [assetId: number]: string };
  income_sources: {
    salary: number[];
    rental_income: { [assetId: number]: number[] };
  };
}
