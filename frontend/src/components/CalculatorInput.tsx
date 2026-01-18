import React, { useState } from 'react';
import { TextField, TextFieldProps, InputAdornment, IconButton, Popover } from '@mui/material';
import CalculateIcon from '@mui/icons-material/Calculate';
import Calculator from './Calculator';

type CalculatorInputProps = TextFieldProps & {
  // Add any specific props if needed, but mostly we just pass through to TextField
};

const CalculatorInput: React.FC<CalculatorInputProps> = (props) => {
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleApply = (value: number) => {
    // We need to trigger the onChange event for the parent component
    if (props.onChange) {
      const event = {
        target: {
          value: String(value),
          name: props.name,
        }
      } as React.ChangeEvent<HTMLInputElement>;
      props.onChange(event);
    }
    // Also support onValueChange for NumberFormat compatibility if passed directly (though usually handled by NumericFormat wrapper)
    // If this component is used as customInput for NumericFormat, NumericFormat handles the onChange.
    // However, we need to pass the raw value up.
    
    // If used directly as a TextField replacement:
    // The props.onChange expects an event.
  };

  const open = Boolean(anchorEl);
  const id = open ? 'calculator-popover' : undefined;

  // We want to force type="text" to remove spinners, but allow "number" behavior logic if needed.
  // Actually, keeping type="text" allows us to have full control and no spinners.
  // But props might pass type="number". Let's override it to "text" effectively for UI,
  // or use CSS to hide spinners if we keep type="number".
  // Using type="text" is safer for "No spinners".
  
  const inputProps = {
    ...props.InputProps,
    endAdornment: (
      <InputAdornment position="end">
        <IconButton
          aria-describedby={id}
          onClick={handleClick}
          edge="end"
          size="small"
          tabIndex={-1} // Skip tab index so tabbing through form doesn't get stuck on calc button
        >
          <CalculateIcon fontSize="small" />
        </IconButton>
        {props.InputProps?.endAdornment}
      </InputAdornment>
    ),
  };

  return (
    <>
      <TextField
        {...props}
        type="text" // Force text to remove browser spinners
        InputProps={inputProps}
        // If the parent passed numeric specific props that might cause issues with type="text", we might need to filter them, but TextField is robust.
      />
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <Calculator
          initialValue={props.value as string | number}
          onClose={handleClose}
          onApply={handleApply}
        />
      </Popover>
    </>
  );
};

export default CalculatorInput;
