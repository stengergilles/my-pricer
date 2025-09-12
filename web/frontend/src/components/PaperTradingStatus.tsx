
import React from 'react';
import { useQuery } from 'react-query';
import { Paper, Typography, Grid, CircularProgress, Alert, Box } from '@mui/material';
import { useApiClient } from '../hooks/useApiClient';

const PaperTradingStatus = () => {
  const { getPaperTradingStatus } = useApiClient();
  const { data, error, isLoading, dataUpdatedAt } = useQuery('paperTradingStatus', getPaperTradingStatus, {
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
    </Paper>
  );
};

export default PaperTradingStatus;
