import React from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, useMediaQuery, Box } from '@mui/material';
import BlockIcon from '@mui/icons-material/Block';


import { Analysis, OpenPosition } from '../../utils/types';

import { useErrorHandler } from '../../hooks/useErrorHandler.ts';
import { ErrorDisplay } from '../ErrorDisplay.tsx';

interface CurrentAnalysisTableProps {
  currentAnalysis: Analysis[];
  openPositions: OpenPosition[];
}

const CurrentAnalysisTable: React.FC<CurrentAnalysisTableProps> = ({ currentAnalysis, openPositions }) => {
  const isPortrait = useMediaQuery('(orientation: portrait)');
  
  
  const { is403Error, errorMessage, clearError } = useErrorHandler();

  

  if (!currentAnalysis || currentAnalysis.length === 0) {
    return <Typography>No current analysis available.</Typography>;
  }

  if (is403Error) {
    return <ErrorDisplay error="403 Forbidden" onRetry={() => { /* TODO: implement retry logic */ }} is403={true} onDismiss={clearError} />;
  }

  return (
    <>
      <ErrorDisplay error={errorMessage} onDismiss={clearError} />
      <TableContainer component={Paper} sx={{ mt: 2 }}>
        <Table sx={{ minWidth: isPortrait ? 'auto' : 650 }} aria-label="current analysis table">
          <TableHead>
            <TableRow>
              {isPortrait ? (
                <TableCell>Crypto / Strategy / Type</TableCell>
              ) : (
                <>
                  <TableCell>Crypto</TableCell>
                  <TableCell>Strategy</TableCell>
                  <TableCell>Type</TableCell>
                </>
              )}
              {isPortrait ? null : <TableCell>Analysis Date</TableCell>}
              {isPortrait ? (
                <TableCell>ADX Trends</TableCell>
              ) : (
                <>
                  <TableCell>Current ADX</TableCell>
                  <TableCell>Backtest ADX Trend</TableCell>
                </>
              )}
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
              const isFrozen = analysis.is_frozen_due_to_stale_data || position?.is_frozen_due_to_stale_data;
              console.log("Position in CurrentAnalysisTable:", position); // Debugging line
              const positionValue = position?.current_value_usd ? `${position.current_value_usd}` : 'N/A';
              const analysisDate = new Date(analysis.analysis_timestamp);
              

              return (
                <TableRow key={analysis.analysis_id} sx={{ backgroundColor: isFrozen ? 'rgba(255, 0, 0, 0.1)' : 'inherit' }}>
                  {isPortrait ? (
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Typography variant="body2">{analysis.crypto_id}</Typography>
                        {isFrozen && <BlockIcon color="error" sx={{ ml: 0.5, fontSize: 'small' }} />}
                      </Box>
                      <Typography variant="body2">{analysis.strategy_used}</Typography>
                      <Typography variant="body2">Type: {position?.signal || 'N/A'}</Typography>
                    </TableCell>
                  ) : (
                    <>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Typography>{analysis.crypto_id}</Typography>
                          {isFrozen && <BlockIcon color="error" sx={{ ml: 0.5, fontSize: 'small' }} />}
                        </Box>
                      </TableCell>
                      <TableCell>{analysis.strategy_used}</TableCell>
                      <TableCell>{position?.signal || 'N/A'}</TableCell>
                    </>
                  )}
                  {isPortrait ? null : <TableCell>{analysisDate.toLocaleString()}</TableCell>}
                  {isPortrait ? (
                    <TableCell>
                      <Typography variant="body2">Current: {analysis.current_adx_trend ?? 'N/A'}</Typography>
                      <Typography variant="body2">Backtest: {analysis.backtested_adx_trend ?? 'N/A'}</Typography>
                    </TableCell>
                  ) : (
                    <>
                      <TableCell>{analysis.current_adx_trend ?? 'N/A'}</TableCell>
                      <TableCell>{analysis.backtested_adx_trend ?? 'N/A'}</TableCell>
                    </>
                  )}
                  {isPortrait ? (
                    <TableCell>
                      <Typography variant="body2">Position Value:
                        <Typography component="span" color={position ? (position.pnl_usd >= 0 ? 'success.main' : 'error.main') : 'inherit'}>{' '}{positionValue}</Typography>
                      </Typography>
                      <Typography variant="body2">Backtest Profit %: {analysis.backtest_result?.total_profit_percentage?.toFixed(2) ?? 'N/A'}%</Typography>
                    </TableCell>
                  ) : (
                    <>
                      <TableCell>
                        <Typography color={position ? (position.pnl_usd >= 0 ? 'success.main' : 'error.main') : 'inherit'}>{positionValue}</Typography>
                      </TableCell>
                      <TableCell>{analysis.backtest_result?.total_profit_percentage?.toFixed(2) ?? 'N/A'}%</TableCell>
                    </>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      
    </>
  );
};

      
export default CurrentAnalysisTable;
