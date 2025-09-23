import React from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography } from '@mui/material';
import { Analysis } from '../../utils/types';

interface CurrentAnalysisTableProps {
  currentAnalysis: Analysis[];
}

const CurrentAnalysisTable: React.FC<CurrentAnalysisTableProps> = ({ currentAnalysis }) => {
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
            <TableCell>Current Price</TableCell>
            <TableCell>Daily Change</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {currentAnalysis.map((analysis) => (
            <TableRow key={analysis.analysis_id}>
              <TableCell>{analysis.crypto_id}</TableCell>
              <TableCell>{analysis.strategy_used}</TableCell>
              <TableCell>{analysis.current_signal}</TableCell>
              <TableCell>{new Date(analysis.analysis_timestamp).toLocaleString()}</TableCell>
              <TableCell>${analysis.current_price.toFixed(2)}</TableCell>
              <TableCell>
                {analysis.backtest_result?.total_profit_percentage?.toFixed(2) ?? 'N/A'}%
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default CurrentAnalysisTable;