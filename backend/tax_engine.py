from typing import Optional
from pydantic import BaseModel
from .tax_config import FilingStatus, get_federal_ordinary_tax_table, get_federal_ltcg_tax_table, get_state_tax_table, TaxTable

class TaxableIncomeBreakdown(BaseModel):
    ordinary_income: float = 0.0           # wages, pensions, IRA withdrawals, STCG, rental net, etc.
    long_term_cap_gains: float = 0.0       # LTCG (non-qualified)
    qualified_dividends: float = 0.0       # QD (taxed using LTCG schedule)
    tax_exempt_income: float = 0.0         # e.g. Roth withdrawals, muni interest

class TaxResult(BaseModel):
    year: int
    filing_status: FilingStatus
    state: Optional[str] = "CA"

    federal_ordinary_tax: float = 0.0
    federal_ltcg_tax: float = 0.0
    state_tax: float = 0.0

    total_tax: float = 0.0
    effective_total_rate: float = 0.0      # total_tax / total_gross_including_exempt
    effective_federal_rate: float = 0.0    # federal_total / total_gross_taxable
    effective_state_rate: float = 0.0      # state_tax / total_gross_taxable

def apply_brackets(taxable_income: float, table: TaxTable) -> float:
    """
    Calculate tax based on progressive brackets.
    Returns total tax amount.
    """
    if taxable_income <= 0:
        return 0.0
        
    tax = 0.0
    previous_up_to = 0.0
    
    for bracket in table.brackets:
        # Determine how much income falls into this bracket
        if taxable_income > previous_up_to:
            # The income in this bracket is either:
            # (bracket.up_to - previous_up_to) -> full bracket filled
            # OR
            # (taxable_income - previous_up_to) -> partial bracket filled
            
            # Handle infinity for top bracket
            if bracket.up_to == float("inf"):
                income_in_bracket = taxable_income - previous_up_to
            else:
                income_in_bracket = min(bracket.up_to, taxable_income) - previous_up_to
                
            if income_in_bracket > 0:
                tax += income_in_bracket * bracket.rate
                
            previous_up_to = bracket.up_to
        else:
            break
            
    return tax

def apply_ltcg_brackets(ltcg_income: float, table: TaxTable) -> float:
    """
    Simplified LTCG calculation.
    In reality, LTCG brackets stack on top of ordinary income.
    For V1, we are simplifying and treating this as a separate stack to get directionally correct numbers.
    """
    # Re-use standard bracket logic for now
    return apply_brackets(ltcg_income, table)

def calculate_taxes(
    year: int,
    filing_status: FilingStatus,
    state: str,
    breakdown: TaxableIncomeBreakdown,
) -> TaxResult:
    """
    Calculate estimated taxes based on income breakdown.
    """
    # 1. Inputs
    ordinary = max(0.0, breakdown.ordinary_income)
    ltcg = max(0.0, breakdown.long_term_cap_gains)
    qd = max(0.0, breakdown.qualified_dividends)
    exempt = max(0.0, breakdown.tax_exempt_income)
    
    total_ltcg_like = ltcg + qd
    gross_taxable = ordinary + total_ltcg_like
    gross_with_exempt = gross_taxable + exempt
    
    # 2. Federal Ordinary Income Tax
    fed_ord_table = get_federal_ordinary_tax_table(year, filing_status)
    
    # Apply standard deduction to ordinary income only (Simplification for V1)
    taxable_ordinary = max(0.0, ordinary - fed_ord_table.standard_deduction)
    
    federal_ordinary_tax = apply_brackets(taxable_ordinary, fed_ord_table)
    
    # 3. Federal LTCG / Qualified Dividends Tax
    fed_ltcg_table = get_federal_ltcg_tax_table(year, filing_status)
    
    # Simplification: Treating LTCG as separate stack (ignoring ordinary income base) for V1
    federal_ltcg_tax = apply_ltcg_brackets(total_ltcg_like, fed_ltcg_table)
    
    # 4. State Tax (CA)
    # CA treats Capital Gains as Ordinary Income
    state_table = get_state_tax_table(state, year, filing_status)
    
    # CA allows standard deduction against total income
    state_taxable_income = max(0.0, gross_taxable - state_table.standard_deduction)
    state_tax = apply_brackets(state_taxable_income, state_table)
    
    # 5. Aggregate Results
    federal_total = federal_ordinary_tax + federal_ltcg_tax
    total_tax = federal_total + state_tax
    
    # Calculate Rates
    eff_total = total_tax / gross_with_exempt if gross_with_exempt > 0 else 0.0
    eff_fed = federal_total / gross_taxable if gross_taxable > 0 else 0.0
    eff_state = state_tax / gross_taxable if gross_taxable > 0 else 0.0
    
    return TaxResult(
        year=year,
        filing_status=filing_status,
        state=state,
        federal_ordinary_tax=federal_ordinary_tax,
        federal_ltcg_tax=federal_ltcg_tax,
        state_tax=state_tax,
        total_tax=total_tax,
        effective_total_rate=eff_total,
        effective_federal_rate=eff_fed,
        effective_state_rate=eff_state
    )

