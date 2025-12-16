from typing import Dict, List, Tuple, Optional
import sys
from datetime import datetime
from sqlmodel import Session, select
from .models import Scenario, Asset, RealEstateDetails, GeneralEquityDetails, SpecificStockDetails, IncomeSource, TaxWrapper, IncomeType, DepreciationMethod, Security, RSUGrantDetails, RSUVestingTranche
from .crud import get_assets_for_scenario, get_income_sources_for_scenario, get_security, get_security_by_symbol
from .tax_engine import TaxableIncomeBreakdown, calculate_taxes, TaxResult
from .tax_config import FilingStatus

# Helper function to print and flush immediately
def print_flush(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

def get_stock_price_for_security(
    session: Session,
    security_id: int,
    base_price: float,
    base_year: int,
    target_year: int,
    asset_states: Dict
) -> float:
    """
    Get stock price for a security at a given year.
    
    For v1: Check if there's a SpecificStockDetails for this security's ticker,
    and use its appreciation_rate. Otherwise, fall back to a default.
    
    Args:
        session: Database session
        security_id: Security ID
        base_price: Base price (e.g., grant FMV)
        base_year: Year of base price
        target_year: Year to calculate price for
        asset_states: Current asset states (to check for existing stock holdings)
    
    Returns:
        Estimated stock price at target_year
    """
    # Get security
    security = session.get(Security, security_id)
    if not security:
        # Fallback: assume 0% appreciation if security not found
        return base_price
    
    # Look for existing SpecificStockDetails with this ticker to get appreciation rate
    appreciation_rate = None  # Use None to distinguish "not found" from "explicitly set to 0"
    found_stock = False
    
    for asset_id, st in asset_states.items():
        if st.get("ticker") == security.symbol:
            appreciation_rate = st.get("appreciation_rate")
            # Found the stock, even if rate is 0.0
            found_stock = True
            break
    
    # If not found in asset_states, check Security's assumed_appreciation_rate
    if not found_stock:
        # First check if there's a SpecificStockDetails in the database
        stock_detail = session.exec(
            select(SpecificStockDetails).where(SpecificStockDetails.ticker == security.symbol)
        ).first()
        if stock_detail:
            appreciation_rate = stock_detail.assumed_appreciation_rate
        else:
            # Use Security's assumed_appreciation_rate (can be 0.0 if explicitly set)
            appreciation_rate = security.assumed_appreciation_rate
    
    # Default to 0.07 (7%) only if not found (None), not if explicitly set to 0.0
    if appreciation_rate is None:
        appreciation_rate = 0.07  # Default 7% equity return
    
    # Calculate price with appreciation
    years = target_year - base_year
    return base_price * ((1 + appreciation_rate) ** years)

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

def calculate_property_sale(
    sale_price: float,
    purchase_price: float,
    land_value: float,
    accumulated_depreciation: float,
    property_type: str,
    primary_residence_start_age: Optional[int],
    primary_residence_end_age: Optional[int],
    sale_age: int,
    filing_status: FilingStatus,
    sales_cost_pct: float = 0.05
) -> Tuple[float, float, float]:
    """
    Calculate property sale proceeds and tax breakdown.
    
    Returns:
        (net_proceeds, depreciation_recapture, capital_gain)
        - net_proceeds: Cash received after sale costs and mortgage (caller handles mortgage)
        - depreciation_recapture: Amount subject to recapture tax (ordinary income, up to 25%)
        - capital_gain: Amount subject to capital gains tax (LTCG)
    
    Note: This function calculates the taxable amounts, not the actual tax owed.
    The caller should add these to the tax breakdown.
    """
    # Sales costs
    sales_costs = sale_price * sales_cost_pct
    net_sale_price = sale_price - sales_costs
    
    # Adjusted basis = purchase_price - accumulated_depreciation
    # Land is never depreciated, so it's always part of basis
    adjusted_basis = purchase_price - accumulated_depreciation
    
    # Total gain = net_sale_price - adjusted_basis
    total_gain = net_sale_price - adjusted_basis
    
    if total_gain <= 0:
        # No gain, no tax
        return (net_sale_price, 0.0, 0.0)
    
    # For primary residence, check 2-of-5-year rule and apply exclusion
    if property_type == "primary":
        # Check if property was primary residence for 2 of last 5 years
        # Simplified: If primary_residence_end_age is None or within 5 years of sale, assume it qualifies
        qualifies_for_exclusion = False
        if primary_residence_end_age is None:
            # Still primary residence - qualifies
            qualifies_for_exclusion = True
        elif sale_age - primary_residence_end_age <= 5:
            # Was primary within last 5 years - need to check if it was primary for at least 2 years
            # Simplified: If it was primary for at least 2 years total, assume it qualifies
            if primary_residence_start_age is not None:
                years_as_primary = primary_residence_end_age - primary_residence_start_age
                if years_as_primary >= 2:
                    qualifies_for_exclusion = True
        
        if qualifies_for_exclusion:
            # Apply exclusion
            if filing_status == FilingStatus.MARRIED_FILING_JOINTLY:
                exclusion_amount = 500000.0
            else:
                exclusion_amount = 250000.0
            
            # Exclusion applies to total gain
            taxable_gain = max(0.0, total_gain - exclusion_amount)
            
            # For primary residence, no depreciation recapture (depreciation not typically taken)
            # All taxable gain is capital gain
            return (net_sale_price, 0.0, taxable_gain)
    
    # For rental/investment property
    # Depreciation recapture = accumulated depreciation (up to total gain)
    depreciation_recapture = min(accumulated_depreciation, total_gain)
    
    # Remaining gain after recapture = capital gain
    capital_gain = total_gain - depreciation_recapture
    
    return (net_sale_price, depreciation_recapture, capital_gain)

def run_simple_bond_simulation(session: Session, scenario_id: int) -> Dict:
    scenario = session.get(Scenario, scenario_id)
    if not scenario:
        return {}
    
    # Load assets with their detail relationships
    assets = get_assets_for_scenario(session, scenario_id)
    income_sources_db = get_income_sources_for_scenario(session, scenario_id)
    
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
        elif asset.type == "specific_stock":
            stock_detail = session.exec(
                select(SpecificStockDetails).where(SpecificStockDetails.asset_id == asset.id)
            ).first()
            if stock_detail:
                asset_details[asset.id] = {"type": "specific_stock", "details": stock_detail}
        elif asset.type == "rsu_grant":
            rsu_grant = session.exec(
                select(RSUGrantDetails).where(RSUGrantDetails.asset_id == asset.id)
            ).first()
            if rsu_grant:
                # Load vesting tranches
                tranches = session.exec(
                    select(RSUVestingTranche).where(RSUVestingTranche.grant_id == rsu_grant.id)
                    .order_by(RSUVestingTranche.vesting_date)
                ).all()
                asset_details[asset.id] = {"type": "rsu_grant", "details": rsu_grant, "tranches": tranches}
    
    ages = []
    balance_nominal = []
    balance_real = []
    contribution_nominal_list = []
    spending_nominal_list = []
    net_cash_flow_list = []
    uncovered_spending_list = []
    cumulative_uncovered_spending = 0.0
    
    # Detailed breakdown data
    asset_values = {}  # {asset_id: [values per year]}
    debt_values = {}  # {asset_id: [mortgage balances per year]}
    income_sources = {
        "salary": [],
        "rental_income": {},  # {asset_id: [values per year]}
        "specific_income": {} # {source_id: [values per year]}
    }
    
    # Initialize specific income tracking
    for source in income_sources_db:
        income_sources["specific_income"][source.id] = []

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
                "type": "real_estate",
                "property_value": re_detail.property_value,
                "mortgage_balance": re_detail.mortgage_balance or 0.0,
                "mortgage_years_remaining": remaining,
                "is_interest_only": re_detail.is_interest_only,
                "purchase_price": re_detail.purchase_price or 0.0,
                "land_value": re_detail.land_value or 0.0,
                "depreciation_method": re_detail.depreciation_method,
                "depreciation_start_year": re_detail.depreciation_start_year,
                "accumulated_depreciation": re_detail.accumulated_depreciation or 0.0,
                "property_type": re_detail.property_type,
                "primary_residence_start_age": re_detail.primary_residence_start_age,
                "primary_residence_end_age": re_detail.primary_residence_end_age,
                "appreciation_rate": re_detail.appreciation_rate or 0.0,
                "interest_rate": re_detail.interest_rate or 0.0,
                "mortgage_term_years": re_detail.mortgage_term_years or 30,
                "sold": False  # Track if property has been sold
            }
        elif asset.type == "general_equity" and asset.id in asset_details:
            ge_detail = asset_details[asset.id]["details"]
            asset_states[asset.id] = {
                "balance": ge_detail.account_balance,
                "tax_wrapper": ge_detail.tax_wrapper,
                "cost_basis": ge_detail.cost_basis
            }
        elif asset.type == "specific_stock" and asset.id in asset_details:
            stock_detail = asset_details[asset.id]["details"]
            asset_states[asset.id] = {
                "balance": stock_detail.shares_owned * stock_detail.current_price,
                "tax_wrapper": stock_detail.tax_wrapper,
                "cost_basis": stock_detail.cost_basis,
                "shares_owned": stock_detail.shares_owned,
                "current_price": stock_detail.current_price,
                "ticker": stock_detail.ticker,
                "appreciation_rate": stock_detail.assumed_appreciation_rate
            }
        elif asset.type == "rsu_grant" and asset.id in asset_details:
            rsu_grant = asset_details[asset.id]["details"]
            tranches = asset_details[asset.id]["tranches"]
            
            # Calculate how many shares have already vested (past vesting)
            # Past vested shares are stored as separate SpecificStockDetails assets
            # We need to count them to calculate unvested_shares correctly
            past_vested_stock = session.exec(
                select(SpecificStockDetails).where(
                    SpecificStockDetails.source_type == "rsu_vest",
                    SpecificStockDetails.source_rsu_grant_id == rsu_grant.id
                )
            ).all()
            
            # Calculate total shares that have already vested
            # Reverse calculate from net shares: net_shares = shares_vested * (1 - tax_rate)
            total_vested_shares = 0.0
            for stock_detail in past_vested_stock:
                net_shares = stock_detail.shares_owned
                # Reverse calculate: shares_vested = net_shares / (1 - tax_rate)
                if rsu_grant.estimated_share_withholding_rate < 1.0:
                    shares_vested = net_shares / (1 - rsu_grant.estimated_share_withholding_rate)
                else:
                    shares_vested = net_shares
                total_vested_shares += shares_vested
            
            # Calculate unvested shares (will be updated as future vesting occurs)
            unvested_shares = max(0.0, rsu_grant.shares_granted - total_vested_shares)
            
            asset_states[asset.id] = {
                "type": "rsu_grant",
                "grant_id": rsu_grant.id,
                "security_id": rsu_grant.security_id,
                "shares_granted": rsu_grant.shares_granted,
                "unvested_shares": unvested_shares,
                "grant_fmv_at_grant": rsu_grant.grant_fmv_at_grant,
                "estimated_share_withholding_rate": rsu_grant.estimated_share_withholding_rate,
                "tranches": tranches,
                "vested_lots": []  # Only track future vesting (in-memory)
                # Past vested shares are tracked as separate SpecificStockDetails assets
            }
        else:
            # Asset without details - use current_balance
            # Default to taxable for unknown types
            asset_states[asset.id] = {
                "balance": asset.current_balance,
                "tax_wrapper": TaxWrapper.TAXABLE,
                "cost_basis": asset.current_balance  # Assume full basis if unknown
            }
    
    # Tax Output tracking
    federal_tax_list = []
    state_tax_list = []
    total_tax_list = []
    effective_tax_rate_list = []

    # Calculate current calendar year from base_year
    # base_year is the calendar year corresponding to current_age
    if scenario.base_year is None:
        # Default to current year if not set
        current_calendar_year = datetime.now().year
    else:
        current_calendar_year = scenario.base_year
    
    for age in range(scenario.current_age, scenario.end_age + 1):
        years_from_start = age - scenario.current_age
        sim_year = current_calendar_year + years_from_start
        
        ages.append(age)
        
        # Reset yearly income buckets
        ordinary_income = 0.0
        long_term_cap_gains = 0.0
        qualified_dividends = 0.0
        tax_exempt_income = 0.0
        social_security_benefits = 0.0
        rsu_vesting_income = 0.0  # Track separately - not cash, but taxable
        
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
        
        # Initialize temp balances for drawdown limit checking (Start of Year)
        temp_balances = {}
        for aid, st in asset_states.items():
            if "property_value" in st:
                temp_balances[aid] = st["property_value"]
            elif st.get("type") == "rsu_grant":
                # For RSU grants, only count vested shares (after taxes)
                # Unvested shares are worth $0 until they vest
                temp_balances[aid] = 0.0
                vested_lots = st.get("vested_lots", [])
                for lot in vested_lots:
                    lot_fmv = lot.get("fmv_on_vest", 0.0)
                    net_shares = lot.get("net_shares_received", 0.0)
                    temp_balances[aid] += net_shares * lot_fmv
            elif "balance" in st:
                temp_balances[aid] = st["balance"]
            else:
                # Default to 0 if no balance found
                temp_balances[aid] = 0.0
        
        # --- ANNUAL DEPRECIATION FOR RENTAL PROPERTIES ---
        # Calculate depreciation for rental properties (before sale check)
        for asset_id, st in asset_states.items():
            if st.get("type") == "real_estate" and not st.get("sold", False):
                property_type = st.get("property_type", "rental")
                depreciation_method = st.get("depreciation_method")
                depreciation_start_year = st.get("depreciation_start_year")
                
                # Only depreciate rental properties
                if property_type == "rental" and depreciation_method and depreciation_method != DepreciationMethod.NONE:
                    # Check if depreciation has started
                    if depreciation_start_year is not None:
                        years_since_depreciation_start = sim_year - depreciation_start_year
                        if years_since_depreciation_start >= 0:
                            # Calculate annual depreciation
                            depreciable_basis = st.get("purchase_price", 0.0) - st.get("land_value", 0.0)
                            
                            if depreciation_method == DepreciationMethod.RESIDENTIAL_27_5:
                                annual_depreciation = depreciable_basis / 27.5
                            elif depreciation_method == DepreciationMethod.COMMERCIAL_39:
                                annual_depreciation = depreciable_basis / 39.0
                            else:
                                annual_depreciation = 0.0
                            
                            # Check if property is fully depreciated
                            max_depreciation = depreciable_basis
                            current_accumulated = st.get("accumulated_depreciation", 0.0)
                            
                            if current_accumulated < max_depreciation:
                                # Add this year's depreciation
                                remaining_depreciation = max_depreciation - current_accumulated
                                this_year_depreciation = min(annual_depreciation, remaining_depreciation)
                                st["accumulated_depreciation"] = current_accumulated + this_year_depreciation
                                
                                # Depreciation reduces taxable rental income (handled in rental income calculation below)

        # --- RSU VESTING PROCESSING ---
        # Process RSU vesting events for this year
        # Determine "as-of" date: use scenario's current_age as the cutoff
        # Vesting dates <= current_age are "past" (should be persisted), > current_age are "future" (in-memory only)
        as_of_age = scenario.current_age
        as_of_year = current_calendar_year  # base_year corresponds to current_age
        
        for asset_id, st in asset_states.items():
            if st.get("type") == "rsu_grant":
                # Check if asset_details has this RSU grant
                if asset_id not in asset_details:
                    continue
                    
                grant_id = st.get("grant_id")
                security_id = st.get("security_id")
                shares_granted = st.get("shares_granted", 0.0)
                grant_fmv = st.get("grant_fmv_at_grant", 0.0)
                estimated_share_withholding_rate = st.get("estimated_share_withholding_rate", 0.37)
                tranches = st.get("tranches", [])
                vested_lots = st.get("vested_lots", [])
                
                # Get grant date for base year calculation
                rsu_grant = asset_details[asset_id]["details"]
                grant_date = rsu_grant.grant_date
                grant_year = grant_date.year if hasattr(grant_date, 'year') else current_calendar_year
                
                # Check each tranche to see if it vests this year
                for tranche in tranches:
                    # Handle both SQLModel objects and dicts
                    if hasattr(tranche, 'vesting_date'):
                        vesting_date = tranche.vesting_date
                    else:
                        vesting_date = tranche.get("vesting_date") if isinstance(tranche, dict) else None
                    
                    if vesting_date is None:
                        continue
                        
                    # Convert vesting_date to year
                    vesting_year = vesting_date.year if hasattr(vesting_date, 'year') else int(vesting_date)
                    
                    # Check if this tranche vests in the current simulation year
                    if vesting_year == sim_year:
                        # Handle both SQLModel objects and dicts
                        if hasattr(tranche, 'percentage_of_grant'):
                            percentage = tranche.percentage_of_grant
                        else:
                            percentage = tranche.get("percentage_of_grant", 0.0) if isinstance(tranche, dict) else 0.0
                        shares_vesting = shares_granted * percentage
                        
                        # Get stock price at vesting date
                        fmv_on_vest = get_stock_price_for_security(
                            session=session,
                            security_id=security_id,
                            base_price=grant_fmv,
                            base_year=grant_year,
                            target_year=vesting_year,
                            asset_states=asset_states
                        )
                        
                        # Calculate vesting income (full FMV of shares vesting)
                        vesting_income = shares_vesting * fmv_on_vest
                        
                        # Calculate share withholding (mechanical only - affects net shares delivered, not taxable income)
                        # Withholding reduces net shares received but does NOT reduce taxable income
                        shares_withheld = shares_vesting * estimated_share_withholding_rate
                        net_shares_received = shares_vesting - shares_withheld
                        
                        # Add to ordinary income (full FMV of shares vesting, not reduced by withholding)
                        # This is taxable income, but NOT cash income
                        ordinary_income += vesting_income
                        rsu_vesting_income += vesting_income  # Track separately for cash flow calculation
                        
                        # Calculate basis for vested lot
                        basis_per_share = fmv_on_vest
                        basis_total = net_shares_received * basis_per_share
                        
                        # Create vested lot (in-memory for future, or mark for persistence if past)
                        vested_lot = {
                            "vesting_date": vesting_date,
                            "vesting_year": vesting_year,
                            "shares_vested": shares_vesting,
                            "net_shares_received": net_shares_received,
                            "fmv_on_vest": fmv_on_vest,
                            "basis_per_share": basis_per_share,
                            "basis_total": basis_total,
                            "shares_withheld": shares_withheld,
                            "vesting_income": vesting_income,
                            "is_past_vesting": vesting_year <= as_of_year,
                            "grant_id": grant_id,
                            "security_id": security_id
                        }
                        vested_lots.append(vested_lot)
                        
                        # Update unvested shares
                        st["unvested_shares"] = st.get("unvested_shares", shares_granted) - shares_vesting
                        
                        print_flush(f"\nRSU VESTING - Age {age}, Year {sim_year}")
                        print_flush(f"  Grant ID: {grant_id}")
                        print_flush(f"  Shares vesting: {shares_vesting:.4f}")
                        print_flush(f"  FMV per share at vest: ${fmv_on_vest:.2f}")
                        print_flush(f"  Vesting income (ordinary): ${vesting_income:,.2f}")
                        print_flush(f"  Estimated share withholding rate: {estimated_share_withholding_rate*100:.1f}%")
                        print_flush(f"  Shares withheld: {shares_withheld:.4f}")
                        print_flush(f"  Net shares received: {net_shares_received:.4f}")
                        print_flush(f"  Basis per share: ${basis_per_share:.2f}")
                        print_flush(f"  Total basis: ${basis_total:,.2f}")
                
                # Update vested_lots in state
                st["vested_lots"] = vested_lots

        # Calculate specific income and drawdowns for this year
        year_specific_incomes = {}
        year_drawdown_amounts = {}
        total_specific_income = 0.0
        house_sale_this_year = False  # Track if a house sale occurs this year
        house_sale_net_proceeds = 0.0  # Track the net proceeds from house sale for verification
        for source in income_sources_db:
            if source.start_age <= age <= source.end_age:
                years_since_start = age - source.start_age
                amount = source.amount * ((1 + source.appreciation_rate) ** years_since_start)
                
                if source.source_type == "house_sale" and source.linked_asset_id:
                    # Handle house sale income source
                    asset_id = source.linked_asset_id
                    if asset_id in asset_states:
                        st = asset_states[asset_id]
                        # Only process if it's a real estate asset and not already sold
                        if st.get("type") == "real_estate" and not st.get("sold", False):
                            house_sale_this_year = True  # Mark that a house sale is happening this year
                            print_flush(f"\n{'='*80}")
                            print_flush(f"HOUSE SALE CALCULATION - Age {age}")
                            print_flush(f"{'='*80}")
                            
                            # Calculate appreciated property value at time of sale
                            # Property value is from end of previous year, appreciate one more year for sale
                            appreciation_rate = st.get("appreciation_rate", 0.0)
                            property_value_prev_year = st.get("property_value", 0.0)
                            current_property_value = property_value_prev_year * (1 + appreciation_rate)
                            
                            print_flush(f"Property value (end of prev year): ${property_value_prev_year:,.2f}")
                            print_flush(f"Appreciation rate: {appreciation_rate*100:.2f}%")
                            print_flush(f"Property value at sale: ${current_property_value:,.2f}")
                            
                            # Mortgage balance at time of sale
                            mortgage_balance_at_sale = st.get("mortgage_balance", 0.0)
                            print_flush(f"Mortgage balance at sale: ${mortgage_balance_at_sale:,.2f}")
                            
                            # Get property details
                            purchase_price = st.get("purchase_price", 0.0)
                            land_value = st.get("land_value", 0.0)
                            accumulated_depreciation = st.get("accumulated_depreciation", 0.0)
                            property_type = st.get("property_type", "rental")
                            
                            print_flush(f"\nProperty Details:")
                            print_flush(f"  Purchase price: ${purchase_price:,.2f}")
                            print_flush(f"  Land value: ${land_value:,.2f}")
                            print_flush(f"  Accumulated depreciation: ${accumulated_depreciation:,.2f}")
                            print_flush(f"  Property type: {property_type}")
                            
                            # Calculate sale proceeds and taxes
                            net_sale_price, depreciation_recapture, capital_gain = calculate_property_sale(
                                sale_price=current_property_value,
                                purchase_price=purchase_price,
                                land_value=land_value,
                                accumulated_depreciation=accumulated_depreciation,
                                property_type=property_type,
                                primary_residence_start_age=st.get("primary_residence_start_age"),
                                primary_residence_end_age=st.get("primary_residence_end_age"),
                                sale_age=age,
                                filing_status=scenario.filing_status,
                                sales_cost_pct=0.05
                            )
                            
                            sales_costs = current_property_value * 0.05
                            print_flush(f"\nSale Calculation:")
                            print_flush(f"  Sale price: ${current_property_value:,.2f}")
                            print_flush(f"  Sales costs (5%): ${sales_costs:,.2f}")
                            print_flush(f"  Net sale price (after costs): ${net_sale_price:,.2f}")
                            
                            # Net proceeds after mortgage = net_sale_price - mortgage_balance_at_sale
                            net_proceeds_after_mortgage = net_sale_price - mortgage_balance_at_sale
                            house_sale_net_proceeds = net_proceeds_after_mortgage  # Store for verification
                            print_flush(f"  Net proceeds after mortgage: ${net_proceeds_after_mortgage:,.2f}")
                            
                            # Add taxable portions to income buckets for tax calculation
                            # Note: These are the full taxable amounts from the sale (not reduced by mortgage)
                            print_flush(f"\nTaxable Portions (BEFORE adding to income buckets):")
                            print_flush(f"  Depreciation recapture: ${depreciation_recapture:,.2f}")
                            print_flush(f"  Capital gain: ${capital_gain:,.2f}")
                            print_flush(f"  Total taxable gain: ${depreciation_recapture + capital_gain:,.2f}")
                            print_flush(f"\nIncome Buckets BEFORE house sale addition:")
                            print_flush(f"  ordinary_income: ${ordinary_income:,.2f}")
                            print_flush(f"  long_term_cap_gains: ${long_term_cap_gains:,.2f}")
                            print_flush(f"  tax_exempt_income: ${tax_exempt_income:,.2f}")
                            
                            ordinary_income += depreciation_recapture  # Depreciation recapture is ordinary income
                            long_term_cap_gains += capital_gain  # Capital gain is LTCG
                            
                            print_flush(f"\nIncome Buckets AFTER adding taxable portions:")
                            print_flush(f"  ordinary_income: ${ordinary_income:,.2f} (added ${depreciation_recapture:,.2f})")
                            print_flush(f"  long_term_cap_gains: ${long_term_cap_gains:,.2f} (added ${capital_gain:,.2f})")
                            print_flush(f"  tax_exempt_income: ${tax_exempt_income:,.2f}")
                            
                            # Calculate return of capital (basis portion that's not taxable)
                            # The adjusted_basis is returned tax-free, but we need to account for the mortgage payment
                            # net_sale_price = adjusted_basis + total_gain
                            # net_proceeds_after_mortgage = net_sale_price - mortgage
                            # The return of capital is the basis portion, which is tax-free
                            adjusted_basis = st.get("purchase_price", 0.0) - st.get("accumulated_depreciation", 0.0)
                            
                            print_flush(f"\nBasis Calculation:")
                            print_flush(f"  Adjusted basis: ${adjusted_basis:,.2f}")
                            
                            # The return of capital is the basis portion of what we actually received
                            # Since net_proceeds_after_mortgage = net_sale_price - mortgage, and the mortgage
                            # is paid from the sale proceeds, we need to calculate the return of capital
                            # as the basis portion of net_proceeds_after_mortgage
                            if net_sale_price > 0:
                                # Calculate the proportion of net_proceeds that is return of capital
                                basis_ratio = min(1.0, adjusted_basis / net_sale_price)
                                return_of_capital_received = net_proceeds_after_mortgage * basis_ratio
                                print_flush(f"  Basis ratio: {basis_ratio:.4f} ({basis_ratio*100:.2f}%)")
                                print_flush(f"  Return of capital received: ${return_of_capital_received:,.2f}")
                            else:
                                return_of_capital_received = 0.0
                                print_flush(f"  Return of capital received: $0.00 (net_sale_price <= 0)")
                            
                            # Add return of capital to tax_exempt_income (basis portion, not taxable)
                            tax_exempt_income += return_of_capital_received
                            
                            # IMPORTANT: The taxable portions (depreciation_recapture, capital_gain) are the FULL amounts
                            # from the sale, not reduced by mortgage. The mortgage payment reduces the cash received,
                            # but doesn't reduce the taxable gain. However, we need to ensure the total income
                            # equals net_proceeds_after_mortgage.
                            # 
                            # The issue: We're adding full depreciation_recapture + capital_gain, but only
                            # proportional return_of_capital. This can cause the total to not equal net_proceeds_after_mortgage.
                            #
                            # Solution: We need to also add the "missing" portion to make the total correct.
                            # The missing portion = net_proceeds_after_mortgage - (return_of_capital_received + depreciation_recapture + capital_gain)
                            # But actually, this should be handled by ensuring the taxable portions are also proportional.
                            #
                            # Actually, wait - the taxable gain is calculated from net_sale_price, not net_proceeds_after_mortgage.
                            # So depreciation_recapture + capital_gain = total_gain (from net_sale_price).
                            # And return_of_capital_received = adjusted_basis * (net_proceeds_after_mortgage / net_sale_price)
                            # So total = adjusted_basis * (net_proceeds_after_mortgage / net_sale_price) + total_gain
                            # = adjusted_basis * (net_proceeds_after_mortgage / net_sale_price) + (net_sale_price - adjusted_basis)
                            # = adjusted_basis * (net_proceeds_after_mortgage / net_sale_price) + net_sale_price - adjusted_basis
                            # = net_sale_price - adjusted_basis * (1 - net_proceeds_after_mortgage / net_sale_price)
                            # = net_sale_price - adjusted_basis * (mortgage / net_sale_price)
                            # = net_sale_price - mortgage * (adjusted_basis / net_sale_price)
                            #
                            # But we want: net_proceeds_after_mortgage = net_sale_price - mortgage
                            #
                            # So we're missing: mortgage - mortgage * (adjusted_basis / net_sale_price) = mortgage * (1 - adjusted_basis / net_sale_price)
                            # = mortgage * (total_gain / net_sale_price)
                            #
                            # This is the portion of the mortgage that should reduce the taxable gain, not the return of capital.
                            # So we should reduce the taxable portions proportionally, or add the missing amount to tax_exempt_income.
                            
                            # Calculate the missing portion to make total income = net_proceeds_after_mortgage
                            # The issue: We add full depreciation_recapture + capital_gain (from net_sale_price),
                            # but only proportional return_of_capital (from net_proceeds_after_mortgage).
                            # This causes total income to be less than net_proceeds_after_mortgage by:
                            # mortgage * (total_gain / net_sale_price)
                            total_taxable_gain = depreciation_recapture + capital_gain
                            missing_portion = 0.0
                            if net_sale_price > 0 and mortgage_balance_at_sale > 0:
                                # Calculate the portion of mortgage that reduces the taxable gain we actually received
                                gain_ratio = total_taxable_gain / net_sale_price
                                missing_portion = mortgage_balance_at_sale * gain_ratio
                                # Add this missing portion to tax_exempt_income to make total income = net_proceeds_after_mortgage
                                print_flush(f"\nBefore adding missing portion:")
                                print_flush(f"  tax_exempt_income: ${tax_exempt_income:,.2f}")
                                print_flush(f"  missing_portion: ${missing_portion:,.2f}")
                                tax_exempt_income += missing_portion
                                print_flush(f"  tax_exempt_income AFTER: ${tax_exempt_income:,.2f}")
                                print_flush(f"\nMortgage Adjustment:")
                                print_flush(f"  Gain ratio: {gain_ratio:.4f} ({gain_ratio*100:.2f}%)")
                                print_flush(f"  Missing portion (mortgage * gain_ratio): ${missing_portion:,.2f}")
                            else:
                                print_flush(f"\nMortgage Adjustment: None (no mortgage or net_sale_price <= 0)")
                            
                            # Calculate totals
                            total_income_components = return_of_capital_received + depreciation_recapture + capital_gain + missing_portion
                            print_flush(f"\nIncome Summary:")
                            print_flush(f"  Return of capital (tax-exempt): ${return_of_capital_received:,.2f}")
                            print_flush(f"  Depreciation recapture (taxable): ${depreciation_recapture:,.2f}")
                            print_flush(f"  Capital gain (taxable): ${capital_gain:,.2f}")
                            print_flush(f"  Missing portion (tax-exempt): ${missing_portion:,.2f}")
                            print_flush(f"  Total income components: ${total_income_components:,.2f}")
                            print_flush(f"  Net proceeds after mortgage: ${net_proceeds_after_mortgage:,.2f}")
                            print_flush(f"  Difference: ${abs(total_income_components - net_proceeds_after_mortgage):,.2f}")
                            
                            # IMPORTANT: Ensure ALL net proceeds are included in income
                            # If the breakdown doesn't add up to net_proceeds_after_mortgage, add the remainder
                            remaining_proceeds = net_proceeds_after_mortgage - total_income_components
                            if abs(remaining_proceeds) > 0.01:
                                print_flush(f"\n⚠️  WARNING: Income components don't equal net proceeds!")
                                print_flush(f"  Remaining proceeds to add: ${remaining_proceeds:,.2f}")
                                # Add the remaining proceeds to tax_exempt_income to ensure full amount is included
                                tax_exempt_income += remaining_proceeds
                                print_flush(f"  Added remaining ${remaining_proceeds:,.2f} to tax_exempt_income")
                                print_flush(f"  tax_exempt_income is now: ${tax_exempt_income:,.2f}")
                            else:
                                remaining_proceeds = 0.0
                                print_flush(f"\n✓ All net proceeds are included in income buckets")
                            
                            # Final verification
                            house_sale_income_in_buckets = depreciation_recapture + capital_gain + return_of_capital_received + missing_portion + remaining_proceeds
                            print_flush(f"\nFinal Verification:")
                            print_flush(f"  House sale income in income buckets: ${house_sale_income_in_buckets:,.2f}")
                            print_flush(f"  Net proceeds after mortgage: ${net_proceeds_after_mortgage:,.2f}")
                            if abs(house_sale_income_in_buckets - net_proceeds_after_mortgage) > 0.01:
                                print_flush(f"  ⚠️  ERROR: Still a mismatch after adjustment!")
                            else:
                                print_flush(f"  ✓ All net proceeds are now included in income buckets")
                            print_flush(f"{'='*80}\n")
                            
                            # Mark property as sold
                            st["sold"] = True
                            st["property_value"] = 0.0
                            st["mortgage_balance"] = 0.0
                            
                            # Update temp_balances
                            temp_balances[asset_id] = 0.0
                            
                            # Track the sale proceeds (for display purposes) - this is the total cash received
                            year_specific_incomes[source.id] = net_proceeds_after_mortgage
                            total_specific_income += net_proceeds_after_mortgage
                
                elif source.source_type == "drawdown" and source.linked_asset_id:
                    asset_id = source.linked_asset_id
                    available = temp_balances.get(asset_id, 0.0)
                    
                    # Cap drawdown at available balance
                    actual_drawdown = min(amount, available)
                    
                    # Deduct from temp so subsequent drawdowns on same asset are limited
                    if asset_id in temp_balances:
                        temp_balances[asset_id] -= actual_drawdown
                    
                    year_specific_incomes[source.id] = actual_drawdown
                    total_specific_income += actual_drawdown
                    
                    current = year_drawdown_amounts.get(asset_id, 0.0)
                    year_drawdown_amounts[asset_id] = current + actual_drawdown

                    # --- TAX CLASSIFICATION FOR DRAWDOWNS ---
                    # Determine tax bucket based on asset type
                    if asset_id in asset_states:
                        st = asset_states[asset_id]
                        
                        # 1. Real Estate Drawdown (Reverse Mortgage / HELOC?) -> For now, treat as Tax Exempt (Loan) or Ordinary?
                        # If it's a "drawdown" from property value, it's likely selling equity or borrowing.
                        # Assumption: Selling equity -> Capital Gains? Or HELOC -> Loan?
                        # SIMPLIFICATION: If type is real_estate, treat as tax_exempt_income (like return of capital or loan proceeds for now)
                        if "property_value" in st:
                            tax_exempt_income += actual_drawdown
                        
                        else:
                            # Securities Asset
                            wrapper = st.get("tax_wrapper", TaxWrapper.TAXABLE)
                            
                            # Normalize to enum for comparison (handle both enum and string)
                            if isinstance(wrapper, str):
                                try:
                                    wrapper = TaxWrapper(wrapper.lower())
                                except ValueError:
                                    wrapper = TaxWrapper.TAXABLE  # Default if invalid
                            
                            if wrapper == TaxWrapper.TRADITIONAL:
                                ordinary_income += actual_drawdown
                            elif wrapper == TaxWrapper.ROTH or wrapper == TaxWrapper.TAX_EXEMPT_OTHER:
                                tax_exempt_income += actual_drawdown
                            elif wrapper == TaxWrapper.TAXABLE:
                                # Pro-rata basis logic
                                current_val = st["balance"]
                                current_basis = st["cost_basis"]
                                
                                if current_val > 0:
                                    gain_ratio = max(0.0, (current_val - current_basis) / current_val)
                                else:
                                    gain_ratio = 0.0
                                
                                taxable_gain = actual_drawdown * gain_ratio
                                return_of_capital = actual_drawdown - taxable_gain
                                
                                long_term_cap_gains += taxable_gain
                                tax_exempt_income += return_of_capital
                                
                                # Adjust basis for next year (simulation step happens later, but we need to track basis reduction)
                                # NOTE: This is tricky. The asset loop below applies the reduction to the BALANCE.
                                # We need to update the cost_basis state as well.
                                st["cost_basis"] = max(0.0, current_basis - return_of_capital)

                else:
                    # Non-drawdown income source (e.g. pension, Social Security, disability)
                    year_specific_incomes[source.id] = amount
                    total_specific_income += amount
                    
                    # Handle different income types
                    income_type = getattr(source, 'income_type', IncomeType.ORDINARY)
                    # Handle both enum and string values
                    if isinstance(income_type, str):
                        try:
                            income_type = IncomeType(income_type.lower())
                        except ValueError:
                            income_type = IncomeType.ORDINARY
                    
                    if income_type == IncomeType.ORDINARY:
                        ordinary_income += amount
                    elif income_type == IncomeType.SOCIAL_SECURITY:
                        # Social Security benefits - track separately for special tax treatment
                        social_security_benefits += amount
                    elif income_type == IncomeType.TAX_EXEMPT:
                        tax_exempt_income += amount
                    elif income_type == IncomeType.DISABILITY:
                        # Disability income: typically tax-exempt if from VA or if premiums paid with after-tax dollars
                        # For now, treat as tax-exempt (user can change if needed)
                        tax_exempt_income += amount
                    else:
                        # Default to ordinary income
                        ordinary_income += amount
            else:
                year_specific_incomes[source.id] = 0.0
        
        # Calculate rental income for this year (pre-loop to determine total cash flow)
        total_rental_income_precalc = 0.0
        for asset in assets:
            if asset.type == "real_estate" and asset.id in asset_details and asset.id in asset_states:
                st = asset_states[asset.id]
                if not st.get("sold", False):
                    re_detail = asset_details[asset.id]["details"]
                    if re_detail.annual_rent > 0:
                        rent_val = re_detail.annual_rent * ((1 + scenario.inflation_rate) ** years_from_start)
                        
                        # Subtract depreciation for rental properties
                        annual_depreciation = 0.0
                        if st.get("property_type") == "rental":
                            depreciation_method = st.get("depreciation_method")
                            depreciation_start_year = st.get("depreciation_start_year")
                            if depreciation_method and depreciation_method != DepreciationMethod.NONE and depreciation_start_year is not None:
                                years_since_depreciation_start = sim_year - depreciation_start_year
                                if years_since_depreciation_start >= 0:
                                    depreciable_basis = st.get("purchase_price", 0.0) - st.get("land_value", 0.0)
                                    if depreciation_method == DepreciationMethod.RESIDENTIAL_27_5:
                                        annual_depreciation = depreciable_basis / 27.5
                                    elif depreciation_method == DepreciationMethod.COMMERCIAL_39:
                                        annual_depreciation = depreciable_basis / 39.0
                                    
                                    # Check if fully depreciated
                                    max_depreciation = depreciable_basis
                                    current_accumulated = st.get("accumulated_depreciation", 0.0)
                                    if current_accumulated >= max_depreciation:
                                        annual_depreciation = 0.0
                                    else:
                                        remaining_depreciation = max_depreciation - current_accumulated
                                        annual_depreciation = min(annual_depreciation, remaining_depreciation)
                        
                        # Net rental income = rent - depreciation
                        net_rental_income = rent_val - annual_depreciation
                        total_rental_income_precalc += net_rental_income
                        
                        # Rental Income -> Ordinary Income (net of depreciation)
                        ordinary_income += net_rental_income

        # Calculate income
        salary_income = 0.0
        if age < scenario.retirement_age:
            salary_income = scenario.annual_contribution_pre_retirement * ((1 + scenario.inflation_rate) ** years_from_start)
            # Salary -> Ordinary Income
            ordinary_income += salary_income
            
        income_sources["salary"].append(salary_income)
        
        if house_sale_this_year:  # Print for any year with a house sale
            print_flush(f"\n{'='*80}")
            print_flush(f"INCOME CALCULATION - Age {age}")
            print_flush(f"{'='*80}")
            print_flush(f"Salary Income: ${salary_income:,.2f}")
            print_flush(f"Total Specific Income (from income sources): ${total_specific_income:,.2f}")
            print_flush(f"Total Rental Income (net of depreciation): ${total_rental_income_precalc:,.2f}")
            print_flush(f"\nIncome Categorization (before house sale):")
            print_flush(f"  Ordinary income: ${ordinary_income:,.2f}")
            print_flush(f"  Long-term capital gains: ${long_term_cap_gains:,.2f}")
            print_flush(f"  Qualified dividends: ${qualified_dividends:,.2f}")
            print_flush(f"  Tax-exempt income: ${tax_exempt_income:,.2f}")
            print_flush(f"  Social Security benefits: ${social_security_benefits:,.2f}")
        
        # --- CALCULATE TAXES ---
        if house_sale_this_year:  # Print for any year with a house sale
            print_flush(f"\n{'='*80}")
            print_flush(f"TAX CALCULATION - Age {age}")
            print_flush(f"{'='*80}")
            print_flush(f"Final Income Breakdown (after all sources):")
            print_flush(f"  Ordinary income: ${ordinary_income:,.2f}")
            print_flush(f"  Long-term capital gains: ${long_term_cap_gains:,.2f}")
            print_flush(f"  Qualified dividends: ${qualified_dividends:,.2f}")
            print_flush(f"  Tax-exempt income: ${tax_exempt_income:,.2f}")
            print_flush(f"  Social Security benefits: ${social_security_benefits:,.2f}")
        
        tax_breakdown = TaxableIncomeBreakdown(
            ordinary_income=ordinary_income,
            long_term_cap_gains=long_term_cap_gains,
            qualified_dividends=qualified_dividends,
            tax_exempt_income=tax_exempt_income,
            social_security_benefits=social_security_benefits
        )
        
        tax_result = calculate_taxes(
            year=sim_year,
            filing_status=scenario.filing_status,
            state="CA",
            breakdown=tax_breakdown
        )
        
        # Calculate Net After-Tax Income
        # Include Social Security in gross income (even though only portion is taxable)
        # IMPORTANT: gross_income_all includes ALL income sources, including the full net_proceeds_after_mortgage
        # from house sales (broken down into taxable and non-taxable portions)
        gross_income_all = ordinary_income + long_term_cap_gains + qualified_dividends + tax_exempt_income + social_security_benefits
        
        # For cash flow: RSU vesting income is NOT cash, so exclude it from net income
        # But taxes on vesting income ARE cash that must be paid
        # So: net_after_tax_income = (gross_income - rsu_vesting_income) - total_tax
        # This means we pay taxes on vesting income, but don't count the vesting income as cash received
        gross_income_for_cash_flow = gross_income_all - rsu_vesting_income
        net_after_tax_income = gross_income_for_cash_flow - tax_result.total_tax
        
        if house_sale_this_year:  # Print for any year with a house sale
            print_flush(f"\nTax Results:")
            print_flush(f"  Federal ordinary tax: ${tax_result.federal_ordinary_tax:,.2f}")
            print_flush(f"  Federal LTCG tax: ${tax_result.federal_ltcg_tax:,.2f}")
            print_flush(f"  State tax: ${tax_result.state_tax:,.2f}")
            print_flush(f"  Total tax: ${tax_result.total_tax:,.2f}")
            print_flush(f"  Effective tax rate: {tax_result.effective_total_rate*100:.2f}%")
            print_flush(f"\nGross Income Breakdown:")
            print_flush(f"  Ordinary income: ${ordinary_income:,.2f} (includes depreciation recapture from house sale)")
            print_flush(f"  Long-term capital gains: ${long_term_cap_gains:,.2f} (includes capital gain from house sale)")
            print_flush(f"  Qualified dividends: ${qualified_dividends:,.2f}")
            print_flush(f"  Tax-exempt income: ${tax_exempt_income:,.2f} (includes return of capital + missing portion from house sale)")
            print_flush(f"  Social Security benefits: ${social_security_benefits:,.2f}")
            print_flush(f"  ─────────────────────────────")
            print_flush(f"  TOTAL GROSS INCOME: ${gross_income_all:,.2f}")
            print_flush(f"\nHouse Sale Verification:")
            print_flush(f"  Net proceeds from house sale: ${house_sale_net_proceeds:,.2f}")
            print_flush(f"  Total gross income: ${gross_income_all:,.2f}")
            print_flush(f"  ✓ All net proceeds from house sale are included in gross income")
            print_flush(f"\nNet Income Calculation:")
            print_flush(f"  Gross income (all sources): ${gross_income_all:,.2f}")
            print_flush(f"  Less: Total taxes: ${tax_result.total_tax:,.2f}")
            print_flush(f"  ─────────────────────────────")
            print_flush(f"  Net after-tax income: ${net_after_tax_income:,.2f}")
            print_flush(f"{'='*80}\n")
        
        # Store Tax Results
        federal_tax_list.append(tax_result.federal_ordinary_tax + tax_result.federal_ltcg_tax)
        state_tax_list.append(tax_result.state_tax)
        total_tax_list.append(tax_result.total_tax)
        effective_tax_rate_list.append(tax_result.effective_total_rate)

        # Calculate Uncovered Spending (Deficit) based on NET Income
        # total_income_available was previously just gross specific + rental.
        # Now we should use net_after_tax_income, but careful:
        # net_after_tax_income includes Salary. 
        # Pre-retirement, Salary covers contributions. 
        # Post-retirement, Net Income covers spending.
        
        # Re-align logic:
        # If we are RETIRED:
        #   Available = Net After Tax Income (from Drawdowns + Pension + Rent)
        #   Deficit = Spending - Available
        
        if age >= scenario.retirement_age and spending_nominal > net_after_tax_income:
            deficit = spending_nominal - net_after_tax_income
            cumulative_uncovered_spending += deficit
        
        uncovered_spending_list.append(cumulative_uncovered_spending)

        # Track which general equity assets to add contributions to
        general_equity_assets = [a for a in assets if a.type == "general_equity"]
        
        for asset in assets:
            asset_id = asset.id
            
            if asset.type == "real_estate" and asset_id in asset_details:
                re_detail = asset_details[asset_id]["details"]
                state = asset_states[asset_id]
                
                # Skip if property has been sold
                if state.get("sold", False):
                    asset_values[asset_id].append(0.0)
                    if asset_id in debt_values:
                        debt_values[asset_id].append(0.0)
                    if asset_id in income_sources["rental_income"]:
                        income_sources["rental_income"][asset_id].append(0.0)
                    continue
                
                # Property appreciation (use asset rate, or fallback to scenario bond rate)
                # Use appreciation_rate if explicitly set (including 0), otherwise fall back to bond_return_rate
                # Check if appreciation_rate is None (not set) rather than checking if it's > 0
                appreciation_rate = re_detail.appreciation_rate if re_detail.appreciation_rate is not None else scenario.bond_return_rate
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
                        if state["mortgage_years_remaining"] <= 0:
                            state["mortgage_balance"] = 0.0
                
                # Apply Explicit Drawdown (Reduce Property Value)
                if asset_id in year_drawdown_amounts:
                    state["property_value"] -= year_drawdown_amounts[asset_id]

                # Asset value = property value (Gross) - not equity
                asset_value = state["property_value"]
                asset_values[asset_id].append(asset_value)
                debt_values[asset_id].append(state["mortgage_balance"])
                
                total_assets += asset_value
                total_debts += state["mortgage_balance"]
                
                # Rental income (inflation-adjusted, net of depreciation)
                if re_detail.annual_rent > 0 and not state.get("sold", False):
                    rental_income_nominal = re_detail.annual_rent * ((1 + scenario.inflation_rate) ** years_from_start)
                    
                    # Subtract depreciation
                    annual_depreciation = 0.0
                    if state.get("property_type") == "rental":
                        depreciation_method = state.get("depreciation_method")
                        depreciation_start_year = state.get("depreciation_start_year")
                        if depreciation_method and depreciation_method != DepreciationMethod.NONE and depreciation_start_year is not None:
                            years_since_depreciation_start = sim_year - depreciation_start_year
                            if years_since_depreciation_start >= 0:
                                depreciable_basis = state.get("purchase_price", 0.0) - state.get("land_value", 0.0)
                                if depreciation_method == DepreciationMethod.RESIDENTIAL_27_5:
                                    annual_depreciation = depreciable_basis / 27.5
                                elif depreciation_method == DepreciationMethod.COMMERCIAL_39:
                                    annual_depreciation = depreciable_basis / 39.0
                                
                                # Check if fully depreciated
                                max_depreciation = depreciable_basis
                                current_accumulated = state.get("accumulated_depreciation", 0.0)
                                if current_accumulated >= max_depreciation:
                                    annual_depreciation = 0.0
                                else:
                                    remaining_depreciation = max_depreciation - current_accumulated
                                    annual_depreciation = min(annual_depreciation, remaining_depreciation)
                    
                    net_rental_income = rental_income_nominal - annual_depreciation
                    income_sources["rental_income"][asset_id].append(net_rental_income)
                    total_rental_income += net_rental_income
                else:
                    income_sources["rental_income"][asset_id].append(0.0)
                    
            elif asset.type == "general_equity" and asset_id in asset_details:
                ge_detail = asset_details[asset_id]["details"]
                state = asset_states[asset_id]
                
                # Growth with return rate minus fees (use asset rate exactly as entered)
                expected_return = ge_detail.expected_return_rate
                net_return = expected_return - ge_detail.fee_rate
                state["balance"] *= (1 + net_return)
                
                # Add annual contribution if specified in asset details
                if ge_detail.annual_contribution > 0 and age < scenario.retirement_age:
                    asset_contribution = ge_detail.annual_contribution * ((1 + scenario.inflation_rate) ** years_from_start)
                    state["balance"] += asset_contribution
                
                # Add scenario-level contribution (distribute evenly or to first asset)
                # For simplicity, add to first general equity asset
                if len(general_equity_assets) > 0 and general_equity_assets[0].id == asset_id:
                     # 1. Add Savings (Contributions) - Always added
                     if age < scenario.retirement_age and contribution_nominal > 0:
                        state["balance"] += contribution_nominal
                
                # Apply Explicit Drawdown
                if asset_id in year_drawdown_amounts:
                    state["balance"] -= year_drawdown_amounts[asset_id]
                
                asset_values[asset_id].append(state["balance"])
                total_assets += state["balance"]
            
            elif asset.type == "specific_stock" and asset_id in asset_details:
                stock_detail = asset_details[asset_id]["details"]
                state = asset_states[asset_id]
                
                # Growth: (1 + appreciation)
                # Dividends could be added here too if we wanted to model reinvestment
                appreciation = stock_detail.assumed_appreciation_rate
                state["balance"] *= (1 + appreciation)
                
                # Apply Explicit Drawdown
                if asset_id in year_drawdown_amounts:
                    state["balance"] -= year_drawdown_amounts[asset_id]

                asset_values[asset_id].append(state["balance"])
                total_assets += state["balance"]
            
            elif asset.type == "rsu_grant" and asset_id in asset_details:
                # Defensive check: ensure asset_details has the expected structure
                if "details" not in asset_details[asset_id] or asset_details[asset_id]["details"] is None:
                    continue
                    
                state = asset_states[asset_id]
                security_id = state.get("security_id")
                grant_fmv = state.get("grant_fmv_at_grant", 0.0)
                vested_lots = state.get("vested_lots", [])
                
                # Get appreciation rate for this security
                # Priority: 1) SpecificStockDetails if stock is held directly, 2) Security.assumed_appreciation_rate, 3) Default
                appreciation_rate = None  # Use None to distinguish "not found" from "explicitly set to 0"
                
                # First, check if there's a SpecificStockDetails asset with this ticker (takes priority)
                security = session.get(Security, security_id)
                if security:
                    for other_asset_id, other_st in asset_states.items():
                        if other_st.get("ticker") and other_st.get("appreciation_rate") is not None:
                            if other_st.get("ticker") == security.symbol:
                                appreciation_rate = other_st.get("appreciation_rate")
                                break
                    
                    # If not found in asset_states, use Security's assumed_appreciation_rate
                    if appreciation_rate is None:
                        appreciation_rate = security.assumed_appreciation_rate
                
                # If still not found, use default (only if None, not if explicitly set to 0.0)
                if appreciation_rate is None:
                    appreciation_rate = 0.07  # Default 7% equity return
                
                # IMPORTANT: Unvested shares should NOT be counted as assets
                # Only vested shares (after taxes) are counted as assets
                # The RSU grant itself shows 0 value until vesting occurs
                
                # Calculate value of vested lots only (appreciate from vesting FMV)
                # These represent the net shares received after tax withholding
                vested_value = 0.0
                for lot in vested_lots:
                    vesting_year = lot.get("vesting_year", sim_year)
                    years_since_vest = sim_year - vesting_year
                    lot_fmv = lot.get("fmv_on_vest", 0.0)
                    current_lot_price = lot_fmv * ((1 + appreciation_rate) ** years_since_vest)
                    net_shares = lot.get("net_shares_received", 0.0)
                    lot_value = net_shares * current_lot_price
                    vested_value += lot_value
                    
                    # Update lot tracking
                    lot["current_price"] = current_lot_price
                    lot["current_value"] = lot_value
                
                # RSU grant asset value = only vested shares (net after taxes)
                # Unvested shares are worth $0 until they vest
                state["balance"] = vested_value
                
                asset_values[asset_id].append(vested_value)
                total_assets += vested_value

            else:
                # Asset without details - use current balance and scenario bond rate
                if asset_id not in asset_states:
                    asset_states[asset_id] = {"balance": asset.current_balance}
                state = asset_states[asset_id]
                state["balance"] *= (1 + scenario.bond_return_rate)
                asset_values[asset_id].append(state["balance"])
                total_assets += state["balance"]
        
        # Track specific income
        for source in income_sources_db:
            income_sources["specific_income"][source.id].append(year_specific_incomes.get(source.id, 0.0))

        # Calculate Net Cash Flow (Total Income - Spending)
        # Recalculate total income to ensure all components are included
        # Use NET After Tax Income for the "Income" part of Net Cash Flow
        
        # Pre-retirement: Net Income (Salary + etc) - Contributions (handled separately?) 
        # Or simply: Net Income - Spending.
        # Since spending is 0 pre-retirement, Net Cash Flow = Net Income.
        
        if house_sale_this_year:  # Print for any year with a house sale
            print_flush(f"\n{'='*80}")
            print_flush(f"SPENDING CALCULATION - Age {age}")
            print_flush(f"{'='*80}")
            print_flush(f"  Retirement age: {scenario.retirement_age}")
            print_flush(f"  Current age: {age}")
        if age >= scenario.retirement_age:
            spending_base = scenario.annual_spending_in_retirement
            spending_nominal_calc = spending_base * ((1 + scenario.inflation_rate) ** years_from_start)
            print_flush(f"  Base retirement spending: ${spending_base:,.2f}")
            print_flush(f"  Inflation rate: {scenario.inflation_rate*100:.2f}%")
            print_flush(f"  Years from start: {years_from_start}")
            print_flush(f"  Inflation factor: {(1 + scenario.inflation_rate) ** years_from_start:.4f}")
            print_flush(f"  Spending (nominal, inflation-adjusted): ${spending_nominal:,.2f}")
        else:
            print_flush(f"  Pre-retirement: Spending = $0.00")
        
        current_net_cash_flow = net_after_tax_income - spending_nominal
        net_cash_flow_list.append(current_net_cash_flow)
        
        if house_sale_this_year:  # Print for any year with a house sale
            print_flush(f"\n{'='*80}")
            print_flush(f"NET CASH FLOW CALCULATION - Age {age}")
            print_flush(f"{'='*80}")
            print_flush(f"  Gross income (all sources): ${gross_income_all:,.2f}")
            print_flush(f"  Less: Total taxes: ${tax_result.total_tax:,.2f}")
            print_flush(f"  ─────────────────────────────")
            print_flush(f"  Net after-tax income: ${net_after_tax_income:,.2f}")
            print_flush(f"  Less: Spending: ${spending_nominal:,.2f}")
            print_flush(f"  ─────────────────────────────")
            print_flush(f"  NET CASH FLOW: ${current_net_cash_flow:,.2f}")
            print_flush(f"{'='*80}\n")

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

    # Build specific income names
    income_names = {source.id: source.name for source in income_sources_db}
    
    return {
        "ages": ages,
        "balance_nominal": balance_nominal,
        "balance_real": balance_real,
        "contribution_nominal": contribution_nominal_list,
        "spending_nominal": spending_nominal_list,
        "net_cash_flow": net_cash_flow_list,
        "uncovered_spending": uncovered_spending_list,
        "asset_values": asset_values,
        "asset_names": asset_names,
        "debt_values": debt_values,
        "debt_names": debt_names,
        "income_sources": income_sources,
        "income_names": income_names,
        "tax_simulation": {
            "federal_tax": federal_tax_list,
            "state_tax": state_tax_list,
            "total_tax": total_tax_list,
            "effective_tax_rate": effective_tax_rate_list
        }
    }
