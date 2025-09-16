
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Paper, Typography, Grid, CircularProgress, Alert, Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import { useApiClient } from '../hooks/useApiClient.ts';

const PaperTradingStatus = () => {
  const { getPaperTradingStatus } = useApiClient();
  const { data, error, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['paperTradingStatus'],
    queryFn: getPaperTradingStatus,
    refetchInterval: 60000, // Refetch every 1 minute
  });

  if (isLoading && !data) { // Show loader only on initial load
    return (
      <Paper elevation={3} sx={{ p: 2, mb: 2, textAlign: 'center' }}>
        <CircularProgress />
      </Paper>
    );
  }

  if (error) {
    return <Alert severity="error">Error fetching paper trading status.</Alert>;
  }

  if (!data) {
    return null; // Don't render anything if there's no data yet
  }

  const totalPnl = data.open_positions.reduce((acc, pos) => acc + (pos.pnl_usd || 0), 0);

  return (
    <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6">
          Paper Trading Status
        </Typography>
        {dataUpdatedAt && (
          <Typography variant="caption" color="text.secondary">
            Last updated: {new Date(dataUpdatedAt).toLocaleTimeString()}
          </Typography>
        )}
      </Box>
      <Grid container spacing={2}>
        <Grid item xs={4}>
          <Typography variant="subtitle1">Portfolio Value</Typography>
          <Typography variant="h5">${data.portfolio_value.toFixed(2)}</Typography>
        </Grid>
        <Grid item xs={4}>
          <Typography variant="subtitle1">Open Positions</Typography>
          <Typography variant="h5">{data.open_positions.length}</Typography>
        </Grid>
        <Grid item xs={4}>
          <Typography variant="subtitle1">Total Open PnL</Typography>
          <Typography variant="h5" color={totalPnl >= 0 ? 'success.main' : 'error.main'}>
            ${totalPnl.toFixed(2)}
          </Typography>
        </Grid>
      </Grid>

      {data.analysis_history && data.analysis_history.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6">Analysis and Positions</Typography>
          <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="simple table">
              <TableHead>
                <TableRow>
                  <TableCell>Crypto</TableCell>
                  <TableCell align="right">Signal</TableCell>
                  <TableCell align="right">Timestamp</TableCell>
                  <TableCell align="right">Entry Price</TableCell>
                  <TableCell align="right">Current Price</TableCell>
                  <TableCell align="right">Size (USD)</TableCell>
                  <TableCell align="right">Current Value (USD)</TableCell>
                  <TableCell align="right">PnL (USD)</TableCell>
                  <TableCell align="right">Opened Date</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.analysis_history.map((analysis) => {
                  const openPosition = data.open_positions.find(p => p.crypto_id === analysis.crypto_id);
                  return (
                    <TableRow
                      key={analysis.crypto_id}
                      sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                    >
                      <TableCell component="th" scope="row">
                        {analysis.crypto_id}
                      </TableCell>
                      <TableCell align="right">{analysis.signal}</TableCell>
                      <TableCell align="right">{new Date(analysis.timestamp).toLocaleString()}</TableCell>
                      {openPosition ? (
                        <>
                          <TableCell align="right">${openPosition.entry_price.toFixed(2)}</TableCell>
                          <TableCell align="right">${openPosition.current_price.toFixed(2)}</TableCell>
                          <TableCell align="right">${openPosition.size_usd.toFixed(2)}</TableCell>
                          <TableCell align="right">${openPosition.current_value_usd.toFixed(2)}</TableCell>
                          <TableCell align="right" sx={{ color: openPosition.pnl_usd >= 0 ? 'success.main' : 'error.main' }}>
                            ${openPosition.pnl_usd.toFixed(2)}
                          </TableCell>
                          <TableCell align="right">{new Date(openPosition.timestamp).toLocaleString()}</TableCell>
                        </>
                      ) : (
                        <TableCell colSpan={6} />
                      )}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}
    </Paper>
  );
};

export default PaperTradingStatus;
