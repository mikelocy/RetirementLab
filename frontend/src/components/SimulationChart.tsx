import React from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { Typography, Box } from '@mui/material';
import { SimpleBondSimulationResult } from '../types';

interface SimulationChartProps {
  data: SimpleBondSimulationResult | null;
  fixedWidth?: number | null;
}

const SimulationChart: React.FC<SimulationChartProps> = ({ data, fixedWidth }) => {
  if (!data) {
    return (
      <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#f5f5f5', borderRadius: 1 }}>
        <Typography color="textSecondary">Run the simulation to see results.</Typography>
      </Box>
    );
  }

  const chartData = data.ages.map((age, index) => ({
    age,
    balance_nominal: Math.max(0, data.balance_nominal[index]),
    balance_real: Math.max(0, data.balance_real[index]),
    // Store original values for tooltip
    balance_nominal_original: data.balance_nominal[index],
    balance_real_original: data.balance_real[index],
  }));

  // Calculate max value for Y-axis domain
  const maxValue = Math.max(
    ...data.balance_nominal.map(v => Math.max(0, v)),
    ...data.balance_real.map(v => Math.max(0, v))
  );

  // Use fixed width if provided, otherwise use 100%
  const chartWidth = fixedWidth || '100%';

  // If using fixed width (passed from parent calculation), we want to align with the table.
  // The table has a 250px sticky left column.
  // We set the chart's left margin to match this so the X-axis starts after the category column.
  // We also align the points to the center of the table columns (width 120px) using padding.
  const leftMargin = fixedWidth ? 250 : 20;
  const rightMargin = fixedWidth ? 0 : 30;
  const xAxisPadding = fixedWidth ? { left: 60, right: 60 } : { left: 10, right: 10 };

  return (
    <ResponsiveContainer width={chartWidth} height={400}>
      <LineChart data={chartData} margin={{ top: 20, right: rightMargin, left: leftMargin, bottom: 10 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="age" 
          label={{ value: 'Age', position: 'insideBottomRight', offset: -5 }} 
          interval={0}
          tick={{ fontSize: 12 }}
          padding={xAxisPadding}
        />
        <YAxis 
          domain={[0, maxValue * 1.1]}
          tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
        />
        <Tooltip 
          formatter={(value: number, name: string, props: any) => {
            // Use original values for tooltip if available
            const originalValue = name === 'Nominal Balance' 
              ? props.payload.balance_nominal_original 
              : props.payload.balance_real_original;
            return [`$${originalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, ''];
          }}
          labelFormatter={(label) => `Age ${label}`}
        />
        <Legend verticalAlign="top" height={36}/>
        <Line 
          type="monotone" 
          dataKey="balance_nominal" 
          name="Nominal Balance" 
          stroke="#8884d8" 
          strokeWidth={2}
          dot={false}
        />
        <Line 
          type="monotone" 
          dataKey="balance_real" 
          name="Real Balance (Inflation Adjusted)" 
          stroke="#82ca9d" 
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default SimulationChart;
