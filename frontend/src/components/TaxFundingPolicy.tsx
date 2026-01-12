import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  Typography,
  Alert
} from '@mui/material';
import { getTaxFundingSettings, updateTaxFundingSettings } from '../api/client';
import { TaxFundingSettings, TaxFundingSettingsCreate, TaxFundingSource, InsufficientFundsBehavior } from '../types';

interface TaxFundingPolicyProps {
  scenarioId: number;
  onBack: () => void;
  onClose: () => void;
}

const TaxFundingPolicy: React.FC<TaxFundingPolicyProps> = ({ scenarioId, onBack, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [taxFundingOrder, setTaxFundingOrder] = useState<[TaxFundingSource | "", TaxFundingSource | "", TaxFundingSource | "", TaxFundingSource | ""]>(["CASH", "TAXABLE_BROKERAGE", "TRADITIONAL_RETIREMENT", "ROTH"]);
  const [allowRetirementWithdrawals, setAllowRetirementWithdrawals] = useState(true);
  const [insufficientFundsBehavior, setInsufficientFundsBehavior] = useState<InsufficientFundsBehavior>("FAIL_WITH_SHORTFALL");

  useEffect(() => {
    loadSettings();
  }, [scenarioId]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const settings = await getTaxFundingSettings(scenarioId);
      setTaxFundingOrder([
        settings.tax_funding_order[0] || "",
        settings.tax_funding_order[1] || "",
        settings.tax_funding_order[2] || "",
        settings.tax_funding_order[3] || ""
      ]);
      setAllowRetirementWithdrawals(settings.allow_retirement_withdrawals_for_taxes);
      setInsufficientFundsBehavior(settings.if_insufficient_funds_behavior);
    } catch (err: any) {
      setError(err.message || "Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      
      // Validate
      const order = taxFundingOrder.filter(s => s !== "") as TaxFundingSource[];
      if (order.length === 0) {
        setError("At least one funding source is required");
        return;
      }
      if (new Set(order).size !== order.length) {
        setError("Funding sources must be unique");
        return;
      }

      // Get current settings to preserve indexing policy
      const currentSettings = await getTaxFundingSettings(scenarioId);
      
      const payload: TaxFundingSettingsCreate = {
        tax_funding_order: order,
        allow_retirement_withdrawals_for_taxes: allowRetirementWithdrawals,
        if_insufficient_funds_behavior: insufficientFundsBehavior,
        tax_table_indexing_policy: currentSettings.tax_table_indexing_policy,
        tax_table_custom_index_rate: currentSettings.tax_table_custom_index_rate
      };

      await updateTaxFundingSettings(scenarioId, payload);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const availableSources: TaxFundingSource[] = ["CASH", "TAXABLE_BROKERAGE", "TRADITIONAL_RETIREMENT", "ROTH"];

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      
      <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary' }}>
        Configure the order in which assets are used to pay taxes. The system will attempt to use sources in the order specified below.
      </Typography>

      <Grid container spacing={2}>
        {[0, 1, 2, 3].map((index) => (
          <Grid item xs={12} sm={6} key={index}>
            <FormControl fullWidth>
              <InputLabel>{index === 0 ? "1st Priority" : index === 1 ? "2nd Priority" : index === 2 ? "3rd Priority" : "4th Priority"}</InputLabel>
              <Select
                value={taxFundingOrder[index] || ""}
                label={index === 0 ? "1st Priority" : index === 1 ? "2nd Priority" : index === 2 ? "3rd Priority" : "4th Priority"}
                onChange={(e) => {
                  const newOrder = [...taxFundingOrder] as [TaxFundingSource | "", TaxFundingSource | "", TaxFundingSource | "", TaxFundingSource | ""];
                  newOrder[index] = e.target.value as TaxFundingSource | "";
                  setTaxFundingOrder(newOrder);
                }}
              >
                <MenuItem value="">None</MenuItem>
                {availableSources
                  .filter(source => !taxFundingOrder.includes(source) || taxFundingOrder[index] === source)
                  .map(source => (
                    <MenuItem key={source} value={source}>
                      {source.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
          </Grid>
        ))}
      </Grid>

      <Box sx={{ mt: 3 }}>
        <FormControlLabel
          control={
            <Checkbox
              checked={allowRetirementWithdrawals}
              onChange={(e) => setAllowRetirementWithdrawals(e.target.checked)}
            />
          }
          label="Allow withdrawals from retirement accounts (Traditional IRA, 401k, Roth) to pay taxes"
        />
      </Box>

      <Box sx={{ mt: 2 }}>
        <FormControl fullWidth>
          <InputLabel>If Insufficient Funds</InputLabel>
          <Select
            value={insufficientFundsBehavior}
            label="If Insufficient Funds"
            onChange={(e) => setInsufficientFundsBehavior(e.target.value as InsufficientFundsBehavior)}
          >
            <MenuItem value="FAIL_WITH_SHORTFALL">Record tax shortfall and mark scenario as infeasible</MenuItem>
            <MenuItem value="LIQUIDATE_ALL_AVAILABLE">Liquidate all available assets</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Button onClick={onBack}>Back</Button>
        <Button variant="contained" onClick={handleSave} disabled={loading || saving}>
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </Box>
    </Box>
  );
};

export default TaxFundingPolicy;

