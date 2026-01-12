# Tax Settings & Editable Tax Tables Implementation Summary

## Overview
This document summarizes the implementation of the expanded Settings menu, editable Tax Tables, and Tax Table Indexing Policy feature.

## ✅ Completed (Backend)

### 1. Data Models (`backend/models.py`)
- **Extended `TaxFundingSettings`**:
  - Added `tax_table_indexing_policy: TaxTableIndexingPolicy` enum field
  - Added `tax_table_custom_index_rate: Optional[float]` field
- **New `TaxTableIndexingPolicy` enum**:
  - `CONSTANT_NOMINAL`: Keep thresholds constant (no indexing)
  - `SCENARIO_INFLATION`: Index to scenario's inflation rate
  - `CUSTOM_RATE`: Index to user-defined rate
- **New `TaxTable` model**:
  - Stores editable tax brackets and standard deductions per scenario
  - Fields: `jurisdiction` (FED/CA), `filing_status`, `year_base`, `brackets_json`, `standard_deduction`
  - Helper methods: `get_brackets()`, `set_brackets()`
- **Updated `Scenario` model**: Added relationship to `tax_tables`

### 2. Schemas (`backend/schemas.py`)
- Updated `TaxFundingSettingsBase`, `TaxFundingSettingsCreate`, `TaxFundingSettingsRead` to include indexing policy fields
- New schemas: `TaxBracketSchema`, `TaxTableBase`, `TaxTableCreate`, `TaxTableRead`

### 3. API Endpoints (`backend/main.py`)
- **Updated `/api/scenarios/{scenario_id}/settings`**:
  - GET: Now returns `tax_table_indexing_policy` and `tax_table_custom_index_rate`
  - PUT: Now accepts and validates indexing policy fields
- **New `/api/scenarios/{scenario_id}/tax-tables`**:
  - GET: Returns all tax tables for a scenario
  - PUT `/api/scenarios/{scenario_id}/tax-tables/{jurisdiction}`: Creates or updates a tax table
  - Validates: bracket thresholds ascending, rates 0-1, standard deduction non-negative, custom index rate -5% to +15%

### 4. Tax Engine Integration (`backend/tax_config.py`, `backend/tax_engine.py`)
- **New function `apply_tax_table_indexing()`** in `tax_config.py`:
  - Applies indexing policy to tax table thresholds and standard deduction
  - Supports CONSTANT_NOMINAL, SCENARIO_INFLATION, and CUSTOM_RATE policies
  - Rates are NOT indexed (only thresholds and deductions)
- **Updated `calculate_taxes()`** in `tax_engine.py`:
  - Now accepts optional `custom_fed_table`, `custom_state_table`, `indexing_policy`, `year_base`, `scenario_inflation_rate`, `custom_index_rate`
  - Uses custom tables if provided, otherwise falls back to hardcoded tables
  - Applies indexing when custom tables are used

### 5. Simulation Integration (`backend/simulation.py`)
- Loads custom tax tables from database at simulation start
- Loads indexing policy from `TaxFundingSettings`
- Passes custom tables and indexing parameters to `calculate_taxes()` for each year
- Supports both initial tax calculation and iterative tax funding calculations

### 6. Frontend Types (`frontend/src/types.ts`)
- Added `TaxTableIndexingPolicy` type
- Updated `TaxFundingSettings` and `TaxFundingSettingsCreate` interfaces
- Added `TaxBracket`, `TaxTable`, `TaxTableCreate` interfaces

## ⏳ Remaining (Frontend UI)

### 1. Settings Menu Component
**Location**: Create `frontend/src/components/SettingsMenu.tsx`

**Requirements**:
- List of settings items:
  - "Tax Funding Policy" → navigates to existing tax funding settings
  - "Tax Tables" → navigates to tax tables editor
  - "Tax Table Indexing Policy" → navigates to indexing policy editor
- Each item should be clickable and navigate to its respective screen
- Should be accessible from scenario detail page (replace or augment existing "Settings" button)

### 2. Tax Tables Editor Component
**Location**: Create `frontend/src/components/TaxTablesEditor.tsx`

