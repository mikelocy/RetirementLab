from typing import Dict, List
from sqlmodel import Session
from .models import Scenario, Asset
from .crud import get_assets_for_scenario

def run_simple_bond_simulation(session: Session, scenario_id: int) -> Dict:
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        return {}
    
    assets = get_assets_for_scenario(session, scenario_id)
    starting_balance = sum(asset.current_balance for asset in assets)
    
    ages = []
    balance_nominal = []
    balance_real = []
    contribution_nominal_list = []
    spending_nominal_list = []
    
    current_balance = starting_balance
    
    for age in range(scenario.current_age, scenario.end_age + 1):
        years_from_start = age - scenario.current_age
        
        ages.append(age)
        
        # Calculate nominal values
        if age < scenario.retirement_age:
            contribution = scenario.annual_contribution_pre_retirement
            contribution_nominal = contribution * ((1 + scenario.inflation_rate) ** years_from_start)
            spending_nominal = 0.0
            
            # Prompt: balance = (balance + contribution_nominal) * (1 + bond_return_rate)
            current_balance = (current_balance + contribution_nominal) * (1 + scenario.bond_return_rate)
            
        else:
            contribution_nominal = 0.0
            spending = scenario.annual_spending_in_retirement
            spending_nominal = spending * ((1 + scenario.inflation_rate) ** years_from_start)
            
            # Prompt: balance = balance * (1 + bond_return_rate) - spending_nominal
            current_balance = current_balance * (1 + scenario.bond_return_rate) - spending_nominal
            
        contribution_nominal_list.append(contribution_nominal)
        spending_nominal_list.append(spending_nominal)
        balance_nominal.append(current_balance)
        
        # Calculate real balance
        real_balance = current_balance / ((1 + scenario.inflation_rate) ** years_from_start)
        balance_real.append(real_balance)
        
    return {
        "ages": ages,
        "balance_nominal": balance_nominal,
        "balance_real": balance_real,
        "contribution_nominal": contribution_nominal_list,
        "spending_nominal": spending_nominal_list
    }

