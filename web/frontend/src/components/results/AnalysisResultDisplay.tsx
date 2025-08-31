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
} from '@mui/material'
import { styled } from '@mui/system'
import { AnalysisResult, Line } from '../../utils/types'

const StyledCard = styled(Card)(({ theme }) => ({
  marginTop: theme.spacing(2),
  background: theme.palette.background.paper,
  width: '100%', // Make width flexible
}))

const MetricItem = ({ label, value }: { label: string; value: string | number | undefined }) => (
  <ListItem>
    <ListItemText
      primary={label}
      secondary={value || 'N/A'}
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

export const AnalysisResultDisplay = ({ result }: { result: AnalysisResult }) => {
  // console.log("AnalysisResultDisplay: result prop received:", result); // Removed for production
  if (!result) {
    // console.log("AnalysisResultDisplay: result is null or undefined, returning null."); // Removed for production
    return null;
  }

  const {
    crypto_id,
    current_price,
    current_signal,
    strategy_used,
    active_resistance_lines,
    active_support_lines,
    chart_data,
    backtest_result,
  } = result;

  const {
    total_profit_percentage,
    num_trades: total_trades,
    win_rate,
  } = backtest_result || {};

  // console.log("AnalysisResultDisplay: active_resistance_lines:", active_resistance_lines); // Removed for production
  // console.log("AnalysisResultDisplay: active_support_lines:", active_support_lines); // Removed for production

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
                <MetricItem
                  label="Strategy Used"
                  value={strategy_used.replace(/_/g, ' ')}
                />
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
              <List dense>
                <MetricItem
                  label="Total Profit"
                  value={`${total_profit_percentage?.toFixed(2)}%`}
                />
                <MetricItem label="Total Trades" value={total_trades} />
                <MetricItem label="Win Rate" value={`${win_rate?.toFixed(1)}%`} />
              </List>
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
