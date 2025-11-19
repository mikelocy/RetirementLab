import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { 
  Typography, Card, CardContent, Grid, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Button, TextField, Box, Divider 
} from '@mui/material';
import { getScenario, getAssets, createAsset, runSimpleBondSimulation } from '../api/client';
import { Scenario, Asset, AssetCreate, SimpleBondSimulationResult } from '../types';
import SimulationChart from './SimulationChart';

const ScenarioDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const scenarioId = parseInt(id || '0', 10);
  
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [simulationResult, setSimulationResult] = useState<SimpleBondSimulationResult | null>(null);
  
  const [newAsset, setNewAsset] = useState<AssetCreate>({
    name: '',
    type: 'taxable',
    current_balance: 0
  });

  const loadData = async () => {
    if (!scenarioId) return;
    try {
      const s = await getScenario(scenarioId);
      setScenario(s);
      const a = await getAssets(scenarioId);
      setAssets(a);
    } catch (error) {
      console.error("Error loading scenario data", error);
    }
  };

  useEffect(() => {
    loadData();
  }, [scenarioId]);

  const handleAddAsset = async () => {
    try {
      await createAsset(scenarioId, newAsset);
      setNewAsset({ name: '', type: 'taxable', current_balance: 0 });
      const a = await getAssets(scenarioId);
      setAssets(a);
    } catch (error) {
      console.error("Error creating asset", error);
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

  if (!scenario) return <Typography>Loading...</Typography>;

  return (
    <Grid container spacing={3} direction="column">
      {/* 1) Scenario Card */}
      <Grid item>
        <Card>
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
                <Typography variant="body2">Contrib (Pre): ${scenario.annual_contribution_pre_retirement.toLocaleString()}</Typography>
                <Typography variant="body2">Spend (Post): ${scenario.annual_spending_in_retirement.toLocaleString()}</Typography>
              </Grid>
            </Grid>
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
                  </TableRow>
                </TableHead>
                <TableBody>
                  {assets.map(asset => (
                    <TableRow key={asset.id}>
                      <TableCell>{asset.name}</TableCell>
                      <TableCell>{asset.type}</TableCell>
                      <TableCell align="right">${asset.current_balance.toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                  {assets.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} align="center">No assets added yet.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="subtitle2" gutterBottom>Add New Asset</Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <TextField 
                label="Name" 
                size="small" 
                value={newAsset.name} 
                onChange={(e) => setNewAsset({...newAsset, name: e.target.value})} 
              />
              <TextField 
                label="Type" 
                size="small" 
                value={newAsset.type} 
                onChange={(e) => setNewAsset({...newAsset, type: e.target.value})} 
                helperText="e.g. taxable, 401k, roth"
              />
              <TextField 
                label="Balance" 
                type="number" 
                size="small" 
                value={newAsset.current_balance} 
                onChange={(e) => setNewAsset({...newAsset, current_balance: parseFloat(e.target.value)})} 
              />
              <Button variant="contained" onClick={handleAddAsset} sx={{ mt: 0.5 }}>
                Add Asset
              </Button>
            </Box>
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
    </Grid>
  );
};

export default ScenarioDetail;
