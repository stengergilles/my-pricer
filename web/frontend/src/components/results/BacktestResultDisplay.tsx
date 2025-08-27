// web/frontend/src/components/results/BacktestResultDisplay.tsx
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Chip,
} from '@mui/material'
import { styled } from '@mui/system'
import { BacktestResponse } from '../../utils/types'

const StyledCard = styled(Card)(({ theme }) => ({
  marginTop: theme.spacing(2),
  background: theme.palette.background.paper,
}))

const MetricItem = ({ label, value }: { label: string; value: string | number | undefined }) => (
  <ListItem>
    <ListItemText primary={label} secondary={value || 'N/A'} />
  </ListItem>
)

export const BacktestResultDisplay = ({ result }: { result: BacktestResponse }) => {
  if (!result || !result.result) return null

  const {
    crypto,
    strategy,
    timeframe,
    total_profit_percentage,
    total_trades,
    win_rate,
    max_drawdown,
    parameters,
  } = result.result

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Backtest Summary
              </Typography>
              <List dense>
                <MetricItem label="Cryptocurrency" value={crypto.toUpperCase()} />
                <MetricItem label="Strategy" value={strategy.replace(/_/g, ' ')} />
                <MetricItem label="Timeframe" value={`${timeframe} days`} />
              </List>
            </CardContent>
          </StyledCard>
        </Grid>
        <Grid item xs={12} md={6}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Performance Metrics
              </Typography>
              <List dense>
                <MetricItem
                  label="Total Profit"
                  value={`${total_profit_percentage?.toFixed(2)}%`}
                />
                <MetricItem label="Total Trades" value={total_trades} />
                <MetricItem label="Win Rate" value={`${win_rate?.toFixed(1)}%`} />
                <MetricItem
                  label="Max Drawdown"
                  value={`${max_drawdown?.toFixed(2)}%`}
                />
              </List>
            </CardContent>
          </StyledCard>
        </Grid>
      </Grid>

      {parameters && Object.keys(parameters).length > 0 && (
        <StyledCard>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Parameters Used
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {Object.entries(parameters).map(([key, value]) => (
                <Chip
                  key={key}
                  label={`${key.replace(/_/g, ' ')}: ${value}`}
                  variant="outlined"
                />
              ))}
            </Box>
          </CardContent>
        </StyledCard>
      )}
    </Box>
  )
}
