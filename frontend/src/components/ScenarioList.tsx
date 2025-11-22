import React, { useEffect, useState } from 'react';
import { 
  Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, 
  Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Grid, Box 
} from '@mui/material';
import { NumericFormat } from 'react-number-format';
import { useNavigate } from 'react-router-dom';
import { getScenarios, createScenario } from '../api/client';
import { Scenario, ScenarioCreate } from '../types';

const ScenarioList: React.FC = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  
  const [newScenario, setNewScenario] = useState<ScenarioCreate>({
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

  const fetchScenarios = async () => {
    try {
      const data = await getScenarios();
      setScenarios(data);
    } catch (error) {
      console.error("Failed to fetch scenarios", error);
    }
  };

  useEffect(() => {
    fetchScenarios();
  }, []);

  const handleCreate = async () => {
    try {
      const created = await createScenario(newScenario);
      setOpen(false);
      // Refresh list and navigate to the new scenario
      await fetchScenarios();
      navigate(`/scenarios/${created.id}`);
    } catch (error) {
      console.error("Failed to create scenario", error);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setNewScenario(prev => ({
      ...prev,
      [name]: name === 'name' || name === 'description' ? value : parseFloat(value)
    }));
  };

  return (
    <div>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h4">Scenarios</Typography>
        <Button variant="contained" onClick={() => setOpen(true)}>CREATE SCENARIO</Button>
      </Box>
      
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Current Age</TableCell>
              <TableCell>Retirement Age</TableCell>
              <TableCell>Created At</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {scenarios.map((scenario) => (
              <TableRow 
                key={scenario.id} 
                hover 
                onClick={() => navigate(`/scenarios/${scenario.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>{scenario.name}</TableCell>
                <TableCell>{scenario.current_age}</TableCell>
                <TableCell>{scenario.retirement_age}</TableCell>
                <TableCell>{new Date(scenario.created_at).toLocaleDateString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Scenario</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField fullWidth label="Name" name="name" value={newScenario.name} onChange={handleChange} required />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth label="Description" name="description" multiline rows={2} value={newScenario.description || ''} onChange={handleChange} />
            </Grid>
            <Grid item xs={4}>
              <TextField fullWidth type="number" label="Current Age" name="current_age" value={newScenario.current_age} onChange={handleChange} />
            </Grid>
            <Grid item xs={4}>
              <TextField fullWidth type="number" label="Retirement Age" name="retirement_age" value={newScenario.retirement_age} onChange={handleChange} />
            </Grid>
            <Grid item xs={4}>
              <TextField fullWidth type="number" label="End Age" name="end_age" value={newScenario.end_age} onChange={handleChange} />
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth type="number" label="Inflation Rate (0.03 = 3%)" name="inflation_rate" value={newScenario.inflation_rate} onChange={handleChange} inputProps={{ step: 0.001 }} />
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth type="number" label="Bond Return Rate (0.04 = 4%)" name="bond_return_rate" value={newScenario.bond_return_rate} onChange={handleChange} inputProps={{ step: 0.001 }} />
            </Grid>
            <Grid item xs={6}>
              <NumericFormat
                customInput={TextField}
                fullWidth
                label="Annual Contribution (Pre)"
                value={newScenario.annual_contribution_pre_retirement}
                onValueChange={(values) => {
                  const { floatValue } = values;
                  setNewScenario(prev => ({
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
                value={newScenario.annual_spending_in_retirement}
                onValueChange={(values) => {
                  const { floatValue } = values;
                  setNewScenario(prev => ({
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
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default ScenarioList;
