export type FilingStatus = "single" | "married_filing_jointly" | "married_filing_separately" | "head_of_household";

export interface Scenario {
  id: number;
  name: string;
  description?: string | null;
  current_age: number;
  base_year?: number | null;  // Calendar year corresponding to current_age
  retirement_age: number;
  end_age: number;
  inflation_rate: number;
  bond_return_rate: number;
  annual_contribution_pre_retirement: number;
  annual_spending_in_retirement: number;
  filing_status: FilingStatus;
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreate {
  name: string;
  description?: string | null;
  current_age: number;
  base_year?: number | null;  // Calendar year corresponding to current_age
  retirement_age: number;
  end_age: number;
  inflation_rate: number;
  bond_return_rate: number;
  annual_contribution_pre_retirement: number;
  annual_spending_in_retirement: number;
  filing_status?: FilingStatus;
}

export type AssetType = "real_estate" | "general_equity" | "specific_stock" | "rsu_grant";

export interface SpecificStockDetailsCreate {
  ticker: string;
  shares_owned: number;
  current_price: number;
  assumed_appreciation_rate?: number;
  dividend_yield?: number;
  cost_basis?: number; // Original purchase price per share * shares
}

export interface SpecificStockDetailsRead extends SpecificStockDetailsCreate {
  id: number;
  asset_id: number;
  source_type?: string;
  source_rsu_grant_id?: number | null;
}

export type DepreciationMethod = "none" | "residential_27_5" | "commercial_39";

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
  // Tax-related fields
  purchase_price?: number; // Original acquisition cost
  land_value?: number; // Portion that's land (not depreciable)
  depreciation_method?: DepreciationMethod;
  depreciation_start_year?: number | null; // Year depreciation began
  accumulated_depreciation?: number; // Total depreciation taken to date
  // Property sale fields
  sale_age?: number | null; // Age at which property will be sold
  primary_residence_start_age?: number | null; // Age when property became primary residence
  primary_residence_end_age?: number | null; // Age when property stopped being primary residence
}

export interface GeneralEquityDetailsCreate {
  account_type?: string; // e.g. "taxable" | "ira" | "roth" | "401k"
  account_balance: number;
  expected_return_rate?: number;
  fee_rate?: number;
  annual_contribution?: number;
  cost_basis?: number; // For taxable accounts - original purchase price
}

export interface RealEstateDetailsRead extends RealEstateDetailsCreate {
  id: number;
  asset_id: number;
}

export interface GeneralEquityDetailsRead extends GeneralEquityDetailsCreate {
  id: number;
  asset_id: number;
}

export type IncomeType = "ordinary" | "social_security" | "tax_exempt" | "disability";

export interface IncomeSourceCreate {
  name: string;
  amount: number;
  start_age: number;
  end_age: number;
  appreciation_rate?: number;
  source_type?: "income" | "drawdown" | "house_sale";
  linked_asset_id?: number | null;
  income_type?: IncomeType;
}

export interface IncomeSource {
  id: number;
  scenario_id: number;
  name: string;
  amount: number;
  start_age: number;
  end_age: number;
  appreciation_rate: number;
  source_type: "income" | "drawdown" | "house_sale";
  linked_asset_id?: number | null;
  income_type: IncomeType;
}

// Security/Ticker types
export interface Security {
  id: number;
  symbol: string;
  name?: string | null;
  assumed_appreciation_rate: number;  // Expected annual return (e.g., 0.07 = 7%)
}

export interface SecurityCreate {
  symbol: string;
  name?: string | null;
  assumed_appreciation_rate?: number;  // Optional, defaults to 0.0
}

// RSU Vesting Tranche types
export interface RSUVestingTrancheCreate {
  vesting_date: string; // ISO date string
  percentage_of_grant: number; // 0-1, e.g., 0.25 for 25%
}

export interface RSUVestingTrancheRead extends RSUVestingTrancheCreate {
  id: number;
  grant_id: number;
}

