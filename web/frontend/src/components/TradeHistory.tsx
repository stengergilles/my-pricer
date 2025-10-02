
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Paper, Typography, CircularProgress, Alert, useMediaQuery, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, List, ListItem, ListItemText } from '@mui/material';

import { useApiClient } from '../hooks/useApiClient.ts';

const TradeHistory = () => {
  const { getPaperTradingStatus } = useApiClient();
  const { data, error, isLoading } = useQuery({
    queryKey: ['paperTradingStatus'],
    queryFn: getPaperTradingStatus,
  });
  
  const isPortrait = useMediaQuery('(orientation: portrait)');

  if (isLoading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Alert severity="error">Error fetching trade history: {error.message}</Alert>;
  }

  const tradeHistory = data?.trade_history || [];

  if (tradeHistory.length === 0) {
    return <Typography>No trade history yet.</Typography>;
  }

  const tradeDates = tradeHistory.map(trade => new Date(trade.entry_date));
  const oldestTrade = new Date(Math.min.apply(null, tradeDates));
  const newestTrade = new Date(Math.max.apply(null, tradeDates));

  if (isPortrait) {
    return (
      <>
        <Typography variant="h6">Trade Period</Typography>
        <Typography variant="body2">Oldest Trade: {oldestTrade.toLocaleString()}</Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>Newest Trade: {newestTrade.toLocaleString()}</Typography>
        <List>
          {tradeHistory.map((trade, index) => (
            <Paper key={index} sx={{ mb: 2, p: 2 }}>
              <ListItem>
                <ListItemText
                  primary={`${trade.crypto_id} (${trade.signal})`}
                  secondary={
                    <>
                      <Typography component="span" variant="body2">Entry: {new Date(trade.entry_date).toLocaleString()}</Typography><br />
                      <Typography component="span" variant="body2">Exit: {trade.exit_date ? new Date(trade.exit_date).toLocaleString() : 'N/A'}</Typography><br />
                      <Typography component="span" variant="body2">Entry Reason: {trade.entry_reason}</Typography><br />
                      <Typography component="span" variant="body2">Exit Reason: {trade.exit_reason}</Typography><br />
                      <Typography component="span" variant="body2">Entry Value: ${trade.size_usd?.toFixed(2)}</Typography><br />
                      <Typography component="span" variant="body2">Exit Value: ${(trade.size_usd + trade.pnl_usd)?.toFixed(2)}</Typography><br />
                      <Typography component="span" variant="body2" color={trade.pnl_usd >= 0 ? 'success.main' : 'error.main'}>
                        PnL: ${trade.pnl_usd?.toFixed(2)}
                      </Typography>
                    </>
                  }
                />
              </ListItem>
            </Paper>
          ))}
        </List>
      </>
    );
  }

  return (
    <>
      <Typography variant="h6">Trade Period</Typography>
      <Typography variant="body2">Oldest Trade: {oldestTrade.toLocaleString()}</Typography>
      <Typography variant="body2" sx={{ mb: 2 }}>Newest Trade: {newestTrade.toLocaleString()}</Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Crypto</TableCell>
              <TableCell>Position</TableCell>
              <TableCell>Entry Date</TableCell>
              <TableCell>Exit Date</TableCell>
              <TableCell>Entry Reason</TableCell>
              <TableCell>Exit Reason</TableCell>
              <TableCell>Entry Value ($)</TableCell>
              <TableCell>Exit Value ($)</TableCell>
              <TableCell>PnL ($)</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tradeHistory.map((trade, index) => (
              <TableRow key={index}>
                <TableCell>{trade.crypto_id}</TableCell>
                <TableCell>{trade.signal}</TableCell>
                <TableCell>{new Date(trade.entry_date).toLocaleString()}</TableCell>
                <TableCell>{trade.exit_date ? new Date(trade.exit_date).toLocaleString() : 'N/A'}</TableCell>
                <TableCell>{trade.entry_reason}</TableCell>
                <TableCell>{trade.exit_reason}</TableCell>
                <TableCell>${trade.size_usd?.toFixed(2)}</TableCell>
                <TableCell>${(trade.size_usd + trade.pnl_usd)?.toFixed(2)}</TableCell>
                <TableCell>
                  <Typography color={trade.pnl_usd >= 0 ? 'success.main' : 'error.main'}>
                    {trade.pnl_usd?.toFixed(2)}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
};

export default TradeHistory;
