# RSU Value Debug Implementation Summary

## Overview

This document summarizes the diagnostic tools and test added to debug the RSU value disappearance issue.

## Deliverable A: Debug Trace

### What Was Added

1. **Debug Parameter**: Added `debug` parameter to the simulation endpoint and `run_simple_bond_simulation` function
2. **Debug Trace Collection**: Added comprehensive trace collection throughout the simulation loop

### Where Trace Collection Was Added

1. **Start of Year** (line ~631-679 in `backend/simulation.py`):
   - Captures initial total assets, cash, and RSU unvested values
   - Initializes trace entry for each year

2. **During RSU Vesting** (line ~847-852):
   - Captures vesting events: shares vested, FMV at vest, vested value
   - Updates trace when shares vest

3. **After Tax Calculation** (line ~1276-1283):
   - Captures income totals (gross, ordinary, RSU-specific)
   - Captures tax totals (federal, state, total)

4. **End of Year** (line ~1690-1730):
   - Captures final total assets, cash
   - Captures RSU end state (unvested value, vested holdings)

5. **Return Value** (line ~1735-1738):
   - Adds `debug_trace` to result if `debug=True`

### How to Use

**Backend API Call:**
```
GET /api/scenarios/{scenario_id}/simulate/simple-bond?debug=true
```

**Python Code:**
```python
result = simulation.run_simple_bond_simulation(session, scenario_id, debug=True)
debug_trace = result.get("debug_trace", [])
```

### Trace Structure

Each year's trace entry contains:
```python
{
    "age": 51,
    "year": 2026,
    "rsu": {
        asset_id: {
            "unvested_value_start": 200000.0,
            "unvested_value_end": 100000.0,
            "unvested_shares_start": 200.0,
            "unvested_shares_end": 100.0,
            "shares_granted": 200.0,
            "shares_vested_this_year": 100.0,
            "fmv_at_vest": 1000.0,
            "vested_value_this_year": 100000.0,
            "vested_holding_value_end": 0.0,  # Will show if vested holdings exist
            "vested_holding_shares_end": 0.0
        }
    },
    "income": {
        "gross_income_total": 100000.0,
        "ordinary_income_total": 100000.0,
        "rsu_ordinary_income": 100000.0
    },
    "tax": {
        "federal_tax": 8032.0,
        "state_tax": 2602.0,
        "total_tax": 10634.0
    },
    "cash": {
        "cash_start": 100000.0,
        "cash_end": 89366.0
    },
    "asset_totals": {
        "total_assets_start": 300000.0,
        "total_assets_end": 289366.0
    }
}
```

## Deliverable B: Regression Test

### Test File

`backend/tests/test_rsu_value_conservation.py`

### Test Setup

- Scenario: Age 50-55 (2025-2030)
- Starting cash: $100,000
- RSU grant: $200,000 (200 shares @ $1,000)
- Vesting: 50% in 2026, 50% in 2027
- No appreciation (0% growth)
- No spending

### Test Assertions

1. **Year 2025 (Before vest)**:
   - Unvested = 200 shares, $200k value
   - No vested holdings

2. **Year 2026 (First vest)**:
   - 100 shares vest
   - Unvested decreases by ~$100k
   - Income includes $100k RSU vesting income
   - Assets decrease only by taxes (not by full $100k)

3. **Year 2027 (Second vest)**:
   - Remaining 100 shares vest
   - Unvested goes to 0
   - Vested holdings should exist

### How to Run

```bash
# From project root
python -m pytest backend/tests/test_rsu_value_conservation.py -v

# Or with unittest
python -m unittest backend.tests.test_rsu_value_conservation -v
```

## What We'll Learn

The debug trace will reveal:

1. **If vested holdings are created**: Check `vested_holding_value_end` - if 0, holdings aren't being created
2. **If income is recorded**: Check `income.gross_income_total` and `income.rsu_ordinary_income`
3. **If value is conserved**: Compare `unvested_value_start - unvested_value_end` vs `vested_holding_value_end`
4. **If assets decrease correctly**: Compare `total_assets_start - total_assets_end` vs `tax.total_tax`

## Next Steps

After running the simulation with `debug=true` and examining the trace:

1. **If `vested_holding_value_end` is always 0**: Vested shares aren't being converted to separate assets
2. **If `income.gross_income_total` is 0 but taxes exist**: Income isn't being included in gross income calculation
3. **If `total_assets_end` drops by full vested amount**: Vested value isn't being tracked in asset totals

Once we identify the root cause from the trace, we can fix the specific issue.

