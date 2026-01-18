import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormControlLabel,
  InputLabel,
  Radio,
  RadioGroup,
  Select,
  MenuItem,
  TextField,
  Typography,
  Alert
} from '@mui/material';
import { getTaxFundingSettings, updateTaxFundingSettings } from '../api/client';
import { TaxFundingSettingsCreate, TaxTableIndexingPolicy as TaxTableIndexingPolicyType } from '../types';
import { NumericFormat } from 'react-number-format';
import CalculatorInput from './CalculatorInput';

interface TaxTableIndexingPolicyProps {
  scenarioId: number;
  onBack: () => void;
  onClose: () => void;
}

const TaxTableIndexingPolicy: React.FC<TaxTableIndexingPolicyProps> = ({ scenarioId, onBack, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [policy, setPolicy] = useState<TaxTableIndexingPolicyType>("CONSTANT_NOMINAL");
  const [customRate, setCustomRate] = useState<number | "">("");

  useEffect(() => {
    loadSettings();
  }, [scenarioId]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const settings = await getTaxFundingSettings(scenarioId);
      setPolicy(settings.tax_table_indexing_policy);
      setCustomRate(settings.tax_table_custom_index_rate !== null ? settings.tax_table_custom_index_rate * 100 : "");
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

      // Validate custom rate if needed
      if (policy === "CUSTOM_RATE") {
        if (customRate === "" || isNaN(Number(customRate))) {
          setError("Custom rate is required when using custom rate policy");
          return;
        }
        const rate = Number(customRate);
        if (rate < -5 || rate > 15) {
          setError("Custom rate must be between -5% and 15%");
          return;
        }
      }

      // Get current settings to preserve other fields
      const currentSettings = await getTaxFundingSettings(scenarioId);
      
      const payload: TaxFundingSettingsCreate = {
        ...currentSettings,
        tax_table_indexing_policy: policy,
        tax_table_custom_index_rate: policy === "CUSTOM_RATE" && customRate !== "" ? Number(customRate) / 100 : null
      };

      await updateTaxFundingSettings(scenarioId, payload);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      
      <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary' }}>
        Configure how tax table thresholds and standard deductions adjust over time in projections. 
        Tax rates remain constant regardless of indexing policy.
      </Typography>

      <FormControl component="fieldset" fullWidth>
        <RadioGroup
          value={policy}
          onChange={(e) => {
            setPolicy(e.target.value as TaxTableIndexingPolicyType);
            if (e.target.value !== "CUSTOM_RATE") {
              setCustomRate("");
            }
          }}
        >
          <FormControlLabel
            value="CONSTANT_NOMINAL"
            control={<Radio />}
            label="Keep constant (nominal) - Thresholds and deductions remain at base year values"
          />
          <FormControlLabel
            value="SCENARIO_INFLATION"
            control={<Radio />}
            label="Index to scenario inflation rate - Thresholds and deductions adjust with scenario's inflation rate"
          />
          <FormControlLabel
            value="CUSTOM_RATE"
            control={<Radio />}
            label="Custom rate - Specify your own annual adjustment rate"
          />
        </RadioGroup>
      </FormControl>

      {policy === "CUSTOM_RATE" && (
        <Box sx={{ mt: 3 }}>
          <NumericFormat
            customInput={CalculatorInput}
            fullWidth
            label="Custom Index Rate (%)"
            value={customRate === "" ? "" : customRate}
            onValueChange={(values) => {
              const { floatValue } = values;
              if (floatValue === undefined) {
                setCustomRate("");
              } else {
                setCustomRate(floatValue);
              }
            }}
            suffix="%"
            decimalScale={2}
            allowNegative={true}
            helperText="Enter annual adjustment rate between -5% and 15%"
          />
        </Box>
      )}

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Button onClick={onBack}>Back</Button>
        <Button variant="contained" onClick={handleSave} disabled={loading || saving}>
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </Box>
    </Box>
  );
};

export default TaxTableIndexingPolicy;

