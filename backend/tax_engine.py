from typing import Optional
from pydantic import BaseModel
from .tax_config import FilingStatus, get_federal_ordinary_tax_table, get_federal_ltcg_tax_table, get_state_tax_table, TaxTable

class TaxableIncomeBreakdown(BaseModel):
    ordinary_income: float = 0.0           # wages, pensions, IRA withdrawals, STCG, rental net, etc.
    long_term_cap_gains: float = 0.0       # LTCG (non-qualified)
    qualified_dividends: float = 0.0       # QD (taxed using LTCG schedule)
    tax_exempt_income: float = 0.0         # e.g. Roth withdrawals, muni interest
    social_security_benefits: float = 0.0  # Social Security benefits (before tax calculation)

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

def calculate_social_security_taxable(
    social_security_benefits: float,
    other_income: float,  # AGI + nontaxable interest + 50% of SS benefits
    filing_status: FilingStatus
) -> float:
    """
    Calculate taxable portion of Social Security benefits.
    
    Combined Income = AGI + Nontaxable Interest + 50% of Social Security Benefits
    
    Taxable thresholds (2024):
    - Single/HoH: $25,000 (50% taxable), $34,000 (85% taxable)
    - Married Filing Jointly: $32,000 (50% taxable), $44,000 (85% taxable)
    - Married Filing Separately: $0 (85% taxable if living together)
    
    Returns: taxable amount of Social Security benefits (added to ordinary income)
    """
    if social_security_benefits <= 0:
        return 0.0
    
    # Calculate combined income
    # other_income should already include AGI + nontaxable interest
    combined_income = other_income + (0.5 * social_security_benefits)
    
    # Determine thresholds based on filing status
    if filing_status == FilingStatus.MARRIED_FILING_JOINTLY:
        threshold_50 = 32000.0
        threshold_85 = 44000.0
    elif filing_status == FilingStatus.MARRIED_FILING_SEPARATELY:
        # If living together, 85% is taxable regardless of income
        return 0.85 * social_security_benefits
    elif filing_status == FilingStatus.HEAD_OF_HOUSEHOLD:
        threshold_50 = 25000.0
        threshold_85 = 34000.0
    else:  # SINGLE
        threshold_50 = 25000.0
        threshold_85 = 34000.0
    
    # Calculate taxable amount
    if combined_income <= threshold_50:
        # 0% taxable
        return 0.0
    elif combined_income <= threshold_85:
        # 50% taxable (but not more than 50% of benefits)
        # The taxable amount is 50% of the lesser of:
        # - The excess over threshold_50
        # - 50% of Social Security benefits
        excess_over_50 = combined_income - threshold_50
        taxable_50_percent = 0.5 * social_security_benefits
        return min(excess_over_50 * 0.5, taxable_50_percent)
    else:
        # 85% taxable (with phase-in)
        # Base amount: 50% of benefits up to threshold_85
        base_taxable_50 = 0.5 * social_security_benefits
        
        # Additional amount: 85% of the excess over threshold_85, but capped at 35% of benefits
        excess_over_85 = combined_income - threshold_85
        additional_taxable = min(excess_over_85 * 0.85, 0.35 * social_security_benefits)
        
        # Total taxable is base + additional, but capped at 85% of benefits
        return min(base_taxable_50 + additional_taxable, 0.85 * social_security_benefits)

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
    ss_benefits = max(0.0, breakdown.social_security_benefits)
    
    # 2. Calculate Social Security taxable amount
    # Combined income = AGI + Nontaxable Interest + 50% of Social Security Benefits
    # AGI includes: ordinary income, LTCG, QD (but for SS calculation, we use modified AGI)
    # For Social Security calculation, AGI = ordinary + LTCG + QD (all are part of AGI)
    # Nontaxable interest is part of tax_exempt_income, but we'll simplify and use AGI only
    agi_for_ss = ordinary + ltcg + qd  # AGI includes all taxable income
    ss_taxable = calculate_social_security_taxable(ss_benefits, agi_for_ss, filing_status)
    
    # Add taxable SS to ordinary income
    ordinary_with_ss = ordinary + ss_taxable
    
    total_ltcg_like = ltcg + qd
    gross_taxable = ordinary_with_ss + total_ltcg_like
    gross_with_exempt = gross_taxable + exempt + (ss_benefits - ss_taxable)  # Include non-taxable SS
    
    # 3. Federal Ordinary Income Tax
    fed_ord_table = get_federal_ordinary_tax_table(year, filing_status)
    
    # Apply standard deduction to ordinary income (including taxable SS)
    taxable_ordinary = max(0.0, ordinary_with_ss - fed_ord_table.standard_deduction)
    
    federal_ordinary_tax = apply_brackets(taxable_ordinary, fed_ord_table)
    
    # 4. Federal LTCG / Qualified Dividends Tax
    fed_ltcg_table = get_federal_ltcg_tax_table(year, filing_status)
    
    # Simplification: Treating LTCG as separate stack (ignoring ordinary income base) for V1
    federal_ltcg_tax = apply_ltcg_brackets(total_ltcg_like, fed_ltcg_table)
    
    # 5. State Tax (CA)
    # CA treats Capital Gains as Ordinary Income
    state_table = get_state_tax_table(state, year, filing_status)
    
    # CA allows standard deduction against total income
    state_taxable_income = max(0.0, gross_taxable - state_table.standard_deduction)
    state_tax = apply_brackets(state_taxable_income, state_table)
    
    # Debug logging for tax calculations (always print to help diagnose issues)
    import sys
    def print_flush(*args, **kwargs):
        print(*args, **kwargs)
        sys.stdout.flush()
    print_flush(f"\n[TAX DEBUG] Tax Calculation - Year {year}, Filing Status: {filing_status}")
    print_flush(f"[TAX DEBUG] Income Breakdown:")
    print_flush(f"[TAX DEBUG]   Ordinary income (before SS): ${ordinary:,.2f}")
    print_flush(f"[TAX DEBUG]   Social Security benefits: ${ss_benefits:,.2f}, SS taxable: ${ss_taxable:,.2f}")
    print_flush(f"[TAX DEBUG]   Ordinary income (with SS): ${ordinary_with_ss:,.2f}")
    print_flush(f"[TAX DEBUG]   Long-term capital gains: ${ltcg:,.2f}")
    print_flush(f"[TAX DEBUG]   Qualified dividends: ${qd:,.2f}")
    print_flush(f"[TAX DEBUG]   Tax-exempt income: ${exempt:,.2f}")
    print_flush(f"[TAX DEBUG]   Gross taxable income: ${gross_taxable:,.2f}")
    print_flush(f"\n[TAX DEBUG] Federal Tax Calculation:")
    print_flush(f"[TAX DEBUG]   Federal standard deduction: ${fed_ord_table.standard_deduction:,.2f}")
    print_flush(f"[TAX DEBUG]   Taxable ordinary income: ${taxable_ordinary:,.2f}")
    print_flush(f"[TAX DEBUG]   Federal ordinary tax: ${federal_ordinary_tax:,.2f}")
    print_flush(f"[TAX DEBUG]   LTCG + QD: ${total_ltcg_like:,.2f}")
    print_flush(f"[TAX DEBUG]   Federal LTCG tax: ${federal_ltcg_tax:,.2f}")
    print_flush(f"[TAX DEBUG]   Federal total tax: ${federal_ordinary_tax + federal_ltcg_tax:,.2f}")
    print_flush(f"\n[TAX DEBUG] State Tax Calculation (CA):")
    print_flush(f"[TAX DEBUG]   State standard deduction: ${state_table.standard_deduction:,.2f}")
    print_flush(f"[TAX DEBUG]   State taxable income: ${state_taxable_income:,.2f}")
    print_flush(f"[TAX DEBUG]   State tax: ${state_tax:,.2f}")
    print_flush(f"[TAX DEBUG]   Total tax: ${federal_ordinary_tax + federal_ltcg_tax + state_tax:,.2f}")
    
    # 6. Aggregate Results
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

