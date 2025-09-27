import React from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, useMediaQuery } from '@mui/material';
import { Analysis, OpenPosition } from '../../utils/types'; // Import OpenPosition

interface CurrentAnalysisTableProps {
  currentAnalysis: Analysis[];
  openPositions: OpenPosition[]; // Add openPositions prop
}

const CurrentAnalysisTable: React.FC<CurrentAnalysisTableProps> = ({ currentAnalysis, openPositions }) => {
  const isPortrait = useMediaQuery('(orientation: portrait)');

  if (!currentAnalysis || currentAnalysis.length === 0) {
    return <Typography>No current analysis available.</Typography>;
  }

  return (
    <TableContainer component={Paper} sx={{ mt: 2 }}>
      <Table sx={{ minWidth: isPortrait ? 'auto' : 650 }} aria-label="current analysis table">
        <TableHead>
          <TableRow>
            {isPortrait ? (
              <TableCell>Crypto / Strategy</TableCell>
            ) : (
              <>
                <TableCell>Crypto</TableCell>
                <TableCell>Strategy</TableCell>
              </>
            )}
            {isPortrait ? null : <TableCell>Analysis Date</TableCell>}
            {isPortrait ? (
              <TableCell>Position & Profit</TableCell>
            ) : (
              <>
                <TableCell>Position Value</TableCell>
                <TableCell>Expected Profit (Backtest)</TableCell>
              </>
            )}
          </TableRow>
        </TableHead>
        <TableBody>
          {currentAnalysis.map((analysis) => {
            const position = openPositions.find(pos => pos.crypto_id === analysis.crypto_id);
            const positionValue = position?.current_value_usd ? `$${position.current_value_usd.toFixed(2)}` : 'N/A';
            const analysisDate = new Date(analysis.analysis_timestamp);

            return (
              <TableRow key={analysis.analysis_id}>
                {isPortrait ? (
                  <TableCell>
                    <Typography variant="body2">{analysis.crypto_id}</Typography>
                    <Typography variant="body2">{analysis.strategy_used}</Typography>
                  </TableCell>
                ) : (
                  <>
                    <TableCell>{analysis.crypto_id}</TableCell>
                    <TableCell>{analysis.strategy_used}</TableCell>
                  </>
                )}
                {isPortrait ? null : <TableCell>{analysisDate.toLocaleString()}</TableCell>}
                {isPortrait ? (
                  <TableCell>
                    <Typography variant="body2">
                      Position Value:
                      <Typography component="span" color={position?.pnl_usd && position.pnl_usd >= 0 ? 'success.main' : 'error.main'}>
                        {' '}{positionValue}
                      </Typography>
                    </Typography>
                    <Typography variant="body2">
                      Expected Profit: {analysis.backtest_result?.total_profit_percentage?.toFixed(2) ?? 'N/A'}%
                    </Typography>
                  </TableCell>
                ) : (
                  <>
                    <TableCell>
                      <Typography color={position?.pnl_usd && position.pnl_usd >= 0 ? 'success.main' : 'error.main'}>
                        {positionValue}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {analysis.backtest_result?.total_profit_percentage?.toFixed(2) ?? 'N/A'}%
                    </TableCell>
                  </>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default CurrentAnalysisTable;
