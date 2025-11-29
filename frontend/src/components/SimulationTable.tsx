import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box
} from '@mui/material';
import { SimpleBondSimulationResult } from '../types';

interface SimulationTableProps {
  data: SimpleBondSimulationResult | null;
  fixedWidth?: number | null;
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const SimulationTable: React.FC<SimulationTableProps> = ({ data, fixedWidth }) => {
  if (!data || !data.ages || data.ages.length === 0) {
    return null;
  }

  const numYears = data.ages.length;
  const assetIds = Object.keys(data.asset_values).map(Number);
  const debtIds = Object.keys(data.debt_values).map(Number);

  // Calculate totals for each year
  const totalAssets = data.ages.map((_, yearIndex) => {
    return assetIds.reduce((sum, assetId) => {
      return sum + (data.asset_values[assetId]?.[yearIndex] || 0);
    }, 0);
  });

  const totalDebts = data.ages.map((_, yearIndex) => {
    return debtIds.reduce((sum, debtId) => {
      return sum + (data.debt_values[debtId]?.[yearIndex] || 0);
    }, 0);
  });

  const netWorth = data.ages.map((_, yearIndex) => {
    return totalAssets[yearIndex] - totalDebts[yearIndex];
  });

  const totalIncome = data.ages.map((_, yearIndex) => {
    const salary = data.income_sources.salary[yearIndex] || 0;
    const rental = Object.values(data.income_sources.rental_income).reduce((sum, rentalArray) => {
      return sum + (rentalArray[yearIndex] || 0);
    }, 0);
    const specific = Object.values(data.income_sources.specific_income || {}).reduce((sum, arr) => {
      return sum + (arr[yearIndex] || 0);
    }, 0);
    return salary + rental + specific;
  });

  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" gutterBottom>
        Detailed Breakdown by Year
      </Typography>
      <TableContainer 
        component={Paper} 
        sx={{ 
          maxHeight: 600, 
          // Disable internal horizontal scroll if fixedWidth is provided, 
          // relying on parent container for scrolling
          overflowX: fixedWidth ? 'visible' : 'auto',
          width: '100%'
        }}
      >
        <Table 
          stickyHeader 
          size="small"
          sx={{ 
            width: fixedWidth || '100%',
            minWidth: fixedWidth || '100%'
          }}
        >
          <TableHead>
            <TableRow>
              <TableCell sx={{ position: 'sticky', left: 0, backgroundColor: 'white', zIndex: 3, fontWeight: 'bold', width: 250, minWidth: 250 }}>
                Category
              </TableCell>
              {data.ages.map((age) => (
                <TableCell key={age} align="right" sx={{ minWidth: 120 }}>
                  Age {age}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {/* Assets Section */}
            <TableRow>
              <TableCell colSpan={numYears + 1} sx={{ backgroundColor: '#f5f5f5', fontWeight: 'bold' }}>
                ASSETS
              </TableCell>
            </TableRow>
            {assetIds.map((assetId) => (
              <TableRow key={`asset-${assetId}`}>
                <TableCell sx={{ pl: 4, position: 'sticky', left: 0, backgroundColor: 'white', zIndex: 2, whiteSpace: 'nowrap' }}>
                  {data.asset_names[assetId]}
                </TableCell>
                {data.ages.map((_, yearIndex) => (
                  <TableCell key={yearIndex} align="right">
                    {formatCurrency(data.asset_values[assetId]?.[yearIndex] || 0)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
            <TableRow>
              <TableCell sx={{ pl: 2, fontWeight: 'bold', position: 'sticky', left: 0, backgroundColor: '#e3f2fd', zIndex: 2, whiteSpace: 'nowrap' }}>
                Total Assets
              </TableCell>
              {totalAssets.map((value, yearIndex) => (
                <TableCell key={yearIndex} align="right" sx={{ fontWeight: 'bold', backgroundColor: '#e3f2fd' }}>
                  {formatCurrency(value)}
                </TableCell>
              ))}
            </TableRow>

            {/* Debts Section */}
            {debtIds.length > 0 && (
              <>
                <TableRow>
                  <TableCell colSpan={numYears + 1} sx={{ backgroundColor: '#f5f5f5', fontWeight: 'bold' }}>
                    DEBTS
                  </TableCell>
                </TableRow>
                {debtIds.map((debtId) => (
                  <TableRow key={`debt-${debtId}`}>
                    <TableCell sx={{ pl: 4, position: 'sticky', left: 0, backgroundColor: 'white', zIndex: 2, whiteSpace: 'nowrap' }}>
                      {data.debt_names[debtId]}
                    </TableCell>
                    {data.ages.map((_, yearIndex) => (
                      <TableCell key={yearIndex} align="right">
                        {formatCurrency(data.debt_values[debtId]?.[yearIndex] || 0)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell sx={{ pl: 2, fontWeight: 'bold', position: 'sticky', left: 0, backgroundColor: '#ffebee', zIndex: 2, whiteSpace: 'nowrap' }}>
                    Total Debts
                  </TableCell>
                  {totalDebts.map((value, yearIndex) => (
                    <TableCell key={yearIndex} align="right" sx={{ fontWeight: 'bold', backgroundColor: '#ffebee' }}>
                      {formatCurrency(value)}
                    </TableCell>
                  ))}
                </TableRow>
              </>
            )}

            {/* Net Worth */}
            <TableRow>
              <TableCell colSpan={numYears + 1} sx={{ backgroundColor: '#f5f5f5', fontWeight: 'bold' }}>
                NET WORTH
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 2, fontWeight: 'bold', position: 'sticky', left: 0, backgroundColor: '#e8f5e9', zIndex: 2, whiteSpace: 'nowrap' }}>
                Net Worth
              </TableCell>
              {netWorth.map((value, yearIndex) => (
                <TableCell key={yearIndex} align="right" sx={{ fontWeight: 'bold', backgroundColor: '#e8f5e9' }}>
                  {formatCurrency(value)}
                </TableCell>
              ))}
            </TableRow>

            {/* Income Section */}
            <TableRow>
              <TableCell colSpan={numYears + 1} sx={{ backgroundColor: '#f5f5f5', fontWeight: 'bold' }}>
                INCOME
              </TableCell>
            </TableRow>
            {data.income_sources.salary.some(v => v > 0) && (
            <TableRow>
              <TableCell sx={{ pl: 4, position: 'sticky', left: 0, backgroundColor: 'white', zIndex: 2, whiteSpace: 'nowrap' }}>
                Salary
              </TableCell>
              {data.ages.map((_, yearIndex) => (
                <TableCell key={yearIndex} align="right">
                  {formatCurrency(data.income_sources.salary[yearIndex] || 0)}
                </TableCell>
              ))}
            </TableRow>
            )}
            {/* Specific Income Sources */}
            {data.income_sources.specific_income && Object.keys(data.income_sources.specific_income).map((sourceIdStr) => {
              const sourceId = Number(sourceIdStr);
              const values = data.income_sources.specific_income[sourceId] || [];
              if (values.every(v => v === 0)) return null;

              const sourceName = data.income_names ? data.income_names[sourceId] : `Income Source ${sourceId}`;
              return (
                <TableRow key={`income-${sourceId}`}>
                  <TableCell sx={{ pl: 4, position: 'sticky', left: 0, backgroundColor: 'white', zIndex: 2, whiteSpace: 'nowrap' }}>
                    {sourceName}
                  </TableCell>
                  {data.ages.map((_, yearIndex) => (
                    <TableCell key={yearIndex} align="right">
                      {formatCurrency(data.income_sources.specific_income[sourceId]?.[yearIndex] || 0)}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
            {Object.keys(data.income_sources.rental_income).map((assetIdStr) => {
              const assetId = Number(assetIdStr);
              const values = data.income_sources.rental_income[assetId] || [];
              if (values.every(v => v === 0)) return null;

              const assetName = data.asset_names[assetId];
              return (
                <TableRow key={`rental-${assetId}`}>
                  <TableCell sx={{ pl: 4, position: 'sticky', left: 0, backgroundColor: 'white', zIndex: 2, whiteSpace: 'nowrap' }}>
                    Rental Income - {assetName}
                  </TableCell>
                  {data.ages.map((_, yearIndex) => (
                    <TableCell key={yearIndex} align="right">
                      {formatCurrency(data.income_sources.rental_income[assetId]?.[yearIndex] || 0)}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
            <TableRow>
              <TableCell sx={{ pl: 2, fontWeight: 'bold', position: 'sticky', left: 0, backgroundColor: '#fff3e0', zIndex: 2, whiteSpace: 'nowrap' }}>
                Total Income
              </TableCell>
              {totalIncome.map((value, yearIndex) => (
                <TableCell key={yearIndex} align="right" sx={{ fontWeight: 'bold', backgroundColor: '#fff3e0' }}>
                  {formatCurrency(value)}
                </TableCell>
              ))}
            </TableRow>

            {/* Expenses Section */}
            <TableRow>
              <TableCell colSpan={numYears + 1} sx={{ backgroundColor: '#f5f5f5', fontWeight: 'bold' }}>
                EXPENSES
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 4, position: 'sticky', left: 0, backgroundColor: 'white', zIndex: 2, whiteSpace: 'nowrap' }}>
                Living Expenses (Retirement)
              </TableCell>
              {data.spending_nominal.map((value, yearIndex) => (
                <TableCell key={yearIndex} align="right">
                  {formatCurrency(value)}
                </TableCell>
              ))}
            </TableRow>

            {/* Net Cash Flow */}
            <TableRow>
              <TableCell sx={{ pl: 2, fontWeight: 'bold', position: 'sticky', left: 0, backgroundColor: '#fce4ec', zIndex: 2, whiteSpace: 'nowrap' }}>
                Net Cash Flow (Income - Exp)
              </TableCell>
              {data.net_cash_flow && data.net_cash_flow.map((value, yearIndex) => (
                <TableCell key={yearIndex} align="right" sx={{ fontWeight: 'bold', backgroundColor: '#fce4ec', color: value < 0 ? '#d32f2f' : '#2e7d32' }}>
                  {formatCurrency(value)}
                </TableCell>
              ))}
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default SimulationTable;