**Requirements**:
- Show federal and CA sections (tabs or accordion)
- For each jurisdiction:
  - Editable standard deduction field
  - Editable bracket table with columns: "Up To" (threshold) and "Rate" (%)
  - Add/remove bracket rows buttons
  - Validation: thresholds ascending, rates 0-100%, standard deduction >= 0
- Save/Cancel buttons
- Load existing tables on mount
- Display validation errors in UI

### 3. Tax Table Indexing Policy Component
**Location**: Create `frontend/src/components/TaxTableIndexingPolicy.tsx`

**Requirements**:
- Radio/select control with three options:
  - "Keep constant (nominal)"
  - "Index to scenario inflation"
  - "Custom rate"
- If "Custom rate" selected, show numeric input for percentage (-5% to 15%)
- Save/Cancel buttons
- Load current policy from settings on mount

### 4. API Client Updates
**Location**: `frontend/src/api/client.ts`

**Required functions**:
```typescript
export async function getTaxTables(scenarioId: number): Promise<TaxTable[]>
export async function upsertTaxTable(scenarioId: number, jurisdiction: "FED" | "CA", table: TaxTableCreate): Promise<TaxTable>
```

**Update existing**:
- `getTaxFundingSettings()`: Should now return indexing policy fields
- `updateTaxFundingSettings()`: Should now accept indexing policy fields

### 5. Update Existing Settings Dialog
**Location**: `frontend/src/components/ScenarioDetail.tsx`

**Changes needed**:
- Update `handleSaveTaxSettings()` to include indexing policy fields
- Update `loadTaxSettings()` to handle new fields
- Consider splitting into separate screens or tabs

## 📝 How to Add a New Setting Item in the Future

1. **Backend**:
   - Add field to `TaxFundingSettings` model (if setting-specific) OR create new model/table
   - Add schema in `schemas.py`
   - Add API endpoint in `main.py` if needed
   - Update simulation logic if setting affects calculations

2. **Frontend**:
   - Add type definitions in `types.ts`
   - Add API client functions in `api/client.ts`
   - Create new component for the setting (or add to existing component)
   - Add menu item to `SettingsMenu.tsx` that navigates to the new component

## 🧪 Testing Recommendations

### Backend Tests Needed:
1. **Settings persistence**: Save and load indexing policy
2. **Tax table CRUD**: Create, read, update tax tables
3. **Indexing calculations**:
   - CONSTANT_NOMINAL: thresholds unchanged
   - SCENARIO_INFLATION: thresholds *= (1+infl)^years
   - CUSTOM_RATE: thresholds *= (1+custom)^years
4. **Regression**: inflation=0 and custom=0 should yield same tax as baseline

### Frontend Tests Needed:
1. Settings menu navigation
2. Tax table editor validation
3. Indexing policy form validation
4. Save/cancel functionality

## 📋 Database Migration Notes

The new fields in `TaxFundingSettings` and the new `TaxTable` table will be automatically created by SQLModel on next database initialization. For existing databases, you may need to:

1. Add columns to `taxfundingsettings` table:
   - `tax_table_indexing_policy` (TEXT, default 'CONSTANT_NOMINAL')
   - `tax_table_custom_index_rate` (REAL, nullable)

2. Create `taxtable` table with columns:
   - `id`, `scenario_id`, `jurisdiction`, `filing_status`, `year_base`
   - `brackets_json` (TEXT), `standard_deduction` (REAL)
   - `schema_version`, `notes`, `created_at`, `updated_at`

## 🎯 Next Steps

1. Create frontend UI components (Settings Menu, Tax Tables Editor, Indexing Policy)
2. Update API client with new endpoints
3. Test end-to-end: create scenario → edit tax tables → set indexing policy → run simulation
4. Add backend tests for indexing calculations
5. Add frontend validation and error handling

## 📚 Key Files Modified

- `backend/models.py`: Added TaxTable model, extended TaxFundingSettings
- `backend/schemas.py`: Added tax table schemas, extended settings schemas
- `backend/main.py`: Added tax table endpoints, updated settings endpoints
- `backend/tax_config.py`: Added `apply_tax_table_indexing()` function
- `backend/tax_engine.py`: Updated `calculate_taxes()` to accept custom tables
- `backend/simulation.py`: Loads and uses custom tax tables with indexing
- `frontend/src/types.ts`: Added tax table and indexing policy types

