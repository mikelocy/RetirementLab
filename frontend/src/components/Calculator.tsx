import React, { useState, useEffect } from 'react';
import { Box, Button, Grid, Typography, IconButton } from '@mui/material';
import BackspaceIcon from '@mui/icons-material/Backspace';

interface CalculatorProps {
  initialValue: string | number;
  onClose: () => void;
  onApply: (value: number) => void;
}

const Calculator: React.FC<CalculatorProps> = ({ initialValue, onClose, onApply }) => {
  const [display, setDisplay] = useState(String(initialValue || '0'));
  const [expression, setExpression] = useState('');
  const [isResult, setIsResult] = useState(false);

  useEffect(() => {
    // Sanitize initial value: remove everything except digits, decimal point, and minus sign
    const sanitized = String(initialValue || '0').replace(/[^0-9.-]/g, '');
    setDisplay(sanitized || '0');
    setExpression('');
    setIsResult(false);
  }, [initialValue]);

  const handleNumber = (num: string) => {
    if (isResult) {
      setDisplay(num);
      setIsResult(false);
    } else {
      setDisplay(display === '0' ? num : display + num);
    }
  };

  const handleOperator = (op: string) => {
    setExpression(display + ' ' + op + ' ');
    setIsResult(false);
    setDisplay('0');
  };

  const handleClear = () => {
    setDisplay('0');
    setExpression('');
    setIsResult(false);
  };

  const handleBackspace = () => {
    if (isResult) {
      handleClear();
    } else {
      setDisplay(display.length > 1 ? display.slice(0, -1) : '0');
    }
  };

  const handleEqual = () => {
    try {
      // Basic safety check: only allow numbers and operators
      const fullExpr = expression + display;
      if (!/^[\d\.\+\-\*\/ \(\)]+$/.test(fullExpr)) {
        setDisplay('Error');
        return;
      }
      
      // eslint-disable-next-line no-eval
      const result = eval(fullExpr);
      
      if (!isFinite(result) || isNaN(result)) {
        setDisplay('Error');
      } else {
        // limit decimals to avoid floating point issues
        const formatted = Math.round(result * 1000000) / 1000000;
        setDisplay(String(formatted));
        setExpression('');
        setIsResult(true);
      }
    } catch (e) {
      setDisplay('Error');
    }
  };

  const handleApply = () => {
    let valueToApply = Number(display);
    if (isNaN(valueToApply)) {
        // Try to evaluate if user forgot to press =
        if (expression) {
             try {
                const fullExpr = expression + display;
                 // eslint-disable-next-line no-eval
                const result = eval(fullExpr);
                if (isFinite(result) && !isNaN(result)) {
                    valueToApply = result;
                } else {
                    return; // Don't apply error
                }
             } catch {
                 return;
             }
        } else {
            return;
        }
    }
    onApply(valueToApply);
    onClose();
  };

  const btnStyle = { minWidth: '40px', height: '40px', p: 0, fontSize: '1.1rem' };

  return (
    <Box sx={{ p: 2, width: 240, bgcolor: 'background.paper', borderRadius: 1 }}>
      <Box sx={{ mb: 1, textAlign: 'right', minHeight: '1.5em' }}>
        <Typography variant="caption" color="text.secondary">{expression}</Typography>
      </Box>
      <Box sx={{ mb: 2, p: 1, border: '1px solid #ccc', borderRadius: 1, textAlign: 'right', bgcolor: '#f5f5f5' }}>
        <Typography variant="h5">{display}</Typography>
      </Box>

      <Grid container spacing={1}>
        <Grid item xs={3}><Button variant="outlined" fullWidth color="error" onClick={handleClear} sx={btnStyle}>C</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleOperator('/')} sx={btnStyle}>/</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleOperator('*')} sx={btnStyle}>*</Button></Grid>
        <Grid item xs={3}>
            <Button variant="outlined" fullWidth color="warning" onClick={handleBackspace} sx={btnStyle}>
                <BackspaceIcon fontSize="small" />
            </Button>
        </Grid>

        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('7')} sx={btnStyle}>7</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('8')} sx={btnStyle}>8</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('9')} sx={btnStyle}>9</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleOperator('-')} sx={btnStyle}>-</Button></Grid>

        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('4')} sx={btnStyle}>4</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('5')} sx={btnStyle}>5</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('6')} sx={btnStyle}>6</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleOperator('+')} sx={btnStyle}>+</Button></Grid>

        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('1')} sx={btnStyle}>1</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('2')} sx={btnStyle}>2</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('3')} sx={btnStyle}>3</Button></Grid>
        <Grid item xs={3}><Button variant="contained" fullWidth onClick={handleEqual} sx={btnStyle}>=</Button></Grid>

        <Grid item xs={6}><Button variant="outlined" fullWidth onClick={() => handleNumber('0')} sx={btnStyle}>0</Button></Grid>
        <Grid item xs={3}><Button variant="outlined" fullWidth onClick={() => handleNumber('.')} sx={btnStyle}>.</Button></Grid>
        <Grid item xs={3}></Grid> {/* Spacer */}
        
        <Grid item xs={12}>
            <Button variant="contained" fullWidth color="primary" onClick={handleApply} sx={{ mt: 1 }}>
                Use Result
            </Button>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Calculator;
