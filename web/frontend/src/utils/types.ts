// API Response Types
export interface ApiResponse<T> {
  success?: boolean
  data?: T
  error?: string
  message?: string
}

// Crypto Types
export interface Crypto {
  id: string
  name: string
  symbol: string
  current_price?: number
}

// Strategy Types
export interface Strategy {
  name: string
  display_name: string
  description: string
  config: Record<string, any>
  parameters: Record<string, ParameterDefinition>
}

export interface ParameterDefinition {
  type: 'integer' | 'float' | 'string' | 'boolean'
  min?: number
  max?: number
  default: any
  description: string
}

// Analysis Types
export interface AnalysisRequest {
  crypto_id: string
  strategy_name?: string
  timeframe?: number
  parameters?: Record<string, any>
}

export interface AnalysisResult {
  analysis_id: string
  crypto_id: string
  strategy_used: string
  current_signal: 'LONG' | 'SHORT' | 'HOLD'
  current_price: number
  analysis_timestamp: string
  active_resistance_lines: any[]
  active_support_lines: any[]
  backtest_result?: BacktestResult
  next_move_prediction?: any
  parameters_used: Record<string, any> | string
  timeframe_days: number
  engine_version: string
  result_path?: string
  chart_data?: string
}

// Backtest Types
export interface BacktestRequest {
  crypto_id: string
  strategy_name: string
  parameters: Record<string, any>
  timeframe?: number
}

export interface BacktestResult {
  total_profit_percentage: number
  num_trades: number
  win_rate: number
  sharpe_ratio: number
  max_drawdown: number
  note?: string
}

export interface BacktestResponse {
  backtest_id: string
  crypto_id: string
  strategy_name: string
  parameters: Record<string, any>
  timeframe_days: number
  timestamp: string
  result: BacktestResult
  engine_version: string
  result_path?: string
  chart_data?: string
}

// Health Check Types
export interface HealthCheck {
  timestamp: string
  status: 'healthy' | 'warning' | 'error'
  checks: Record<string, {
    status: 'ok' | 'warning' | 'error'
    message?: string
    path?: string
    writable?: boolean
  }>
}

// Form Types
export interface AnalysisFormData {
  cryptoId: string
  strategyName: string
  timeframe: number
  useCustomParams: boolean
  parameters: Record<string, any>
}

export interface BacktestFormData {
  cryptoId: string
  strategyName: string
  timeframe: number
  parameters: Record<string, any>
}
