from typing import List, Dict, Optional
from pydantic import BaseModel
from enum import Enum

class FilingStatus(str, Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"

class TaxBracket(BaseModel):
    up_to: float | None  # None means “no upper limit”
    rate: float


class TaxTable(BaseModel):
    """
    Represents a set of tax brackets and a standard deduction
    for a given tax regime (federal or state) + filing status + year.
    """
    brackets: List[TaxBracket]
    standard_deduction: float

# -----------------------------------------------------------------------------
# 1. Federal Ordinary Income Tax Config
# -----------------------------------------------------------------------------
# Source (approximate for 2024): https://www.irs.gov/newsroom/irs-provides-tax-inflation-adjustments-for-tax-year-2024
FEDERAL_ORDINARY_TABLES: Dict[int, Dict[FilingStatus, TaxTable]] = {
    2024: {
        FilingStatus.MARRIED_FILING_JOINTLY: TaxTable(
            standard_deduction=29200.0,
            brackets=[
                TaxBracket(up_to=23200.0, rate=0.10),
                TaxBracket(up_to=94300.0, rate=0.12),
                TaxBracket(up_to=201050.0, rate=0.22),
                TaxBracket(up_to=383900.0, rate=0.24),
                TaxBracket(up_to=487450.0, rate=0.32),
                TaxBracket(up_to=731200.0, rate=0.35),
                TaxBracket(up_to=None, rate=0.37),
            ]
        ),
        FilingStatus.SINGLE: TaxTable(
             standard_deduction=14600.0,
             brackets=[
                TaxBracket(up_to=11600.0, rate=0.10),
                TaxBracket(up_to=47150.0, rate=0.12),
                TaxBracket(up_to=100525.0, rate=0.22),
                TaxBracket(up_to=191950.0, rate=0.24),
                TaxBracket(up_to=243725.0, rate=0.32),
                TaxBracket(up_to=609350.0, rate=0.35),
                TaxBracket(up_to=None, rate=0.37),
             ]
        ),
        FilingStatus.MARRIED_FILING_SEPARATELY: TaxTable(
            standard_deduction=14600.0,
            brackets=[
                TaxBracket(up_to=11600.0, rate=0.10),
                TaxBracket(up_to=47150.0, rate=0.12),
                TaxBracket(up_to=100525.0, rate=0.22),
                TaxBracket(up_to=191950.0, rate=0.24),
                TaxBracket(up_to=243725.0, rate=0.32),
                TaxBracket(up_to=365600.0, rate=0.35),
                TaxBracket(up_to=None, rate=0.37),
            ]
        ),
        FilingStatus.HEAD_OF_HOUSEHOLD: TaxTable(
            standard_deduction=21900.0,
            brackets=[
                TaxBracket(up_to=16550.0, rate=0.10),
                TaxBracket(up_to=63100.0, rate=0.12),
                TaxBracket(up_to=100500.0, rate=0.22),
                TaxBracket(up_to=191950.0, rate=0.24),
                TaxBracket(up_to=243700.0, rate=0.32),
                TaxBracket(up_to=609350.0, rate=0.35),
                TaxBracket(up_to=None, rate=0.37),
            ]
        )
    }
}

# -----------------------------------------------------------------------------
# 2. Federal Long-Term Capital Gains (LTCG) Tax Config
# -----------------------------------------------------------------------------
# Note: LTCG brackets are based on TAXABLE INCOME, not just gains.
# Standard deduction is not applicable specifically to this table (it's shared with ordinary),
# so we set it to 0.0 here to avoid double counting if someone naively adds it.
FEDERAL_LTCG_TABLES: Dict[int, Dict[FilingStatus, TaxTable]] = {
    2024: {
        FilingStatus.MARRIED_FILING_JOINTLY: TaxTable(
            standard_deduction=0.0, 
            brackets=[
                TaxBracket(up_to=94050.0, rate=0.00),
                TaxBracket(up_to=583750.0, rate=0.15),
                TaxBracket(up_to=None, rate=0.20),
            ]
        ),
        FilingStatus.SINGLE: TaxTable(
            standard_deduction=0.0,
            brackets=[
                TaxBracket(up_to=47025.0, rate=0.00),
                TaxBracket(up_to=518900.0, rate=0.15),
                TaxBracket(up_to=None, rate=0.20),
            ]
        ),
        FilingStatus.MARRIED_FILING_SEPARATELY: TaxTable(
            standard_deduction=0.0,
            brackets=[
                TaxBracket(up_to=47025.0, rate=0.00),
                TaxBracket(up_to=291850.0, rate=0.15),
                TaxBracket(up_to=None, rate=0.20),
            ]
        ),
        FilingStatus.HEAD_OF_HOUSEHOLD: TaxTable(
            standard_deduction=0.0,
            brackets=[
                TaxBracket(up_to=63100.0, rate=0.00),
                TaxBracket(up_to=551350.0, rate=0.15),
                TaxBracket(up_to=None, rate=0.20),
            ]
        )
    }
}

# -----------------------------------------------------------------------------
# 3. California State Tax Config
# -----------------------------------------------------------------------------
# Source (approximate for 2024): CA FTB 2023 Tax Rate Schedules (inflation adjusted slightly for 2024 placeholder)
STATE_CA_ORDINARY_TABLES: Dict[int, Dict[FilingStatus, TaxTable]] = {
    2024: {
        FilingStatus.MARRIED_FILING_JOINTLY: TaxTable(
            standard_deduction=10726.0, # 2023 value, used as placeholder
            brackets=[
                TaxBracket(up_to=20824.0, rate=0.01),
                TaxBracket(up_to=49368.0, rate=0.02),
                TaxBracket(up_to=77918.0, rate=0.04),
                TaxBracket(up_to=108162.0, rate=0.06),
                TaxBracket(up_to=136692.0, rate=0.08),
                TaxBracket(up_to=698272.0, rate=0.093),
                TaxBracket(up_to=837922.0, rate=0.103),
                TaxBracket(up_to=1396542.0, rate=0.113),
                TaxBracket(up_to=None, rate=0.123),
                # Note: 1% Mental Health Services Tax applies > $1M taxable income, effectively handled as bracket or surcharge.
                # Included in top brackets for simplicity here (11.3 -> 12.3 above 1M ish? CA is complex).
                # Simplified for this exercise.
            ]
        ),
        FilingStatus.SINGLE: TaxTable(
            standard_deduction=5363.0,
            brackets=[
                TaxBracket(up_to=10412.0, rate=0.01),
                TaxBracket(up_to=24684.0, rate=0.02),
                TaxBracket(up_to=38959.0, rate=0.04),
                TaxBracket(up_to=54081.0, rate=0.06),
                TaxBracket(up_to=68346.0, rate=0.08),
                TaxBracket(up_to=349136.0, rate=0.093),
                TaxBracket(up_to=418961.0, rate=0.103),
                TaxBracket(up_to=698271.0, rate=0.113),
                TaxBracket(up_to=None, rate=0.123),
            ]
        ),
        FilingStatus.MARRIED_FILING_SEPARATELY: TaxTable(
            standard_deduction=5363.0,
            brackets=[
                TaxBracket(up_to=10412.0, rate=0.01),
                TaxBracket(up_to=24684.0, rate=0.02),
                TaxBracket(up_to=38959.0, rate=0.04),
                TaxBracket(up_to=54081.0, rate=0.06),
                TaxBracket(up_to=68346.0, rate=0.08),
                TaxBracket(up_to=349136.0, rate=0.093),
                TaxBracket(up_to=418961.0, rate=0.103),
                TaxBracket(up_to=698271.0, rate=0.113),
                TaxBracket(up_to=None, rate=0.123),
            ]
        ),
        FilingStatus.HEAD_OF_HOUSEHOLD: TaxTable(
            standard_deduction=10726.0,
            brackets=[
                TaxBracket(up_to=20824.0, rate=0.01),
                TaxBracket(up_to=49368.0, rate=0.02),
                TaxBracket(up_to=77918.0, rate=0.04),
                TaxBracket(up_to=108162.0, rate=0.06),
                TaxBracket(up_to=136692.0, rate=0.08),
                TaxBracket(up_to=698272.0, rate=0.093),
                TaxBracket(up_to=837922.0, rate=0.103),
                TaxBracket(up_to=1396542.0, rate=0.113),
                TaxBracket(up_to=None, rate=0.123),
            ]
        )
    }
}

def _get_table_for_year_and_status(
    tables: Dict[int, Dict[FilingStatus, TaxTable]], 
    year: int, 
    filing_status: FilingStatus
) -> TaxTable:
    """
    Helper to look up a tax table.
    Strategy:
    1. Look for exact year.
    2. If not found, use the MAX available year (latest known logic).
    3. If filing status not found for that year, raise ValueError.
    """
    if not tables:
        raise ValueError("No tax tables configured.")

    # 1. Determine Year
    if year in tables:
        target_year = year
    else:
        # Fallback to latest available year
        target_year = max(tables.keys())
    
    year_tables = tables[target_year]
    
    # 2. Look up Filing Status
    if filing_status not in year_tables:
        raise ValueError(f"Filing status {filing_status} not found in tax tables for year {target_year}")
        
    return year_tables[filing_status]

def get_federal_ordinary_tax_table(year: int, filing_status: FilingStatus) -> TaxTable:
    """
    Get Federal Ordinary Income tax table (brackets + standard deduction).
    """
    return _get_table_for_year_and_status(FEDERAL_ORDINARY_TABLES, year, filing_status)

def get_federal_ltcg_tax_table(year: int, filing_status: FilingStatus) -> TaxTable:
    """
    Get Federal Long-Term Capital Gains tax table.
    """
    return _get_table_for_year_and_status(FEDERAL_LTCG_TABLES, year, filing_status)

def get_state_tax_table(state: str, year: int, filing_status: FilingStatus) -> TaxTable:
    """
    Get State Tax Table. Currently only supports 'CA'.
    """
    if state.upper() != "CA":
        raise NotImplementedError(f"State {state} not supported. Only 'CA' is currently configured.")
    
    return _get_table_for_year_and_status(STATE_CA_ORDINARY_TABLES, year, filing_status)

def apply_tax_table_indexing(
    base_table: TaxTable,
    year_base: int,
    target_year: int,
    indexing_policy: str,
    scenario_inflation_rate: Optional[float] = None,
    custom_index_rate: Optional[float] = None
) -> TaxTable:
    """
    Apply indexing policy to a tax table to adjust thresholds and standard deduction for a target year.
    
    Args:
        base_table: The base tax table (from year_base)
        year_base: The base year the table represents
        target_year: The year to index to
        indexing_policy: One of "CONSTANT_NOMINAL", "SCENARIO_INFLATION", "CUSTOM_RATE"
        scenario_inflation_rate: Scenario's inflation rate (used if policy is SCENARIO_INFLATION)
        custom_index_rate: Custom indexing rate as decimal (used if policy is CUSTOM_RATE)
    
    Returns:
        A new TaxTable with adjusted thresholds and standard deduction (rates unchanged)
    """
    if indexing_policy == "CONSTANT_NOMINAL":
        # No indexing - return table as-is
        return base_table
    
    # Calculate years from base
    years_from_base = target_year - year_base
    
    if years_from_base == 0:
        # Same year, no indexing needed
        return base_table
    
    # Determine indexing rate
    if indexing_policy == "SCENARIO_INFLATION":
        if scenario_inflation_rate is None:
            raise ValueError("scenario_inflation_rate is required for SCENARIO_INFLATION policy")
        index_rate = scenario_inflation_rate
    elif indexing_policy == "CUSTOM_RATE":
        if custom_index_rate is None:
            raise ValueError("custom_index_rate is required for CUSTOM_RATE policy")
        index_rate = custom_index_rate
    else:
        raise ValueError(f"Unknown indexing policy: {indexing_policy}")
    
    # Calculate multiplier: (1 + rate) ^ years
    multiplier = (1 + index_rate) ** years_from_base
    
    # Create new brackets with adjusted thresholds (rates unchanged)
    adjusted_brackets = []
    for bracket in base_table.brackets:
        if bracket.up_to == None:
            adjusted_up_to = None
        else:
            adjusted_up_to = bracket.up_to * multiplier
        adjusted_brackets.append(TaxBracket(up_to=adjusted_up_to, rate=bracket.rate))
    
    # Adjust standard deduction
    adjusted_standard_deduction = base_table.standard_deduction * multiplier
    
    return TaxTable(
        brackets=adjusted_brackets,
        standard_deduction=adjusted_standard_deduction
    )

