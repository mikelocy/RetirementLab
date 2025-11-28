from typing import Dict, List
from sqlmodel import Session, select
from .models import Scenario, Asset, RealEstateDetails, GeneralEquityDetails
from .crud import get_assets_for_scenario

def calculate_mortgage_payment(principal: float, annual_rate: float, years: int) -> float:
    """Calculate monthly mortgage payment, then return annual payment."""
    if principal == 0 or annual_rate == 0 or years == 0:
        return 0.0
    monthly_rate = annual_rate / 12
    num_payments = years * 12
    if monthly_rate == 0:
        return principal / years
    monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
    return monthly_payment * 12

def run_simple_bond_simulation(session: Session, scenario_id: int) -> Dict:
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        return {}
    
    # Load assets with their detail relationships
    assets = get_assets_for_scenario(session, scenario_id)
    
    # Load detail records for each asset
    asset_details = {}
    for asset in assets:
        if asset.type == "real_estate":
            re_detail = session.exec(
                select(RealEstateDetails).where(RealEstateDetails.asset_id == asset.id)
            ).first()
            if re_detail:
                asset_details[asset.id] = {"type": "real_estate", "details": re_detail}
        elif asset.type == "general_equity":
            ge_detail = session.exec(
                select(GeneralEquityDetails).where(GeneralEquityDetails.asset_id == asset.id)
            ).first()
            if ge_detail:
                asset_details[asset.id] = {"type": "general_equity", "details": ge_detail}
    
    ages = []
    balance_nominal = []
    balance_real = []
    contribution_nominal_list = []
    spending_nominal_list = []
    
    # Detailed breakdown data
    asset_values = {}  # {asset_id: [values per year]}
    debt_values = {}  # {asset_id: [mortgage balances per year]}
    income_sources = {
        "salary": [],
        "rental_income": {}  # {asset_id: [values per year]}
    }
    
    # Initialize asset tracking
    for asset in assets:
        asset_values[asset.id] = []
        if asset.type == "real_estate" and asset.id in asset_details:
            re_detail = asset_details[asset.id]["details"]
            debt_values[asset.id] = []
            income_sources["rental_income"][asset.id] = []
        elif asset.type == "real_estate":
            # Real estate without details - still track it
            debt_values[asset.id] = []
            income_sources["rental_income"][asset.id] = []
    
    # Initialize starting values
    current_total_balance = sum(asset.current_balance for asset in assets)
    
    # Track per-asset state
    asset_states = {}
    
    print(f"DEBUG: Running simulation for scenario {scenario.id}. Range: {scenario.current_age} to {scenario.end_age}")
    
    for asset in assets:
        if asset.type == "real_estate" and asset.id in asset_details:
            re_detail = asset_details[asset.id]["details"]
            
            # Calculate remaining years
            # If current_year is 1, and term is 30, remaining is 30.
            remaining = max(0, re_detail.mortgage_term_years - re_detail.mortgage_current_year + 1)
            
            asset_states[asset.id] = {
                "property_value": re_detail.property_value,
                "mortgage_balance": re_detail.mortgage_balance or 0.0,
                "mortgage_years_remaining": remaining,
                "is_interest_only": re_detail.is_interest_only
            }
        elif asset.type == "general_equity" and asset.id in asset_details:
            ge_detail = asset_details[asset.id]["details"]
            asset_states[asset.id] = {
                "balance": ge_detail.account_balance
            }
        else:
            # Asset without details - use current_balance
            asset_states[asset.id] = {
                "balance": asset.current_balance
            }
    
    for age in range(scenario.current_age, scenario.end_age + 1):
        years_from_start = age - scenario.current_age
        
        ages.append(age)
        
        # Calculate per-asset values and income
        total_assets = 0.0
        total_debts = 0.0
        total_rental_income = 0.0
        
        # Calculate contribution/spending amounts first
        contribution_nominal = 0.0
        spending_nominal = 0.0
        if age < scenario.retirement_age:
            contribution_nominal = scenario.annual_contribution_pre_retirement * ((1 + scenario.inflation_rate) ** years_from_start)
        else:
            spending_nominal = scenario.annual_spending_in_retirement * ((1 + scenario.inflation_rate) ** years_from_start)
        
        # Track which general equity assets to add contributions to
        general_equity_assets = [a for a in assets if a.type == "general_equity"]
        
        for asset in assets:
            asset_id = asset.id
            
            if asset.type == "real_estate" and asset_id in asset_details:
                re_detail = asset_details[asset_id]["details"]
                state = asset_states[asset_id]
                
                # Property appreciation (use asset rate, or fallback to scenario bond rate)
                appreciation_rate = re_detail.appreciation_rate if re_detail.appreciation_rate > 0 else scenario.bond_return_rate
                state["property_value"] *= (1 + appreciation_rate)
                
                # Mortgage amortization
                if state["mortgage_balance"] > 0:
                    if state.get("is_interest_only", False):
                        # Interest only: Balance stays constant (unless manually paid down, not modeled yet)
                        pass
                    elif state["mortgage_years_remaining"] > 0:
                        annual_payment = calculate_mortgage_payment(
                            state["mortgage_balance"],
                            re_detail.interest_rate,
                            state["mortgage_years_remaining"]
                        )
                        interest_payment = state["mortgage_balance"] * re_detail.interest_rate
                        principal_payment = annual_payment - interest_payment
                        state["mortgage_balance"] = max(0, state["mortgage_balance"] - principal_payment)
                        state["mortgage_years_remaining"] -= 1
                
                # Asset value = property value - mortgage balance
                asset_value = state["property_value"] - state["mortgage_balance"]
                asset_values[asset_id].append(asset_value)
                debt_values[asset_id].append(state["mortgage_balance"])
                
                total_assets += asset_value
                total_debts += state["mortgage_balance"]
                
                # Rental income (inflation-adjusted)
                if re_detail.annual_rent > 0:
                    rental_income_nominal = re_detail.annual_rent * ((1 + scenario.inflation_rate) ** years_from_start)
                    income_sources["rental_income"][asset_id].append(rental_income_nominal)
                    total_rental_income += rental_income_nominal
                else:
                    income_sources["rental_income"][asset_id].append(0.0)
                    
            elif asset.type == "general_equity" and asset_id in asset_details:
                ge_detail = asset_details[asset_id]["details"]
                state = asset_states[asset_id]
                
                # Growth with return rate minus fees (use asset rate, or fallback to scenario bond rate)
                expected_return = ge_detail.expected_return_rate if ge_detail.expected_return_rate > 0 else scenario.bond_return_rate
                net_return = expected_return - ge_detail.fee_rate
                state["balance"] *= (1 + net_return)
                
                # Add annual contribution if specified in asset details
                if ge_detail.annual_contribution > 0 and age < scenario.retirement_age:
                    asset_contribution = ge_detail.annual_contribution * ((1 + scenario.inflation_rate) ** years_from_start)
                    state["balance"] += asset_contribution
                
                # Add scenario-level contribution (distribute evenly or to first asset)
                # For simplicity, add to first general equity asset
                if age < scenario.retirement_age and contribution_nominal > 0 and len(general_equity_assets) > 0:
                    if general_equity_assets[0].id == asset_id:
                        state["balance"] += contribution_nominal
                
                # Subtract spending (from first general equity asset)
                if age >= scenario.retirement_age and spending_nominal > 0 and len(general_equity_assets) > 0:
                    if general_equity_assets[0].id == asset_id:
                        state["balance"] = max(0, state["balance"] - spending_nominal)
                
                asset_values[asset_id].append(state["balance"])
                total_assets += state["balance"]
            else:
                # Asset without details - use current balance and scenario bond rate
                if asset_id not in asset_states:
                    asset_states[asset_id] = {"balance": asset.current_balance}
                state = asset_states[asset_id]
                state["balance"] *= (1 + scenario.bond_return_rate)
                asset_values[asset_id].append(state["balance"])
                total_assets += state["balance"]
        
        # Calculate income
        salary_income = 0.0
        if age < scenario.retirement_age:
            salary_income = scenario.annual_contribution_pre_retirement * ((1 + scenario.inflation_rate) ** years_from_start)
        income_sources["salary"].append(salary_income)
        
        # Portfolio balance = total assets (contributions and spending already applied above)
        current_total_balance = total_assets
        
        contribution_nominal_list.append(contribution_nominal)
        spending_nominal_list.append(spending_nominal)
        balance_nominal.append(current_total_balance)
        
        # Calculate real balance
        real_balance = current_total_balance / ((1 + scenario.inflation_rate) ** years_from_start)
        balance_real.append(real_balance)
    
    # Build asset names list
    asset_names = {asset.id: asset.name for asset in assets}
    
    # Build debt names (only for real estate with mortgages)
    debt_names = {}
    for asset in assets:
        if asset.type == "real_estate" and asset.id in asset_details:
            re_detail = asset_details[asset.id]["details"]
            if re_detail.mortgage_balance > 0:
                debt_names[asset.id] = f"{asset.name} Mortgage"
    
    return {
        "ages": ages,
        "balance_nominal": balance_nominal,
        "balance_real": balance_real,
        "contribution_nominal": contribution_nominal_list,
        "spending_nominal": spending_nominal_list,
        "asset_values": asset_values,
        "asset_names": asset_names,
        "debt_values": debt_values,
        "debt_names": debt_names,
        "income_sources": income_sources
    }