// RSU Grant Details types
export interface RSUGrantDetailsCreate {
  employer?: string | null;
  security_id: number;
  grant_date: string; // ISO date string
  grant_value_type?: string; // "dollar_value"
  grant_value: number;
  grant_fmv_at_grant: number; // Fair market value per share at grant
  shares_granted?: number; // Computed: grant_value / grant_fmv_at_grant
  estimated_share_withholding_rate?: number; // Default 0.37 - used only to estimate net shares delivered at vesting
  vesting_tranches: RSUVestingTrancheCreate[];
}

export interface RSUGrantDetailsRead {
  id: number;
  asset_id: number;
  employer?: string | null;
  security_id: number;
  grant_date: string;
  grant_value_type: string;
  grant_value: number;
  grant_fmv_at_grant: number;
  shares_granted: number;
  tax_withholding_rate: number;
  vesting_tranches: RSUVestingTrancheRead[];
}

// RSU Grant Forecast types
export interface RSUGrantForecastCreate {
  security_id: number;
  first_grant_date: string; // ISO date string
  grant_frequency?: string; // "annual", "quarterly", etc.
  grant_value: number;
  tax_withholding_rate?: number;
  vesting_schedule_years?: number; // Default 4
  vesting_cliff_years?: number; // Default 1.0
  vesting_frequency?: string; // "quarterly", "annual", etc.
}

export interface RSUGrantForecastRead extends RSUGrantForecastCreate {
  id: number;
  scenario_id: number;
}

// RSU Grant Details Response (from /api/assets/{id}/rsu_details)
export interface RSUGrantDetailsResponse {
  grant: {
    id: number;
    employer?: string | null;
    security: {
      id: number | null;
      symbol: string | null;
      name: string | null;
      assumed_appreciation_rate: number;
    };
    grant_date: string;
    grant_value: number;
    grant_fmv_at_grant: number;
    shares_granted: number;
    estimated_share_withholding_rate: number; // Used only to estimate net shares delivered at vesting
  };
  vesting_schedule: Array<{
    id: number;
    vesting_date: string;
    percentage_of_grant: number;
    shares_vesting: number;
  }>;
  unvested: {
    shares: number;
    percentage: number;
    estimated_value: number;
  };
  vested_lots: Array<{
    id: number;
    asset_id: number;
    vesting_date?: string | null;
    shares_held: number;
    basis_per_share: number;
    basis_total: number;
    current_price: number;
    current_value: number;
    unrealized_gain: number;
  }>;
}

export interface Asset {
  id: number;
  scenario_id: number;
  name: string;
  type: string; // effectively AssetType
  current_balance: number;
  real_estate_details?: RealEstateDetailsRead;
  general_equity_details?: GeneralEquityDetailsRead;
  specific_stock_details?: SpecificStockDetailsRead;
  rsu_grant_details?: RSUGrantDetailsRead;
}

export interface AssetCreate {
  name: string;
  type: AssetType;
  real_estate_details?: RealEstateDetailsCreate;
  general_equity_details?: GeneralEquityDetailsCreate;
  specific_stock_details?: SpecificStockDetailsCreate;
  rsu_grant_details?: RSUGrantDetailsCreate;
}

export interface SimpleBondSimulationResult {
  ages: number[];
  balance_nominal: number[];
  balance_real: number[];
  contribution_nominal: number[];
  spending_nominal: number[];
  net_cash_flow: number[];
  uncovered_spending: number[];
  asset_values: { [assetId: number]: number[] };
  asset_names: { [assetId: number]: string };
  debt_values: { [assetId: number]: number[] };
  debt_names: { [assetId: number]: string };
  income_sources: {
    salary: number[];
    rental_income: { [assetId: number]: number[] };
    specific_income: { [sourceId: number]: number[] };
  };
  income_names: { [sourceId: number]: string };
  tax_simulation?: {
    federal_tax: number[];
    state_tax: number[];
    total_tax: number[];
    effective_tax_rate: number[];
  };
}
