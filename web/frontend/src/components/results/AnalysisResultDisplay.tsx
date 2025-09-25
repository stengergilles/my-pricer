// web/frontend/src/components/results/AnalysisResultDisplay.tsx
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
} from '@mui/material'
import { styled } from '@mui/system'
import { AnalysisResult, Line, BacktestResponse } from '../../utils/types'

const StyledCard = styled(Card)(({ theme }) => ({
  marginTop: theme.spacing(2),
  background: theme.palette.background.paper,
  width: '100%', // Make width flexible
}))

const MetricItem = ({ label, value }: { label: string; value: string | number | undefined }) => (
  <ListItem>
    <ListItemText
      primary={label}
      secondary={value !== undefined && value !== null ? value : 'N/A'}
      secondaryTypographyProps={{
        color:
          label === 'Current Signal'
            ? value === 'BUY'
              ? 'success.main'
              : value === 'SELL'
              ? 'error.main'
              : 'text.secondary'
            : 'text.secondary',
      }}
    />
  </ListItem>
)

const LineList = ({ title, lines }: { title: string; lines: Line[] | undefined }) => (
  <Box>
    <Typography variant="subtitle1" gutterBottom>
      {title}
    </Typography>
    {lines && lines.length > 0 ? (
      <List dense>
        {lines.map((line, index) => (
          <ListItem key={index}>
            <ListItemText
              primary={`$${line.price?.toFixed(2)}`}
              secondary={`Strength: ${line.strength}, Type: ${line.type}`}
            />
          </ListItem>
        ))}
      </List>
    ) : (
      <Typography variant="body2" color="text.secondary">
        None Found
      </Typography>
    )}
  </Box>
)

export const AnalysisResultDisplay = ({
  result,
  backtestHistory = [],
  onBacktestSelect,
}: {
  result: AnalysisResult,
  backtestHistory: BacktestResponse[],
  onBacktestSelect: (backtest: BacktestResponse) => void,
}) => {
  if (!result) {
    return null;
  }

  const {
    crypto_id,
    current_price,
    current_signal,
    active_resistance_lines,
    active_support_lines,
    chart_data,
    backtest_result,
  } = result;

  const sortedBacktests = [...backtestHistory].sort((a, b) => {
    const profitA = a.backtest_result?.total_profit_percentage ?? -Infinity;
    const profitB = b.backtest_result?.total_profit_percentage ?? -Infinity;
    return profitB - profitA;
  });

  const handleSelectChange = (event: any) => {
    const selectedId = event.target.value;
    const selectedBacktest = sortedBacktests.find(b => b.backtest_id === selectedId);
    if (selectedBacktest) {
      onBacktestSelect(selectedBacktest);
    }
  };

  const backtestToDisplay = backtest_result || (sortedBacktests.length > 0 ? sortedBacktests[0].backtest_result : null);
  const backtestSource = backtestToDisplay?.source || (sortedBacktests.length > 0 ? sortedBacktests[0].source : null);

  const {
    total_profit_percentage,
    total_trades,
    win_rate,
  } = backtestToDisplay || {};

  return (
    <Box>
      <Grid container spacing={3} sx={{ flexDirection: { xs: 'column', md: 'row' } }}>
        <Grid item xs={12} md={6}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Crypto Analysis
              </Typography>
              <List dense>
                <MetricItem label="Cryptocurrency" value={crypto_id?.toUpperCase()} />
                <MetricItem
                  label="Current Price"
                  value={`${current_price.toLocaleString()}`}
                />
                <MetricItem label="Current Signal" value={current_signal} />
              </List>
            </CardContent>
          </StyledCard>
        </Grid>
        <Grid item xs={12} md={6}>
            <StyledCard>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Backtest Performance
                </Typography>
                {backtestToDisplay && backtestToDisplay.total_trades !== undefined ? (
                  <List dense>
                    {backtestSource && (
                        <ListItem>
                            <Chip 
                                label={backtestSource === 'optimized' ? 'Optimized Result' : 'Manual Backtest'} 
                                color={backtestSource === 'optimized' ? 'success' : 'info'}
                                size="small" 
                            />
                        </ListItem>
                    )}
                    <ListItem>
                      <FormControl fullWidth>
                        <InputLabel id="backtest-select-label">Strategy</InputLabel>
                        <Select
                          labelId="backtest-select-label"
                          value={result.backtest_result?.backtest_id || result.analysis_id || ''}
                          onChange={handleSelectChange}
                          label="Strategy"
                        >
                          {sortedBacktests.map((backtest) => (
                            <MenuItem key={backtest.backtest_id} value={backtest.backtest_id}>
                              {backtest.strategy || 'Error: Strategy Missing'}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </ListItem>
                    <MetricItem
                      label="Total Profit"
                      value={total_profit_percentage !== undefined && total_profit_percentage !== null ? `${total_profit_percentage.toFixed(2)}%` : 'N/A'}
                    />
                    {backtestToDisplay?.timestamp && (
                      <MetricItem
                        label="Backtest Date"
                        value={new Date(backtestToDisplay.timestamp).toLocaleString()}
                      />
                    )}
                    <MetricItem label="Total Trades" value={total_trades !== undefined && total_trades !== null ? total_trades : 'N/A'} />
                    <MetricItem label="Win Rate" value={win_rate !== undefined && win_rate !== null ? `${win_rate.toFixed(1)}%` : 'N/A'} />
                  </List>
                ) : (
                  <Typography>No backtest results available.</Typography>
                )}
              </CardContent>
            </StyledCard>
          </Grid>
      </Grid>

      {result.next_move_prediction && (
        <StyledCard>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Next Move Prediction
            </Typography>
            <List dense>
              <MetricItem label="Prediction Score" value={result.next_move_prediction.prediction_score} />
              <ListItem>
                <ListItemText primary="Reasons" />
              </ListItem>
              <List dense disablePadding>
                {result.next_move_prediction.reasons?.map((reason, index) => (
                  <ListItem key={index}>
                    <ListItemText primary={`- ${reason}`} />
                  </ListItem>
                ))}
              </List>
              <MetricItem label="Prediction" value={result.next_move_prediction.direction} />
              <MetricItem label="Confidence" value={`${result.next_move_prediction.confidence?.toFixed(1)}%`} />
            </List>
          </CardContent>
        </StyledCard>
      )}

      <StyledCard>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Support & Resistance Levels
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <LineList
                title="Active Resistance"
                lines={active_resistance_lines}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <LineList title="Active Support" lines={active_support_lines} />
            </Grid>
          </Grid>
        </CardContent>
      </StyledCard>

      {chart_data && (
        <StyledCard>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Chart
            </Typography>
            <img src={chart_data} alt={`${crypto_id} chart`} style={{ maxWidth: '100%' }} />
          </CardContent>
        </StyledCard>
      )}
    </Box>
  )
}
