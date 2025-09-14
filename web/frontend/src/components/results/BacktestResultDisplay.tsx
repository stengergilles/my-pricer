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
  width: '100%', // Make width flexible
  contain: 'paint',
}))

const MetricItem = ({ label, value }: { label: string; value: string | number | undefined }) => (
  <ListItem>
    <ListItemText primary={label} secondary={value ?? 'N/A'} />
  </ListItem>
)

export const BacktestResultDisplay = ({ result }: { result: BacktestResponse }) => {
  if (!result) return null

  const {
    strategy,
    timeframe,
    parameters,
    crypto,
    backtest_result,
    source, // Destructure source
  } = result

  const {
    total_profit_percentage,
    total_trades,
    win_rate,
    max_drawdown,
  } = backtest_result || {}

  return (
    <Box>
      {source && (
        <Chip
          label={source === 'optimized' ? 'Optimized Result' : 'Manual Result'}
          color={source === 'optimized' ? 'primary' : 'default'}
          sx={{ marginBottom: 2 }}
        />
      )}
      <Grid container spacing={3} sx={{ flexDirection: { xs: 'column', md: 'row' } }}>
        <Grid item xs={12} md={6}>
          <StyledCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Backtest Summary
              </Typography>
              <List dense>
                <MetricItem label="Cryptocurrency" value={crypto?.toUpperCase()} />
                <MetricItem label="Strategy" value={strategy?.replace(/_/g, ' ')} />
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
                  value={total_profit_percentage != null ? `${total_profit_percentage.toFixed(2)}%` : undefined}
                />
                <MetricItem label="Total Trades" value={total_trades} />
                <MetricItem label="Win Rate" value={win_rate != null ? `${win_rate.toFixed(1)}%` : undefined} />
                <MetricItem
                  label="Max Drawdown"
                  value={max_drawdown != null ? `${max_drawdown.toFixed(2)}%` : undefined}
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
