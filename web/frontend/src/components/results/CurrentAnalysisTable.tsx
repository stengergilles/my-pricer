import React, { useState } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, useMediaQuery, Dialog, DialogTitle, DialogContent, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import HistoryIcon from '@mui/icons-material/History'; // Import HistoryIcon
import { Analysis, OpenPosition } from '../../utils/types';
import { useApiClient } from '../../hooks/useApiClient.ts';
import { useErrorHandler } from '../../hooks/useErrorHandler.ts';
import { ErrorDisplay } from '../ErrorDisplay.tsx';

interface CurrentAnalysisTableProps {
  currentAnalysis: Analysis[];
  openPositions: OpenPosition[];
}

const CurrentAnalysisTable: React.FC<CurrentAnalysisTableProps> = ({ currentAnalysis, openPositions }) => {
  const isPortrait = useMediaQuery('(orientation: portrait)');
  const [openHistoryModal, setOpenHistoryModal] = useState(false);
  const [selectedCrypto, setSelectedCrypto] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [fetchedTradeHistory, setFetchedTradeHistory] = useState<any[]>([]);
  const { getTradeHistory } = useApiClient();
  const { showError } = useErrorHandler();
  const { is403Error, handleError, errorMessage, clearError } = useErrorHandler();

  const handleShowHistory = async (cryptoId: string, date: string) => {
    setSelectedCrypto(cryptoId);
    setSelectedDate(date);
    try {
      const history = await getTradeHistory(date, cryptoId);
      setFetchedTradeHistory(history);
      setOpenHistoryModal(true);
    } catch (error: any) {
      console.error("Error fetching trade history:", error);
      if (!handleError(error)) {
        showError("Failed to fetch trade history.");
      }
    }
  };

  const handleCloseHistoryModal = () => {
    setOpenHistoryModal(false);
    setFetchedTradeHistory([]);
    setSelectedCrypto('');
    setSelectedDate('');
  };

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
            <TableRow>{isPortrait ? (<TableCell>Crypto / Strategy / Type</TableCell>) : (<><TableCell>Crypto</TableCell><TableCell>Strategy</TableCell><TableCell>Type</TableCell></>)}{isPortrait ? '' : <TableCell>Analysis Date</TableCell>}{isPortrait ? (<TableCell>Position & Profit</TableCell>) : (<><TableCell>Position Value</TableCell><TableCell>Expected Profit (Backtest)</TableCell></>)}<TableCell>Actions</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {currentAnalysis.map((analysis) => {
              const position = openPositions.find(pos => pos.crypto_id === analysis.crypto_id);
              console.log("Position in CurrentAnalysisTable:", position); // Debugging line
              const positionValue = position?.current_value_usd ? `${position.current_value_usd.toFixed(2)}` : 'N/A';
              const analysisDate = new Date(analysis.analysis_timestamp);
              const formattedAnalysisDate = analysisDate.toISOString().split('T')[0];

              return (
                <TableRow key={analysis.analysis_id}>
                  {isPortrait ? (<TableCell><Typography variant="body2">{analysis.crypto_id}</Typography><Typography variant="body2">{analysis.strategy_used}</Typography><Typography variant="body2">Type: {position?.signal || 'N/A'}</Typography></TableCell>) : (<><TableCell>{analysis.crypto_id}</TableCell><TableCell>{analysis.strategy_used}</TableCell><TableCell>{position?.signal || 'N/A'}</TableCell></>)}
                  {isPortrait ? null : <TableCell>{analysisDate.toLocaleString()}</TableCell>}
                  {isPortrait ? (<TableCell><Typography variant="body2">Position Value:<Typography component="span" color={position ? (position.pnl_usd >= 0 ? 'success.main' : 'error.main') : 'inherit'}>{' '}{positionValue}</Typography></Typography><Typography variant="body2">Expected Profit: {analysis.backtest_result?.total_profit_percentage?.toFixed(2) ?? 'N/A'}%</Typography></TableCell>) : (<><TableCell><Typography color={position ? (position.pnl_usd >= 0 ? 'success.main' : 'error.main') : 'inherit'}>{positionValue}</Typography></TableCell><TableCell>{analysis.backtest_result?.total_profit_percentage?.toFixed(2) ?? 'N/A'}%</TableCell></>)}
                  <TableCell>
                    <IconButton
                      aria-label="show history"
                      size="small"
                      onClick={() => handleShowHistory(analysis.crypto_id, formattedAnalysisDate)}
                    >
                      <HistoryIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openHistoryModal} onClose={handleCloseHistoryModal} maxWidth="md" fullWidth>
        <DialogTitle>
          Trade History for {selectedCrypto} on {selectedDate}
          <IconButton
            aria-label="close"
            onClick={handleCloseHistoryModal}
            sx={{
              position: 'absolute',
              right: 8,
              top: 8,
              color: (theme) => theme.palette.grey[500],
            }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {fetchedTradeHistory.length > 0 ? (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Price</TableCell>
                    <TableCell>Quantity</TableCell>
                    <TableCell>Total Value</TableCell>
                    <TableCell>PnL (USD)</TableCell>
                    <TableCell>Reason</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {fetchedTradeHistory.map((trade, index) => (
                    <TableRow key={index}><TableCell>{new Date(trade.timestamp).toLocaleString()}</TableCell><TableCell>{trade.trade_type}</TableCell><TableCell>{trade.price.toFixed(2)}</TableCell><TableCell>{trade.quantity.toFixed(4)}</TableCell><TableCell>{trade.total_value.toFixed(2)}</TableCell><TableCell>{trade.pnl_usd ? trade.pnl_usd.toFixed(2) : 'N/A'}</TableCell><TableCell>{trade.reason || 'N/A'}</TableCell></TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography>No trades recorded for this day.</Typography>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

      
export default CurrentAnalysisTable;
