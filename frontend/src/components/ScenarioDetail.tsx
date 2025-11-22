import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { 
  Typography, Card, CardContent, Grid, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Button, TextField, Box, Divider, Dialog, DialogTitle, DialogContent, DialogActions,
  FormControl, InputLabel, Select, MenuItem, IconButton, InputAdornment
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import { NumericFormat } from 'react-number-format';
import { getScenario, getAssets, createAsset, runSimpleBondSimulation, updateScenario, updateAsset, deleteAsset } from '../api/client';
import { Scenario, ScenarioCreate, Asset, AssetCreate, AssetType, SimpleBondSimulationResult } from '../types';
import SimulationChart from './SimulationChart';

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

const ScenarioDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const scenarioId = parseInt(id || '0', 10);
  
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
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
    annual_spending_in_retirement: 120000
  });

  // Asset Create State
  const [newAssetName, setNewAssetName] = useState("");
  const [newAssetType, setNewAssetType] = useState<AssetType>("general_equity");

  // Real estate-specific state
  const [rePropertyType, setRePropertyType] = useState("rental");
  const [rePropertyValue, setRePropertyValue] = useState<number | "">("");
  const [reMortgageBalance, setReMortgageBalance] = useState<number | "">("");
  const [reInterestRate, setReInterestRate] = useState<number | "">("");
  const [reAnnualRent, setReAnnualRent] = useState<number | "">("");
  const [reAppreciationRate, setReAppreciationRate] = useState<number | "">("");

  // General equity-specific state
  const [geAccountType, setGeAccountType] = useState("taxable");
  const [geAccountBalance, setGeAccountBalance] = useState<number | "">("");
  const [geExpectedReturnRate, setGeExpectedReturnRate] = useState<number | "">("");
  const [geFeeRate, setGeFeeRate] = useState<number | "">("");

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
    setGeAccountType("taxable");
    setGeAccountBalance("");
    setGeExpectedReturnRate("");
    setGeFeeRate("");
    setEditingAssetId(null);
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
        annual_spending_in_retirement: s.annual_spending_in_retirement
      });
      const a = await getAssets(scenarioId);
      setAssets(a);
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
        },
      };
    } else {
      if (geAccountBalance === "" || isNaN(Number(geAccountBalance))) return;
      
      payload = {
        name: newAssetName.trim(),
        type: "general_equity",
        general_equity_details: {
          account_type: geAccountType,
          account_balance: Number(geAccountBalance),
          expected_return_rate: geExpectedReturnRate === "" ? 0 : Number(geExpectedReturnRate),
          fee_rate: geFeeRate === "" ? 0 : Number(geFeeRate),
        },
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
      setReAppreciationRate(d.appreciation_rate || "");
    } else if (asset.type === "general_equity" && asset.general_equity_details) {
      const d = asset.general_equity_details;
      setGeAccountType(d.account_type || "taxable");
      setGeAccountBalance(d.account_balance);
      setGeExpectedReturnRate(d.expected_return_rate || "");
      setGeFeeRate(d.fee_rate || "");
    }

    setAssetEditOpen(true);
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
      loadData(); // Refresh data
    } catch (error) {
      console.error("Error updating scenario", error);
    }
  };

  if (!scenario) return <Typography>Loading...</Typography>;

  // Asset Form Content Helper
  const AssetFormContent = () => (
    <Grid container spacing={2} alignItems="flex-start">
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
            <TextField fullWidth size="small" type="number" label="Appreciation Rate (0.03)" value={reAppreciationRate} onChange={(e) => setReAppreciationRate(e.target.value === "" ? "" : parseFloat(e.target.value))} />
          </Grid>
        </>
      ) : (
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
        </>
      )}
    </Grid>
  );

  return (
    <Grid container spacing={3} direction="column">
      {/* 1) Scenario Card */}
      <Grid item>
        <Card sx={{ position: 'relative' }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>{scenario.name}</Typography>
            {scenario.description && (
              <Typography variant="body2" color="textSecondary" gutterBottom>
                {scenario.description}
              </Typography>
            )}
            
            <Grid container spacing={2} sx={{ mt: 1 }}>
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
      <Grid item>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Assets</Typography>
            <TableContainer sx={{ maxHeight: 300 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell align="right">Balance</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {assets.map(asset => (
                    <TableRow key={asset.id}>
                      <TableCell>{asset.name}</TableCell>
                      <TableCell>
                        {asset.type === 'real_estate' ? 'Real Estate' : 
                         asset.type === 'general_equity' ? 'General Equity' : asset.type}
                      </TableCell>
                      <TableCell align="right">{formatCurrency(asset.current_balance)}</TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => handleEditAssetClick(asset)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={() => handleDeleteAsset(asset.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {assets.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} align="center">No assets added yet.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="subtitle2" gutterBottom>Add New Asset</Typography>
            <AssetFormContent />
            <Button variant="contained" onClick={() => handleSaveAsset(false)} sx={{ mt: 2 }}>
              Add Asset
            </Button>
          </CardContent>
        </Card>
      </Grid>

      {/* 3) Simulation Card */}
      <Grid item>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6">Simple Bond Simulation</Typography>
              <Button variant="contained" color="secondary" onClick={handleRunSimulation}>
                Run Simulation
              </Button>
            </Box>
            
            <SimulationChart data={simulationResult} />
          </CardContent>
        </Card>
      </Grid>

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
            <AssetFormContent />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setAssetEditOpen(false); resetAssetForm(); }}>Cancel</Button>
          <Button onClick={() => handleSaveAsset(true)} variant="contained">Save Changes</Button>
        </DialogActions>
      </Dialog>

    </Grid>
  );
};

export default ScenarioDetail;
