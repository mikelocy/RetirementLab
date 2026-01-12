import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Typography,
  Alert,
  Tabs,
  Tab,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { getTaxTables, upsertTaxTable } from '../api/client';
import { TaxTable, TaxTableCreate, TaxBracket, FilingStatus } from '../types';
import { NumericFormat } from 'react-number-format';
import { getScenario } from '../api/client';

interface TaxTablesEditorProps {
  scenarioId: number;
  onBack: () => void;
  onClose: () => void;
}

const TaxTablesEditor: React.FC<TaxTablesEditorProps> = ({ scenarioId, onBack, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<0 | 1>(0);
  const [filingStatus, setFilingStatus] = useState<FilingStatus>("married_filing_jointly");
  const [yearBase, setYearBase] = useState<number>(new Date().getFullYear());
  
  const [fedTable, setFedTable] = useState<TaxTable | null>(null);
  const [caTable, setCaTable] = useState<TaxTable | null>(null);
  
  const [fedStandardDeduction, setFedStandardDeduction] = useState<number | "">("");
  const [fedBrackets, setFedBrackets] = useState<TaxBracket[]>([]);
  
  const [caStandardDeduction, setCaStandardDeduction] = useState<number | "">("");
  const [caBrackets, setCaBrackets] = useState<TaxBracket[]>([]);

  useEffect(() => {
    loadData();
  }, [scenarioId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [scenario, tables] = await Promise.all([
        getScenario(scenarioId),
        getTaxTables(scenarioId)
      ]);
      
      // Debug logging
      console.log('[DEBUG] TaxTablesEditor: Loaded scenario:', scenario);
      console.log('[DEBUG] TaxTablesEditor: Loaded tax tables:', tables);
      console.log('[DEBUG] TaxTablesEditor: Filing status:', scenario.filing_status);
      
      setFilingStatus(scenario.filing_status);
      setYearBase(scenario.base_year || new Date().getFullYear());
      
      const fed = tables.find(t => t.jurisdiction === "FED" && t.filing_status === scenario.filing_status);
      const ca = tables.find(t => t.jurisdiction === "CA" && t.filing_status === scenario.filing_status);
      
      console.log('[DEBUG] TaxTablesEditor: Found FED table:', fed);
      console.log('[DEBUG] TaxTablesEditor: Found CA table:', ca);
      
      setWarning(null);
      setError(null);

      if (!fed && !ca) {
        setWarning("No tax tables found for this year. Default tables have been initialized, but you may want to verify them.");
      }
      
      if (fed) {
        setFedTable(fed);
        setFedStandardDeduction(fed.standard_deduction);
        // Convert null/undefined up_to to Infinity for frontend handling
        setFedBrackets(fed.brackets.map(b => ({
          ...b,
          up_to: (b.up_to === null || b.up_to === undefined) ? Infinity : b.up_to
        })));
      } else {
        // Initialize with empty brackets
        console.warn('[DEBUG] TaxTablesEditor: No FED table found, initializing empty');
        setFedBrackets([{ up_to: 0, rate: 0 }]);
      }
      
      if (ca) {
        setCaTable(ca);
        setCaStandardDeduction(ca.standard_deduction);
        // Convert null/undefined up_to to Infinity for frontend handling
        setCaBrackets(ca.brackets.map(b => ({
          ...b,
          up_to: (b.up_to === null || b.up_to === undefined) ? Infinity : b.up_to
        })));
      } else {
        // Initialize with empty brackets
        console.warn('[DEBUG] TaxTablesEditor: No CA table found, initializing empty');
        setCaBrackets([{ up_to: 0, rate: 0 }]);
      }
    } catch (err: any) {
      console.error('[ERROR] TaxTablesEditor: Failed to load:', err);
      setError(err.message || "Failed to load tax tables");
    } finally {
      setLoading(false);
    }
  };

  const validateBrackets = (brackets: TaxBracket[]): string | null => {
    if (brackets.length === 0) {
      return "At least one bracket is required";
    }
    
    let prevUpTo = -1;
    for (let i = 0; i < brackets.length; i++) {
      const bracket = brackets[i];
      
      if (bracket.up_to <= prevUpTo && bracket.up_to !== Infinity) {
        return `Bracket ${i + 1}: Threshold must be greater than previous threshold`;
      }
      
      if (bracket.rate < 0 || bracket.rate > 1) {
        return `Bracket ${i + 1}: Rate must be between 0 and 1 (0% to 100%)`;
      }
      
      prevUpTo = bracket.up_to;
    }
    
    return null;
  };

  const handleSave = async (jurisdiction: "FED" | "CA") => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      const brackets = jurisdiction === "FED" ? fedBrackets : caBrackets;
      const standardDeduction = jurisdiction === "FED" ? fedStandardDeduction : caStandardDeduction;
      
      // Validate
      const bracketError = validateBrackets(brackets);
      if (bracketError) {
        setError(bracketError);
        return;
      }
      
      if (standardDeduction === "" || isNaN(Number(standardDeduction)) || Number(standardDeduction) < 0) {
        setError("Standard deduction must be a non-negative number");
        return;
      }
      
      // Convert rates from percentage to decimal if needed (assuming they're already in decimal form from backend)
      const payload: TaxTableCreate = {
        jurisdiction,
        filing_status: filingStatus,
        year_base: yearBase,
        brackets: brackets.map(b => ({
          up_to: b.up_to === Infinity ? Infinity : b.up_to,
          rate: b.rate
        })),
        standard_deduction: Number(standardDeduction),
        notes: null
      };
      
      await upsertTaxTable(scenarioId, jurisdiction, payload);
      setSuccess(`${jurisdiction === "FED" ? "Federal" : "California"} tax table saved successfully`);
      
      // Reload to get updated data
      await loadData();
    } catch (err: any) {
      setError(err.message || `Failed to save ${jurisdiction === "FED" ? "federal" : "California"} tax table`);
    } finally {
      setSaving(false);
    }
  };

  const addBracket = (jurisdiction: "FED" | "CA") => {
    const brackets = jurisdiction === "FED" ? fedBrackets : caBrackets;
    const setBrackets = jurisdiction === "FED" ? setFedBrackets : setCaBrackets;
    
    const lastBracket = brackets[brackets.length - 1];
    const newUpTo = lastBracket?.up_to === Infinity ? 1000000 : (lastBracket?.up_to || 0) + 10000;
    
    setBrackets([...brackets, { up_to: newUpTo, rate: 0.25 }]);
  };

  const removeBracket = (jurisdiction: "FED" | "CA", index: number) => {
    const brackets = jurisdiction === "FED" ? fedBrackets : caBrackets;
    const setBrackets = jurisdiction === "FED" ? setFedBrackets : setCaBrackets;
    
    if (brackets.length <= 1) {
      setError("At least one bracket is required");
      return;
    }
    
    const newBrackets = brackets.filter((_, i) => i !== index);
    setBrackets(newBrackets);
  };

  const updateBracket = (jurisdiction: "FED" | "CA", index: number, field: "up_to" | "rate", value: number) => {
    const brackets = jurisdiction === "FED" ? fedBrackets : caBrackets;
    const setBrackets = jurisdiction === "FED" ? setFedBrackets : setCaBrackets;
    
    const newBrackets = [...brackets];
    newBrackets[index] = { ...newBrackets[index], [field]: value };
    setBrackets(newBrackets);
  };

  const renderTableEditor = (jurisdiction: "FED" | "CA") => {
    const brackets = jurisdiction === "FED" ? fedBrackets : caBrackets;
    const standardDeduction = jurisdiction === "FED" ? fedStandardDeduction : caStandardDeduction;
    const setStandardDeduction = jurisdiction === "FED" ? setFedStandardDeduction : setCaStandardDeduction;
    
    return (
      <Box>
        <Box sx={{ mb: 3 }}>
          <NumericFormat
            customInput={TextField}
            fullWidth
            label="Standard Deduction"
            value={standardDeduction === "" ? "" : standardDeduction}
            onValueChange={(values) => {
              const { floatValue } = values;
              if (floatValue === undefined) {
                setStandardDeduction("");
              } else {
                setStandardDeduction(floatValue);
              }
            }}
            thousandSeparator=","
            prefix="$"
            decimalScale={0}
            allowNegative={false}
          />
        </Box>
        
        <Typography variant="h6" sx={{ mb: 2 }}>Tax Brackets</Typography>
        
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Up To ($)</TableCell>
                <TableCell>Rate (%)</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {brackets.map((bracket, index) => (
                <TableRow key={index}>
                  <TableCell>
                    {bracket.up_to === Infinity ? (
                      <Typography variant="body2" color="text.secondary">∞ (No limit)</Typography>
                    ) : (
                      <NumericFormat
                        customInput={TextField}
                        size="small"
                        fullWidth
                        value={bracket.up_to}
                        onValueChange={(values) => {
                          const { floatValue } = values;
                          if (floatValue !== undefined) {
                            updateBracket(jurisdiction, index, "up_to", floatValue);
                          }
                        }}
                        thousandSeparator=","
                        prefix="$"
                        decimalScale={0}
                        allowNegative={false}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <NumericFormat
                      customInput={TextField}
                      size="small"
                      fullWidth
                      value={bracket.rate * 100}
                      onValueChange={(values) => {
                        const { floatValue } = values;
                        if (floatValue !== undefined) {
                          updateBracket(jurisdiction, index, "rate", floatValue / 100);
                        }
                      }}
                      suffix="%"
                      decimalScale={2}
                      allowNegative={false}
                    />
                  </TableCell>
                  <TableCell align="right">
                    {index === brackets.length - 1 && bracket.up_to !== Infinity ? (
                      <IconButton
                        size="small"
                        onClick={() => {
                          const newBrackets = [...brackets];
                          newBrackets[index] = { ...newBrackets[index], up_to: Infinity };
                          jurisdiction === "FED" ? setFedBrackets(newBrackets) : setCaBrackets(newBrackets);
                        }}
                        title="Set as top bracket (no limit)"
                      >
                        <Typography variant="caption">∞</Typography>
                      </IconButton>
                    ) : null}
                    <IconButton
                      size="small"
                      onClick={() => removeBracket(jurisdiction, index)}
                      disabled={brackets.length <= 1}
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        
        <Box sx={{ mt: 2 }}>
          <Button
            startIcon={<AddIcon />}
            onClick={() => addBracket(jurisdiction)}
            variant="outlined"
            size="small"
          >
            Add Bracket
          </Button>
        </Box>
        
        <Box sx={{ mt: 3 }}>
          <Button
            variant="contained"
            onClick={() => handleSave(jurisdiction)}
            disabled={saving || loading}
          >
            {saving ? 'Saving...' : `Save ${jurisdiction === "FED" ? "Federal" : "California"} Table`}
          </Button>
        </Box>
      </Box>
    );
  };

  if (loading) {
    return <Box>Loading...</Box>;
  }

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {warning && <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setWarning(null)}>{warning}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}
      
      <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
        Filing Status: {filingStatus.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} | Base Year: {yearBase}
      </Typography>
      
      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 3 }}>
        <Tab label="Federal" />
        <Tab label="California" />
      </Tabs>
      
      {activeTab === 0 && renderTableEditor("FED")}
      {activeTab === 1 && renderTableEditor("CA")}
      
      <Box sx={{ mt: 3 }}>
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="body2" color="text.secondary">
              Debug: View Raw JSON
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="caption" component="pre" sx={{ fontSize: '0.75rem', overflow: 'auto' }}>
              {JSON.stringify({ fedTable, caTable, filingStatus, yearBase }, null, 2)}
            </Typography>
          </AccordionDetails>
        </Accordion>
      </Box>
      
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Button onClick={onBack}>Back</Button>
        <Button onClick={onClose}>Close</Button>
      </Box>
    </Box>
  );
};

export default TaxTablesEditor;

