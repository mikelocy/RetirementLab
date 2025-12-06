import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { 
  Typography, Card, CardContent, Grid, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Button, TextField, Box, Divider, Dialog, DialogTitle, DialogContent, DialogActions,
  FormControl, InputLabel, Select, MenuItem, IconButton, InputAdornment, Checkbox, FormControlLabel
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import { NumericFormat } from 'react-number-format';
import { getScenario, getAssets, createAsset, runSimpleBondSimulation, updateScenario, updateAsset, deleteAsset, getIncomeSources, createIncomeSource, updateIncomeSource, deleteIncomeSource } from '../api/client';
import { Scenario, ScenarioCreate, Asset, AssetCreate, AssetType, SimpleBondSimulationResult, IncomeSource, FilingStatus, IncomeType } from '../types';
import SimulationChart from './SimulationChart';
import SimulationTable from './SimulationTable';

// Helper function to format currency for display
const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

// Helper component for currency input with formatting
const CurrencyInput: React.FC<{
  label: string;
  value: number | "";
  onChange: (value: number | "") => void;
  required?: boolean;
}> = ({ label, value, onChange, required }) => {
  return (
    <NumericFormat
      customInput={TextField}
      fullWidth
      size="small"
      label={label}
      value={value === "" ? "" : value}
      onValueChange={(values) => {
        const { floatValue } = values;
        if (floatValue === undefined) {
          onChange("");
        } else {
          onChange(floatValue);
        }
      }}
      required={required}
      thousandSeparator=","
      prefix="$"
      decimalScale={0}
      allowNegative={false}
    />
  );
};

interface AssetFormProps {
  newAssetName: string; setNewAssetName: (v: string) => void;
  newAssetType: AssetType; setNewAssetType: (v: AssetType) => void;
  rePropertyType: string; setRePropertyType: (v: string) => void;
  rePropertyValue: number | ""; setRePropertyValue: (v: number | "") => void;
  reMortgageBalance: number | ""; setReMortgageBalance: (v: number | "") => void;
  reInterestRate: number | ""; setReInterestRate: (v: number | "") => void;
  reAnnualRent: number | ""; setReAnnualRent: (v: number | "") => void;
  reAppreciationRate: number | ""; setReAppreciationRate: (v: number | "") => void;
  reMortgageTerm: number | ""; setReMortgageTerm: (v: number | "") => void;
  reCurrentYear: number | ""; setReCurrentYear: (v: number | "") => void;
  reIsInterestOnly: boolean; setReIsInterestOnly: (v: boolean) => void;
  rePurchasePrice: number | ""; setRePurchasePrice: (v: number | "") => void;
  reLandValue: number | ""; setReLandValue: (v: number | "") => void;
  reDepreciationMethod: "none" | "residential_27_5" | "commercial_39"; setReDepreciationMethod: (v: "none" | "residential_27_5" | "commercial_39") => void;
  reDepreciationStartYear: number | ""; setReDepreciationStartYear: (v: number | "") => void;
  reAccumulatedDepreciation: number | ""; setReAccumulatedDepreciation: (v: number | "") => void;
  rePrimaryResidenceStartAge: number | ""; setRePrimaryResidenceStartAge: (v: number | "") => void;
  rePrimaryResidenceEndAge: number | ""; setRePrimaryResidenceEndAge: (v: number | "") => void;
  geAccountType: string; setGeAccountType: (v: string) => void;
  geAccountBalance: number | ""; setGeAccountBalance: (v: number | "") => void;
  geExpectedReturnRate: number | ""; setGeExpectedReturnRate: (v: number | "") => void;
  geFeeRate: number | ""; setGeFeeRate: (v: number | "") => void;
  geCostBasis: number | ""; setGeCostBasis: (v: number | "") => void;
  
  // Specific Stock Props
  stockTicker: string; setStockTicker: (v: string) => void;
  stockShares: number | ""; setStockShares: (v: number | "") => void;
  stockPrice: number | ""; setStockPrice: (v: number | "") => void;
  stockAppreciation: number | ""; setStockAppreciation: (v: number | "") => void;
  stockDividend: number | ""; setStockDividend: (v: number | "") => void;
  stockCostBasis: number | ""; setStockCostBasis: (v: number | "") => void;
}

const AssetForm: React.FC<AssetFormProps> = ({
  newAssetName, setNewAssetName,
  newAssetType, setNewAssetType,
  rePropertyType, setRePropertyType,
  rePropertyValue, setRePropertyValue,
  reMortgageBalance, setReMortgageBalance,
  reInterestRate, setReInterestRate,
  reAnnualRent, setReAnnualRent,
  reAppreciationRate, setReAppreciationRate,
  reMortgageTerm, setReMortgageTerm,
  reCurrentYear, setReCurrentYear,
  reIsInterestOnly, setReIsInterestOnly,
  rePurchasePrice, setRePurchasePrice,
  reLandValue, setReLandValue,
  reDepreciationMethod, setReDepreciationMethod,
  reDepreciationStartYear, setReDepreciationStartYear,
  reAccumulatedDepreciation, setReAccumulatedDepreciation,
  rePrimaryResidenceStartAge, setRePrimaryResidenceStartAge,
  rePrimaryResidenceEndAge, setRePrimaryResidenceEndAge,
  geAccountType, setGeAccountType,
  geAccountBalance, setGeAccountBalance,
  geExpectedReturnRate, setGeExpectedReturnRate,
  geFeeRate, setGeFeeRate,
  geCostBasis, setGeCostBasis,
  stockTicker, setStockTicker,
  stockShares, setStockShares,
  stockPrice, setStockPrice,
  stockAppreciation, setStockAppreciation,
  stockDividend, setStockDividend,
  stockCostBasis, setStockCostBasis
}) => (
    <Grid container spacing={2} alignItems="flex-start" sx={{ width: '100%', maxWidth: '100%' }}>
      <Grid item xs={12} sm={6}>
        <TextField 
          fullWidth 
          label="Name" 
          size="small" 
          value={newAssetName} 
          onChange={(e) => setNewAssetName(e.target.value)} 
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <FormControl fullWidth size="small">
          <InputLabel>Type</InputLabel>
          <Select
            value={newAssetType}
            label="Type"
            onChange={(e) => setNewAssetType(e.target.value as AssetType)}
          >
            <MenuItem value="general_equity">General Equity</MenuItem>
            <MenuItem value="real_estate">Real Estate</MenuItem>
            <MenuItem value="specific_stock">Specific Stock</MenuItem>
          </Select>
        </FormControl>
      </Grid>

      {newAssetType === 'real_estate' ? (
        <>
          <Grid item xs={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Property Type</InputLabel>
              <Select
                value={rePropertyType}
                label="Property Type"
                onChange={(e) => setRePropertyType(e.target.value)}
              >
                <MenuItem value="primary">Primary Residence</MenuItem>
                <MenuItem value="rental">Rental Property</MenuItem>
                <MenuItem value="land">Land</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6}>
            <CurrencyInput label="Property Value *" value={rePropertyValue} onChange={setRePropertyValue} required />
          </Grid>
          <Grid item xs={6}>
            <CurrencyInput label="Mortgage Balance" value={reMortgageBalance} onChange={setReMortgageBalance} />
          </Grid>
          <Grid item xs={6}>
            <TextField fullWidth size="small" type="number" label="Interest Rate (0.04)" value={reInterestRate} onChange={(e) => setReInterestRate(e.target.value === "" ? "" : parseFloat(e.target.value))} />
          </Grid>
          <Grid item xs={6}>
            <CurrencyInput label="Annual Rent" value={reAnnualRent} onChange={setReAnnualRent} />
          </Grid>
          <Grid item xs={6}>
            <TextField fullWidth size="small" type="number" label="Appreciation Rate" value={reAppreciationRate} onChange={(e) => {
              const val = e.target.value;
              if (val === "") {
                setReAppreciationRate("");
              } else {
                const parsed = parseFloat(val);
                setReAppreciationRate(isNaN(parsed) ? "" : parsed);
              }
            }} inputProps={{ step: 0.001, min: 0 }} />
          </Grid>
          
          {/* Mortgage Details */}
          <Grid item xs={4}>
            <TextField 
              fullWidth 
              size="small" 
              type="number" 
              label="Loan Term (Years)" 
              value={reMortgageTerm} 
              onChange={(e) => setReMortgageTerm(e.target.value === "" ? "" : parseFloat(e.target.value))} 
            />
          </Grid>
          <Grid item xs={4}>
            <TextField 
              fullWidth 
              size="small" 
              type="number" 
              label="Current Year" 
              value={reCurrentYear} 
              onChange={(e) => setReCurrentYear(e.target.value === "" ? "" : parseFloat(e.target.value))} 
              helperText={`Remaining: ${reMortgageTerm === "" || reCurrentYear === "" ? "-" : Math.max(0, Number(reMortgageTerm) - Number(reCurrentYear) + 1)} yrs`}
            />
          </Grid>
          <Grid item xs={4} sx={{ display: 'flex', alignItems: 'center' }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={reIsInterestOnly}
                  onChange={(e) => setReIsInterestOnly(e.target.checked)}
                  size="small"
                />
              }
              label="Interest Only"
            />
          </Grid>
          
          {/* Tax-Related Fields */}
          <Grid item xs={12}>
            <Divider sx={{ my: 1 }}>Tax Information</Divider>
          </Grid>
          
          <Grid item xs={6}>
            <CurrencyInput 
              label="Purchase Price" 
              value={rePurchasePrice} 
              onChange={setRePurchasePrice}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Original acquisition cost (for capital gains calculation)
            </Typography>
          </Grid>
          
          <Grid item xs={6}>
            <CurrencyInput 
              label="Land Value" 
              value={reLandValue} 
              onChange={setReLandValue}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Portion of purchase price that's land (not depreciable)
            </Typography>
          </Grid>
          
          {(rePropertyType === "rental") && (
            <>
              <Grid item xs={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Depreciation Method</InputLabel>
                  <Select
                    value={reDepreciationMethod}
                    label="Depreciation Method"
                    onChange={(e) => setReDepreciationMethod(e.target.value as "none" | "residential_27_5" | "commercial_39")}
                  >
                    <MenuItem value="none">None</MenuItem>
                    <MenuItem value="residential_27_5">Residential Rental (27.5 years)</MenuItem>
                    <MenuItem value="commercial_39">Commercial (39 years)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              {reDepreciationMethod !== "none" && (
                <>
                  <Grid item xs={6}>
                    <TextField 
                      fullWidth 
                      size="small" 
                      type="number" 
                      label="Depreciation Start Year" 
                      value={reDepreciationStartYear} 
                      onChange={(e) => setReDepreciationStartYear(e.target.value === "" ? "" : parseInt(e.target.value))}
                      helperText="Year depreciation began"
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <CurrencyInput 
                      label="Accumulated Depreciation" 
                      value={reAccumulatedDepreciation} 
                      onChange={setReAccumulatedDepreciation}
                    />
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                      Total depreciation taken to date
                    </Typography>
                  </Grid>
                </>
              )}
            </>
          )}
          
          {rePropertyType === "primary" && (
            <Grid item xs={12}>
              <Typography variant="caption" color="text.secondary">
                Primary residences may qualify for capital gains exclusion: $250k (single) or $500k (married filing jointly) if owned and used as primary residence for 2 of the last 5 years.
              </Typography>
            </Grid>
          )}
          
          {/* Primary Residence Fields (for capital gains exclusion) */}
          {(rePropertyType === "primary") && (
            <>
              <Grid item xs={12}>
                <Divider sx={{ my: 1 }}>Primary Residence (for Capital Gains Exclusion)</Divider>
              </Grid>
              <Grid item xs={6}>
                <TextField 
                  fullWidth 
                  size="small" 
                  type="number" 
                  label="Primary Residence Start Age" 
                  value={rePrimaryResidenceStartAge} 
                  onChange={(e) => setRePrimaryResidenceStartAge(e.target.value === "" ? "" : parseInt(e.target.value))}
                  helperText="Age when property became primary residence"
                />
              </Grid>
              <Grid item xs={6}>
                <TextField 
                  fullWidth 
                  size="small" 
                  type="number" 
                  label="Primary Residence End Age" 
                  value={rePrimaryResidenceEndAge} 
                  onChange={(e) => setRePrimaryResidenceEndAge(e.target.value === "" ? "" : parseInt(e.target.value))}
                  helperText="Age when property stopped being primary residence (leave blank if still primary)"
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="caption" color="text.secondary">
                  Note: To sell this property, create a "House Sale" income source instead of setting a sale age here.
                </Typography>
              </Grid>
            </>
          )}
        </>
      ) : newAssetType === 'general_equity' ? (
        <>
          <Grid item xs={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Account Type</InputLabel>
              <Select
                value={geAccountType}
                label="Account Type"
                onChange={(e) => setGeAccountType(e.target.value)}
              >
                <MenuItem value="taxable">Taxable Brokerage</MenuItem>
                <MenuItem value="ira">IRA</MenuItem>
                <MenuItem value="roth">Roth IRA</MenuItem>
                <MenuItem value="401k">401(k)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6}>
            <CurrencyInput label="Balance *" value={geAccountBalance} onChange={setGeAccountBalance} required />
          </Grid>
          <Grid item xs={6}>
            <TextField fullWidth size="small" type="number" label="Expected Return (0.07)" value={geExpectedReturnRate} onChange={(e) => setGeExpectedReturnRate(e.target.value === "" ? "" : parseFloat(e.target.value))} />
          </Grid>
          <Grid item xs={6}>
            <TextField fullWidth size="small" type="number" label="Fee Rate (0.001)" value={geFeeRate} onChange={(e) => setGeFeeRate(e.target.value === "" ? "" : parseFloat(e.target.value))} />
          </Grid>
          {(geAccountType === "taxable" || geAccountType === "") && (
            <Grid item xs={6}>
              <CurrencyInput 
                label="Cost Basis (for taxable accounts)" 
                value={geCostBasis} 
                onChange={setGeCostBasis}
                required={geAccountType === "taxable"}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                Original purchase price. Used to calculate capital gains on withdrawals. Defaults to current balance if not set.
              </Typography>
            </Grid>
          )}
        </>
      ) : (
        // Specific Stock Form
        <>
          <Grid item xs={6}>
            <TextField 
              fullWidth 
              size="small" 
              label="Ticker Symbol" 
              value={stockTicker} 
              onChange={(e) => setStockTicker(e.target.value)} 
            />
          </Grid>
          <Grid item xs={6}>
            <TextField 
              fullWidth 
              size="small" 
              type="number" 
              label="Shares Owned *" 
              value={stockShares} 
              onChange={(e) => setStockShares(e.target.value === "" ? "" : parseFloat(e.target.value))} 
              required
            />
          </Grid>
          <Grid item xs={6}>
            <CurrencyInput 
              label="Current Price *" 
              value={stockPrice} 
              onChange={setStockPrice} 
              required 
            />
          </Grid>
          <Grid item xs={6}>
            <TextField 
              fullWidth 
              size="small" 
              type="number" 
              label="Assumed Appreciation (0.08)" 
              value={stockAppreciation} 
              onChange={(e) => setStockAppreciation(e.target.value === "" ? "" : parseFloat(e.target.value))} 
            />
          </Grid>
          <Grid item xs={6}>
            <CurrencyInput 
              label="Cost Basis (original purchase price)" 
              value={stockCostBasis} 
              onChange={setStockCostBasis}
            />
          </Grid>
          {/* Future: Dividends */}
        </>
      )}
    </Grid>
);

const ScenarioDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const scenarioId = parseInt(id || '0', 10);
  
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [incomeSources, setIncomeSources] = useState<IncomeSource[]>([]);
  const [simulationResult, setSimulationResult] = useState<SimpleBondSimulationResult | null>(null);
  
  // Scenario Edit State
  const [editOpen, setEditOpen] = useState(false);
  const [editScenario, setEditScenario] = useState<ScenarioCreate>({
    name: '',
    description: '',
    current_age: 30,
    retirement_age: 65,
    end_age: 95,
    inflation_rate: 0.03,
    bond_return_rate: 0.04,
    annual_contribution_pre_retirement: 20000,
    annual_spending_in_retirement: 120000,
    filing_status: 'married_filing_jointly'
  });

  // Asset Create State (Dialog)
  const [addAssetOpen, setAddAssetOpen] = useState(false);
  const [newAssetName, setNewAssetName] = useState("");

  // ... (Asset details state remains) ...
  
  // Income Source State
  const [addIncomeSourceOpen, setAddIncomeSourceOpen] = useState(false);
  const [newIncomeName, setNewIncomeName] = useState("");
  const [newIncomeAmount, setNewIncomeAmount] = useState<number | "">("");
  const [newIncomeStartAge, setNewIncomeStartAge] = useState<number | "">("");
  const [newIncomeEndAge, setNewIncomeEndAge] = useState<number | "">("");
  const [newIncomeAppreciation, setNewIncomeAppreciation] = useState<number | "">("");
  const [newIncomeType, setNewIncomeType] = useState<"income" | "drawdown" | "house_sale">("income");
  const [newIncomeTaxType, setNewIncomeTaxType] = useState<IncomeType>("ordinary");
  const [newIncomeLinkedAsset, setNewIncomeLinkedAsset] = useState<number | "">("");
  const [editingIncomeId, setEditingIncomeId] = useState<number | null>(null);
  const [newAssetType, setNewAssetType] = useState<AssetType>("general_equity");

  // Real estate-specific state
  const [rePropertyType, setRePropertyType] = useState("rental");
  const [rePropertyValue, setRePropertyValue] = useState<number | "">("");
  const [reMortgageBalance, setReMortgageBalance] = useState<number | "">("");
  const [reInterestRate, setReInterestRate] = useState<number | "">("");
  const [reAnnualRent, setReAnnualRent] = useState<number | "">("");
  const [reAppreciationRate, setReAppreciationRate] = useState<number | "">("");
  const [reMortgageTerm, setReMortgageTerm] = useState<number | "">(30);
  const [reCurrentYear, setReCurrentYear] = useState<number | "">(1);
  const [reIsInterestOnly, setReIsInterestOnly] = useState(false);
  // Real estate tax fields
  const [rePurchasePrice, setRePurchasePrice] = useState<number | "">("");
  const [reLandValue, setReLandValue] = useState<number | "">("");
  const [reDepreciationMethod, setReDepreciationMethod] = useState<"none" | "residential_27_5" | "commercial_39">("none");
  const [reDepreciationStartYear, setReDepreciationStartYear] = useState<number | "">("");
  const [reAccumulatedDepreciation, setReAccumulatedDepreciation] = useState<number | "">("");
  // Real estate sale fields
  const [rePrimaryResidenceStartAge, setRePrimaryResidenceStartAge] = useState<number | "">("");
  const [rePrimaryResidenceEndAge, setRePrimaryResidenceEndAge] = useState<number | "">("");

  // General equity-specific state
  const [geAccountType, setGeAccountType] = useState("taxable");
  const [geAccountBalance, setGeAccountBalance] = useState<number | "">("");
  const [geExpectedReturnRate, setGeExpectedReturnRate] = useState<number | "">("");
  const [geFeeRate, setGeFeeRate] = useState<number | "">("");
  const [geCostBasis, setGeCostBasis] = useState<number | "">("");

  // Specific Stock State
  const [stockTicker, setStockTicker] = useState("");
  const [stockShares, setStockShares] = useState<number | "">("");
  const [stockPrice, setStockPrice] = useState<number | "">("");
  const [stockAppreciation, setStockAppreciation] = useState<number | "">("");
  const [stockDividend, setStockDividend] = useState<number | "">("");
  const [stockCostBasis, setStockCostBasis] = useState<number | "">("");

  // Asset Edit State
  const [assetEditOpen, setAssetEditOpen] = useState(false);
  const [editingAssetId, setEditingAssetId] = useState<number | null>(null);
  
  const resetAssetForm = () => {
    setNewAssetName("");
    setNewAssetType("general_equity");
    setRePropertyType("rental");
    setRePropertyValue("");
    setReMortgageBalance("");
    setReInterestRate("");
    setReAnnualRent("");
    setReAppreciationRate("");
    setReMortgageTerm(30);
    setReCurrentYear(1);
    setReIsInterestOnly(false);
    setRePurchasePrice("");
    setReLandValue("");
    setReDepreciationMethod("none");
    setReDepreciationStartYear("");
    setReAccumulatedDepreciation("");
    setRePrimaryResidenceStartAge("");
    setRePrimaryResidenceEndAge("");
    setGeAccountType("taxable");
    setGeAccountBalance("");
    setGeExpectedReturnRate("");
    setGeFeeRate("");
    setGeCostBasis("");
    setStockTicker("");
    setStockShares("");
    setStockPrice("");
    setStockAppreciation("");
    setStockDividend("");
    setStockCostBasis("");
    setEditingAssetId(null);
  };

  const resetIncomeForm = () => {
    setNewIncomeName("");
    setNewIncomeAmount("");
    setNewIncomeStartAge("");
    setNewIncomeEndAge("");
    setNewIncomeAppreciation("");
    setNewIncomeType("income");
    setNewIncomeTaxType("ordinary");
    setNewIncomeLinkedAsset("");
    setEditingIncomeId(null);
  };

  const loadData = async () => {
    if (!scenarioId) return;
    try {
      const s = await getScenario(scenarioId);
      setScenario(s);
      // Pre-fill edit form
      setEditScenario({
        name: s.name,
        description: s.description || '',
        current_age: s.current_age,
        retirement_age: s.retirement_age,
        end_age: s.end_age,
        inflation_rate: s.inflation_rate,
        bond_return_rate: s.bond_return_rate,
        annual_contribution_pre_retirement: s.annual_contribution_pre_retirement,
        annual_spending_in_retirement: s.annual_spending_in_retirement,
        filing_status: s.filing_status
      });
      const a = await getAssets(scenarioId);
      setAssets(a);
      const inc = await getIncomeSources(scenarioId);
      setIncomeSources(inc);
    } catch (error) {
      console.error("Error loading scenario data", error);
    }
  };

  useEffect(() => {
    loadData();
  }, [scenarioId]);

  const handleSaveAsset = async (isUpdate: boolean) => {
    if (!scenario) return;
    if (!newAssetName.trim()) return;

    let payload: AssetCreate;

    if (newAssetType === "real_estate") {
      if (rePropertyValue === "" || isNaN(Number(rePropertyValue))) return;
      
      payload = {
        name: newAssetName.trim(),
        type: "real_estate",
        real_estate_details: {
          property_type: rePropertyType,
          property_value: Number(rePropertyValue),
          mortgage_balance: reMortgageBalance === "" ? 0 : Number(reMortgageBalance),
          interest_rate: reInterestRate === "" ? 0 : Number(reInterestRate),
          annual_rent: reAnnualRent === "" ? 0 : Number(reAnnualRent),
          appreciation_rate: reAppreciationRate === "" ? 0 : Number(reAppreciationRate),
          mortgage_term_years: reMortgageTerm === "" ? 30 : Number(reMortgageTerm),
          mortgage_current_year: reCurrentYear === "" ? 1 : Number(reCurrentYear),
          is_interest_only: reIsInterestOnly,
          purchase_price: rePurchasePrice === "" ? (rePropertyValue === "" ? 0 : Number(rePropertyValue)) : Number(rePurchasePrice),
          land_value: reLandValue === "" ? 0 : Number(reLandValue),
          depreciation_method: reDepreciationMethod,
          depreciation_start_year: reDepreciationStartYear === "" ? null : Number(reDepreciationStartYear),
          accumulated_depreciation: reAccumulatedDepreciation === "" ? 0 : Number(reAccumulatedDepreciation),
          primary_residence_start_age: rePrimaryResidenceStartAge === "" ? null : Number(rePrimaryResidenceStartAge),
          primary_residence_end_age: rePrimaryResidenceEndAge === "" ? null : Number(rePrimaryResidenceEndAge),
        },
      };
    } else if (newAssetType === "general_equity") {
      if (geAccountBalance === "" || isNaN(Number(geAccountBalance))) return;
      
      payload = {
        name: newAssetName.trim(),
        type: "general_equity",
        general_equity_details: {
          account_type: geAccountType,
          account_balance: Number(geAccountBalance),
          expected_return_rate: geExpectedReturnRate === "" ? 0 : Number(geExpectedReturnRate),
          fee_rate: geFeeRate === "" ? 0 : Number(geFeeRate),
          cost_basis: geCostBasis === "" ? (geAccountType === "taxable" ? Number(geAccountBalance) : 0) : Number(geCostBasis),
        },
      };
    } else {
      if (stockShares === "" || isNaN(Number(stockShares))) return;
      if (stockPrice === "" || isNaN(Number(stockPrice))) return;

      payload = {
        name: newAssetName.trim(),
        type: "specific_stock",
        specific_stock_details: {
          ticker: stockTicker,
          shares_owned: Number(stockShares),
          current_price: Number(stockPrice),
          assumed_appreciation_rate: stockAppreciation === "" ? 0 : Number(stockAppreciation),
          dividend_yield: stockDividend === "" ? 0 : Number(stockDividend),
          cost_basis: stockCostBasis === "" ? (Number(stockShares) * Number(stockPrice)) : Number(stockCostBasis),
        }
      };
    }

    try {
      if (isUpdate && editingAssetId) {
        await updateAsset(editingAssetId, payload);
        setAssetEditOpen(false);
      } else {
        await createAsset(scenario.id, payload);
      }
      
      // Refresh assets list
      const updatedAssets = await getAssets(scenario.id);
      setAssets(updatedAssets);

      // Clear form fields
      resetAssetForm();

    } catch (error) {
      console.error("Error saving asset", error);
    }
  };

  const handleDeleteAsset = async (assetId: number) => {
    if (!window.confirm("Are you sure you want to delete this asset?")) return;
    try {
      await deleteAsset(assetId);
      const updatedAssets = await getAssets(scenarioId);
      setAssets(updatedAssets);
    } catch (error) {
      console.error("Error deleting asset", error);
    }
  };

  const handleEditAssetClick = (asset: Asset) => {
    setEditingAssetId(asset.id);
    setNewAssetName(asset.name);
    setNewAssetType(asset.type as AssetType);

    if (asset.type === "real_estate" && asset.real_estate_details) {
      const d = asset.real_estate_details;
      setRePropertyType(d.property_type || "rental");
      setRePropertyValue(d.property_value);
      setReMortgageBalance(d.mortgage_balance || "");
      setReInterestRate(d.interest_rate || "");
      setReAnnualRent(d.annual_rent || "");
      setReAppreciationRate(d.appreciation_rate !== undefined && d.appreciation_rate !== null ? d.appreciation_rate : "");
      setReMortgageTerm(d.mortgage_term_years || 30);
      setReCurrentYear(d.mortgage_current_year || 1);
      setReIsInterestOnly(d.is_interest_only || false);
      setRePurchasePrice((d as any).purchase_price || "");
      setReLandValue((d as any).land_value || "");
      setReDepreciationMethod((d as any).depreciation_method || "none");
      setReDepreciationStartYear((d as any).depreciation_start_year || "");
      setReAccumulatedDepreciation((d as any).accumulated_depreciation || "");
      setRePrimaryResidenceStartAge((d as any).primary_residence_start_age || "");
      setRePrimaryResidenceEndAge((d as any).primary_residence_end_age || "");
    } else if (asset.type === "general_equity" && asset.general_equity_details) {
      const d = asset.general_equity_details;
      setGeAccountType(d.account_type || "taxable");
      setGeAccountBalance(d.account_balance);
      setGeExpectedReturnRate(d.expected_return_rate || "");
      setGeFeeRate(d.fee_rate || "");
      setGeCostBasis((d as any).cost_basis || "");
    } else if (asset.type === "specific_stock" && asset.specific_stock_details) {
      const d = asset.specific_stock_details;
      setStockTicker(d.ticker || "");
      setStockShares(d.shares_owned);
      setStockPrice(d.current_price);
      setStockAppreciation(d.assumed_appreciation_rate || "");
      setStockDividend(d.dividend_yield || "");
      setStockCostBasis((d as any).cost_basis || "");
    }

    setAssetEditOpen(true);
  };

  const handleCreateIncomeSource = async () => {
    if (!scenario) return;
    
    // Validation
    if ((newIncomeType === "drawdown" || newIncomeType === "house_sale") && (newIncomeLinkedAsset === "" || newIncomeLinkedAsset === 0)) {
      alert(`Please select an asset to ${newIncomeType === "house_sale" ? "sell" : "sell/drawdown"}.`);
      return;
    }

    // Auto-generate name if empty for drawdown or house_sale
    let finalName = newIncomeName.trim();
    if ((newIncomeType === "drawdown" || newIncomeType === "house_sale") && !finalName) {
      const asset = assets.find(a => a.id === Number(newIncomeLinkedAsset));
      if (newIncomeType === "house_sale") {
        finalName = asset ? `Sale of ${asset.name}` : "House Sale";
      } else {
        finalName = asset ? `Drawdown from ${asset.name}` : "Asset Drawdown";
      }
    }

    if (!finalName) {
      alert("Please enter a Name or Description.");
      return;
    }

    if (newIncomeType !== "house_sale" && (newIncomeAmount === "" || isNaN(Number(newIncomeAmount)))) {
      alert("Please enter a valid Annual Amount.");
      return;
    }
    if (newIncomeStartAge === "" || isNaN(Number(newIncomeStartAge))) {
      alert("Please enter a Start Age.");
      return;
    }
    if (newIncomeType !== "house_sale" && (newIncomeEndAge === "" || isNaN(Number(newIncomeEndAge)))) {
      alert("Please enter an End Age.");
      return;
    }

    const payload = {
      name: finalName,
      amount: newIncomeType === "house_sale" ? 0 : Number(newIncomeAmount), // Amount not used for house_sale
      start_age: Number(newIncomeStartAge),
      end_age: newIncomeType === "house_sale" ? Number(newIncomeStartAge) : Number(newIncomeEndAge), // For house_sale, end_age = start_age (one-time sale)
      appreciation_rate: newIncomeType === "house_sale" ? 0 : (newIncomeAppreciation === "" ? 0 : Number(newIncomeAppreciation)),
      source_type: newIncomeType,
      linked_asset_id: ((newIncomeType === "drawdown" || newIncomeType === "house_sale") && newIncomeLinkedAsset !== "") ? Number(newIncomeLinkedAsset) : null,
      income_type: newIncomeType === "income" ? newIncomeTaxType : "ordinary",  // Only apply tax type to non-drawdown/house_sale income
    };

    try {
      if (editingIncomeId) {
        await updateIncomeSource(editingIncomeId, payload);
      } else {
        await createIncomeSource(scenario.id, payload);
      }
      
      const inc = await getIncomeSources(scenario.id);
      setIncomeSources(inc);
      
      // Reset form
      resetIncomeForm();
      setAddIncomeSourceOpen(false);
    } catch (error: any) {
      console.error("Error saving income source", error);
      const errorMessage = error?.response?.data?.detail || error?.message || "Failed to save income source";
      alert(`Error: ${errorMessage}`);
    }
  };

  const handleEditIncomeSourceClick = (income: IncomeSource) => {
    setEditingIncomeId(income.id);
    setNewIncomeName(income.name);
    setNewIncomeAmount(income.amount);
    setNewIncomeStartAge(income.start_age);
    setNewIncomeEndAge(income.end_age);
    setNewIncomeAppreciation(income.appreciation_rate);
    setNewIncomeType(income.source_type || "income");
    setNewIncomeTaxType(income.income_type || "ordinary");
    setNewIncomeLinkedAsset(income.linked_asset_id || "");
    setAddIncomeSourceOpen(true);
  };

  const handleDeleteIncomeSource = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this income source?")) return;
    try {
      await deleteIncomeSource(id);
      const inc = await getIncomeSources(scenarioId);
      setIncomeSources(inc);
    } catch (error) {
      console.error("Error deleting income source", error);
    }
  };

  const handleRunSimulation = async () => {
    try {
      const result = await runSimpleBondSimulation(scenarioId);
      setSimulationResult(result);
    } catch (error) {
      console.error("Error running simulation", error);
    }
  };

  const handleEditChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setEditScenario(prev => ({
      ...prev,
      [name]: name === 'name' || name === 'description' ? value : parseFloat(value)
    }));
  };

  const handleUpdateScenario = async () => {
    try {
      await updateScenario(scenarioId, editScenario);
      setEditOpen(false);
      setSimulationResult(null); // Clear old simulation results to force re-run
      loadData(); // Refresh data
    } catch (error) {
      console.error("Error updating scenario", error);
    }
  };

  if (!scenario) return <Typography>Loading...</Typography>;

  const assetFormProps = {
    newAssetName, setNewAssetName,
    newAssetType, setNewAssetType,
    rePropertyType, setRePropertyType,
    rePropertyValue, setRePropertyValue,
    reMortgageBalance, setReMortgageBalance,
    reInterestRate, setReInterestRate,
    reAnnualRent, setReAnnualRent,
    reAppreciationRate, setReAppreciationRate,
    reMortgageTerm, setReMortgageTerm,
    reCurrentYear, setReCurrentYear,
    reIsInterestOnly, setReIsInterestOnly,
    rePurchasePrice, setRePurchasePrice,
    reLandValue, setReLandValue,
    reDepreciationMethod, setReDepreciationMethod,
    reDepreciationStartYear, setReDepreciationStartYear,
    reAccumulatedDepreciation, setReAccumulatedDepreciation,
    geAccountType, setGeAccountType,
    geAccountBalance, setGeAccountBalance,
    geExpectedReturnRate, setGeExpectedReturnRate,
    geFeeRate, setGeFeeRate,
    geCostBasis, setGeCostBasis,
    stockTicker, setStockTicker,
    stockShares, setStockShares,
    stockPrice, setStockPrice,
    stockAppreciation, setStockAppreciation,
    stockDividend, setStockDividend,
    stockCostBasis, setStockCostBasis
  };

  // Calculate fixed width for chart and table alignment
  const calculateContentWidth = () => {
    if (!simulationResult || !simulationResult.ages || simulationResult.ages.length === 0) {
      return null;
    }
    const numYears = simulationResult.ages.length;
    // Table structure: Category column (~250px) + age columns (120px each)
    const categoryColumnWidth = 250;
    const ageColumnWidth = 120;
    // Calculate total width to match table
    return categoryColumnWidth + (numYears * ageColumnWidth);
  };

  const contentWidth = calculateContentWidth();

  return (
    <Box sx={{ width: '100%', maxWidth: '100%', overflowX: 'hidden' }}>
      <Grid container spacing={3} direction="column" sx={{ width: '100%', maxWidth: '100%' }}>
        {/* 1) Test Plan Card */}
        <Grid item sx={{ width: '100%', maxWidth: '100%' }}>
          <Card sx={{ position: 'relative', width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
            <CardContent sx={{ width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
              <Typography variant="h5" gutterBottom>{scenario.name}</Typography>
              {scenario.description && (
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  {scenario.description}
                </Typography>
              )}
              
              <Grid container spacing={2} sx={{ mt: 1, width: '100%', maxWidth: '100%' }}>
                <Grid item xs={12} sm={6} md={4}>
                  <Typography variant="subtitle2">Timeline</Typography>
                  <Typography variant="body2">Current Age: {scenario.current_age}</Typography>
                  <Typography variant="body2">Retirement Age: {scenario.retirement_age}</Typography>
                  <Typography variant="body2">End Age: {scenario.end_age}</Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Typography variant="subtitle2">Rates</Typography>
                  <Typography variant="body2">Inflation: {(scenario.inflation_rate * 100).toFixed(2)}%</Typography>
                  <Typography variant="body2">Bond Return: {(scenario.bond_return_rate * 100).toFixed(2)}%</Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Typography variant="subtitle2">Cash Flow</Typography>
                  <Typography variant="body2">Contrib (Pre): {formatCurrency(scenario.annual_contribution_pre_retirement)}</Typography>
                  <Typography variant="body2">Spend (Post): {formatCurrency(scenario.annual_spending_in_retirement)}</Typography>
                </Grid>
              </Grid>

              <Box sx={{ position: 'absolute', bottom: 16, right: 16 }}>
                <Button variant="outlined" size="small" onClick={() => setEditOpen(true)}>
                  Edit
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* 2) Assets Card */}
        <Grid item sx={{ width: '100%', maxWidth: '100%' }}>
          <Card sx={{ width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
            <CardContent sx={{ width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Assets</Typography>
                <Button variant="contained" size="small" onClick={() => { resetAssetForm(); setAddAssetOpen(true); }}>
                  Add Asset
                </Button>
              </Box>
              <TableContainer sx={{ maxHeight: 300, width: '100%', maxWidth: '100%' }}>
                <Table size="small" sx={{ width: '100%', maxWidth: '100%' }}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell align="right">Balance</TableCell>
                      <TableCell align="right">Cost Basis</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {assets.map(asset => {
                      const costBasis = asset.type === 'general_equity' && asset.general_equity_details 
                        ? (asset.general_equity_details as any).cost_basis 
                        : asset.type === 'specific_stock' && asset.specific_stock_details
                        ? (asset.specific_stock_details as any).cost_basis
                        : null;
                      const showCostBasis = costBasis !== null && costBasis !== undefined && costBasis > 0;
                      
                      return (
                      <TableRow key={asset.id}>
                        <TableCell>{asset.name}</TableCell>
                        <TableCell>
                          {asset.type === 'real_estate' ? 'Real Estate' : 
                           asset.type === 'general_equity' ? 'General Equity' : 
                           asset.type === 'specific_stock' ? 'Specific Stock' : asset.type}
                        </TableCell>
                        <TableCell align="right">{formatCurrency(asset.current_balance)}</TableCell>
                        <TableCell align="right">
                          {showCostBasis ? formatCurrency(costBasis) : '-'}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton size="small" onClick={() => handleEditAssetClick(asset)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" onClick={() => handleDeleteAsset(asset.id)}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                      );
                    })}
                    {assets.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} align="center">No assets added yet.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* 3) Income Sources Card */}
        <Grid item sx={{ width: '100%', maxWidth: '100%' }}>
          <Card sx={{ width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
            <CardContent sx={{ width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Income Sources</Typography>
                <Button variant="contained" size="small" onClick={() => { resetIncomeForm(); setAddIncomeSourceOpen(true); }}>
                  Add Income Source
                </Button>
              </Box>
              <TableContainer sx={{ maxHeight: 300, width: '100%', maxWidth: '100%' }}>
                <Table size="small" sx={{ width: '100%', maxWidth: '100%' }}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell align="right">Amount</TableCell>
                      <TableCell align="right">Start Age</TableCell>
                      <TableCell align="right">End Age</TableCell>
                      <TableCell align="right">Appreciation</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {incomeSources.map(inc => (
                      <TableRow key={inc.id}>
                        <TableCell>{inc.name}</TableCell>
                        <TableCell align="right">{formatCurrency(inc.amount)}</TableCell>
                        <TableCell align="right">{inc.start_age}</TableCell>
                        <TableCell align="right">{inc.end_age}</TableCell>
                        <TableCell align="right">{(inc.appreciation_rate * 100).toFixed(2)}%</TableCell>
                        <TableCell align="right">
                          <IconButton size="small" onClick={() => handleEditIncomeSourceClick(inc)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" onClick={() => handleDeleteIncomeSource(inc.id)}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                    {incomeSources.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6} align="center">No income sources added yet.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

      {/* 3) Simulation Header & Button */}
      <Grid item>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">Simple Bond Simulation</Typography>
          <Button variant="contained" color="secondary" onClick={handleRunSimulation}>
            RUN SIMULATION
          </Button>
        </Box>
      </Grid>
    </Grid>

    {/* 4 & 5) Chart and Table Container (Shared Scrollable) */}
    <Box sx={{ mt: 3, width: '100%', overflowX: 'auto', border: '1px solid #e0e0e0' }}>
      <Box sx={{ 
        width: contentWidth ? `${contentWidth}px` : '100%', 
        minWidth: contentWidth ? `${contentWidth}px` : '100%',
        display: 'block',
        position: 'relative'
      }}>
        {/* Chart */}
        <Box sx={{ width: '100%', height: 400 }}>
          <SimulationChart 
            key={`chart-${contentWidth}`} 
            data={simulationResult} 
            fixedWidth={contentWidth} 
          />
        </Box>
        
        {/* Table */}
        {simulationResult && (
          <Box sx={{ width: '100%' }}>
            <SimulationTable 
              key={`table-${contentWidth}`} 
              data={simulationResult} 
              fixedWidth={contentWidth} 
            />
          </Box>
        )}
      </Box>
    </Box>

      {/* Scenario Edit Dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Scenario</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField fullWidth label="Name" name="name" value={editScenario.name} onChange={handleEditChange} required />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth label="Description" name="description" multiline rows={2} value={editScenario.description || ''} onChange={handleEditChange} />
            </Grid>
            <Grid item xs={4}>
              <TextField fullWidth type="number" label="Current Age" name="current_age" value={editScenario.current_age} onChange={handleEditChange} />
            </Grid>
            <Grid item xs={4}>
              <TextField fullWidth type="number" label="Retirement Age" name="retirement_age" value={editScenario.retirement_age} onChange={handleEditChange} />
            </Grid>
            <Grid item xs={4}>
              <TextField fullWidth type="number" label="End Age" name="end_age" value={editScenario.end_age} onChange={handleEditChange} />
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth type="number" label="Inflation Rate (0.03 = 3%)" name="inflation_rate" value={editScenario.inflation_rate} onChange={handleEditChange} inputProps={{ step: 0.001 }} />
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth type="number" label="Bond Return Rate (0.04 = 4%)" name="bond_return_rate" value={editScenario.bond_return_rate} onChange={handleEditChange} inputProps={{ step: 0.001 }} />
            </Grid>
            <Grid item xs={6}>
              <NumericFormat
                customInput={TextField}
                fullWidth
                label="Annual Contribution (Pre)"
                value={editScenario.annual_contribution_pre_retirement}
                onValueChange={(values) => {
                  const { floatValue } = values;
                  setEditScenario(prev => ({
                    ...prev,
                    annual_contribution_pre_retirement: floatValue || 0
                  }));
                }}
                thousandSeparator=","
                prefix="$"
                decimalScale={0}
                allowNegative={false}
              />
            </Grid>
            <Grid item xs={6}>
              <NumericFormat
                customInput={TextField}
                fullWidth
                label="Annual Spending (Post)"
                value={editScenario.annual_spending_in_retirement}
                onValueChange={(values) => {
                  const { floatValue } = values;
                  setEditScenario(prev => ({
                    ...prev,
                    annual_spending_in_retirement: floatValue || 0
                  }));
                }}
                thousandSeparator=","
                prefix="$"
                decimalScale={0}
                allowNegative={false}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Tax Filing Status</InputLabel>
                <Select
                  value={editScenario.filing_status || 'married_filing_jointly'}
                  label="Tax Filing Status"
                  onChange={(e) => setEditScenario(prev => ({
                    ...prev,
                    filing_status: e.target.value as FilingStatus
                  }))}
                >
                  <MenuItem value="single">Single</MenuItem>
                  <MenuItem value="married_filing_jointly">Married Filing Jointly</MenuItem>
                  <MenuItem value="married_filing_separately">Married Filing Separately</MenuItem>
                  <MenuItem value="head_of_household">Head of Household</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdateScenario} variant="contained">Update</Button>
        </DialogActions>
      </Dialog>

      {/* Asset Edit Dialog */}
      <Dialog open={assetEditOpen} onClose={() => { setAssetEditOpen(false); resetAssetForm(); }} maxWidth="md" fullWidth>
        <DialogTitle>Edit Asset</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <AssetForm {...assetFormProps} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setAssetEditOpen(false); resetAssetForm(); }}>Cancel</Button>
          <Button onClick={() => handleSaveAsset(true)} variant="contained">Save Changes</Button>
        </DialogActions>
      </Dialog>

      {/* Add Asset Dialog */}
      <Dialog open={addAssetOpen} onClose={() => setAddAssetOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Asset</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <AssetForm {...assetFormProps} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddAssetOpen(false)}>Cancel</Button>
          <Button onClick={() => handleSaveAsset(false)} variant="contained">Add</Button>
        </DialogActions>
      </Dialog>

      {/* Add Income Source Dialog */}
      <Dialog open={addIncomeSourceOpen} onClose={() => { setAddIncomeSourceOpen(false); resetIncomeForm(); }} maxWidth="sm" fullWidth>
        <DialogTitle>{editingIncomeId ? 'Edit Income Source' : 'Add Income Source'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth size="small">
                <InputLabel>Type</InputLabel>
                <Select
                  value={newIncomeType}
                  label="Type"
                  onChange={(e) => setNewIncomeType(e.target.value as "income" | "drawdown" | "house_sale")}
                >
                  <MenuItem value="income">Income Stream (e.g. Pension)</MenuItem>
                  <MenuItem value="drawdown">Asset Drawdown (Sell Asset)</MenuItem>
                  <MenuItem value="house_sale">House Sale</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            {newIncomeType === "drawdown" && (
              <Grid item xs={12}>
                <FormControl fullWidth size="small">
                  <InputLabel>Asset to Sell</InputLabel>
                  <Select
                    value={newIncomeLinkedAsset}
                    label="Asset to Sell"
                    onChange={(e) => setNewIncomeLinkedAsset(Number(e.target.value))}
                  >
                    {assets.map(a => (
                      <MenuItem key={a.id} value={a.id}>{a.name} ({formatCurrency(a.current_balance)})</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            )}
            
            {newIncomeType === "house_sale" && (
              <Grid item xs={12}>
                <FormControl fullWidth size="small">
                  <InputLabel>Property to Sell</InputLabel>
                  <Select
                    value={newIncomeLinkedAsset}
                    label="Property to Sell"
                    onChange={(e) => setNewIncomeLinkedAsset(Number(e.target.value))}
                  >
                    {assets.filter(a => a.type === "real_estate").map(a => (
                      <MenuItem key={a.id} value={a.id}>{a.name} ({formatCurrency(a.current_balance)})</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                  Sale proceeds will be calculated automatically based on property value, appreciation, mortgage balance, and tax treatment.
                </Typography>
              </Grid>
            )}

            {newIncomeType === "income" && (
              <Grid item xs={12}>
                <FormControl fullWidth size="small">
                  <InputLabel>Tax Treatment</InputLabel>
                  <Select
                    value={newIncomeTaxType}
                    label="Tax Treatment"
                    onChange={(e) => setNewIncomeTaxType(e.target.value as IncomeType)}
                  >
                    <MenuItem value="ordinary">Ordinary Income (Fully Taxable)</MenuItem>
                    <MenuItem value="social_security">Social Security Benefits</MenuItem>
                    <MenuItem value="tax_exempt">Tax Exempt (e.g., VA Disability)</MenuItem>
                    <MenuItem value="disability">Disability Income (Tax Exempt)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            )}

            <Grid item xs={12}>
              <TextField fullWidth label={newIncomeType === "drawdown" || newIncomeType === "house_sale" ? "Description" : "Name"} value={newIncomeName} onChange={(e) => setNewIncomeName(e.target.value)} />
            </Grid>
            {newIncomeType !== "house_sale" && (
              <Grid item xs={6}>
                <CurrencyInput label={newIncomeType === "drawdown" ? "Annual Drawdown" : "Annual Amount"} value={newIncomeAmount} onChange={setNewIncomeAmount} required />
              </Grid>
            )}
            {newIncomeType !== "house_sale" && (
              <Grid item xs={6}>
                <TextField fullWidth type="number" label="Appreciation (0.00)" value={newIncomeAppreciation} onChange={(e) => setNewIncomeAppreciation(e.target.value)} />
              </Grid>
            )}
            <Grid item xs={6}>
              <TextField fullWidth type="number" label={newIncomeType === "house_sale" ? "Sale Age" : "Start Age"} value={newIncomeStartAge} onChange={(e) => setNewIncomeStartAge(e.target.value)} required />
            </Grid>
            {newIncomeType !== "house_sale" && (
              <Grid item xs={6}>
                <TextField fullWidth type="number" label="End Age" value={newIncomeEndAge} onChange={(e) => setNewIncomeEndAge(e.target.value)} required />
              </Grid>
            )}
            {newIncomeType === "house_sale" && (
              <Grid item xs={6}>
                <TextField fullWidth type="number" label="End Age (same as Sale Age)" value={newIncomeStartAge} disabled />
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setAddIncomeSourceOpen(false); resetIncomeForm(); }}>Cancel</Button>
          <Button onClick={handleCreateIncomeSource} variant="contained">{editingIncomeId ? 'Save Changes' : 'Add'}</Button>
        </DialogActions>
      </Dialog>

    </Box>
  );
};

export default ScenarioDetail;
