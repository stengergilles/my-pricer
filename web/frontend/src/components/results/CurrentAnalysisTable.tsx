import React from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography } from '@mui/material';
import { Analysis, OpenPosition } from '../../utils/types'; // Import OpenPosition

interface CurrentAnalysisTableProps {
  currentAnalysis: Analysis[];
  openPositions: OpenPosition[]; // Add openPositions prop
}

const CurrentAnalysisTable: React.FC<CurrentAnalysisTableProps> = ({ currentAnalysis, openPositions }) => {
  if (!currentAnalysis || currentAnalysis.length === 0) {
    return <Typography>No current analysis available.</Typography>;
  }

  return (
    <TableContainer component={Paper} sx={{ mt: 2 }}>
      <Table sx={{ minWidth: 650 }} aria-label="current analysis table">
        <TableHead>
          <TableRow>
            <TableCell>Crypto</TableCell>
            <TableCell>Strategy</TableCell>
            <TableCell>Signal</TableCell>
            <TableCell>Analysis Date</TableCell>
            <TableCell>Position Value</TableCell>
            <TableCell>Expected Profit (Backtest)</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {currentAnalysis.map((analysis) => {
            const position = openPositions.find(pos => pos.crypto_id === analysis.crypto_id);
            const positionValue = position?.current_value_usd ? `${position.current_value_usd.toFixed(2)}` : 'N/A';

            return (
              <TableRow key={analysis.analysis_id}>
                <TableCell>{analysis.crypto_id}</TableCell>
                <TableCell>{analysis.strategy_used}</TableCell>
                <TableCell>{analysis.current_signal}</TableCell>
                <TableCell>{new Date(analysis.analysis_timestamp).toLocaleString()}</TableCell>
                <TableCell>{positionValue}</TableCell>
                <TableCell>
                  {analysis.backtest_result?.total_profit_percentage?.toFixed(2) ?? 'N/A'}%
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default CurrentAnalysisTable;