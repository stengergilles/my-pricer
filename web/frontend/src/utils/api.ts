import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios'

export class ApiClient {
  private client: AxiosInstance

  constructor(getAccessToken?: () => Promise<string | undefined>) {
    this.client = axios.create({
      baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.request.use(
      async (config: InternalAxiosRequestConfig) => {
        if (getAccessToken) {
          try {
            const token = await getAccessToken();
            if (token) {
              config.headers.Authorization = `Bearer ${token}`;
            }
          } catch (error) {
            console.warn('Could not get access token:', error);
          }
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        // if (error.response?.status === 401) {
        //   // Redirect to login on unauthorized
        //   window.location.href = '/api/auth/login'
        // }
        return Promise.reject(error)
      }
    )
  }

  // Crypto endpoints
  async getCryptos() {
    const response = await this.client.get('/api/cryptos')
    return response.data
  }

  async getCrypto(cryptoId: string) {
    const response = await this.client.get(`/api/cryptos/${cryptoId}`)
    return response.data
  }

  // Strategy endpoints
  async getStrategies() {
    const response = await this.client.get('/api/strategies')
    return response.data
  }

  async getStrategy(strategyName: string) {
    const response = await this.client.get(`/api/strategies/${strategyName}`)
    return response.data
  }

  // Analysis endpoints
  async runAnalysis(data: {
    crypto_id: string
    strategy_name?: string
    timeframe?: number
    parameters?: Record<string, any>
  }) {
    const response = await this.client.post('/api/analysis', data)
    return response.data
  }

  async getAnalysis(analysisId: string) {
    const response = await this.client.get(`/api/analysis/${analysisId}`)
    return response.data
  }

  async getAnalysisHistory(cryptoId?: string, limit = 50) {
    const params = new URLSearchParams()
    if (cryptoId) params.append('crypto_id', cryptoId)
    params.append('limit', limit.toString())
    
    const response = await this.client.get(`/api/analysis?${params}`)
    return response.data
  }

  // Backtest endpoints
  async runBacktest(data: {
    crypto_id: string
    strategy_name: string
    parameters: Record<string, any>
    timeframe?: number
  }) {
    const response = await this.client.post('/api/backtest', data)
    return response.data
  }

  async getBacktest(backtestId: string) {
    const response = await this.client.get(`/api/backtest/${backtestId}`)
    return response.data
  }

  async getBacktestHistory(cryptoId?: string, strategyName?: string, limit = 50) {
    const params = new URLSearchParams()
    if (cryptoId) params.append('crypto_id', cryptoId)
    if (strategyName) params.append('strategy_name', strategyName)
    params.append('limit', limit.toString())
    
    const response = await this.client.get(`/api/backtest?${params}`)
    return response.data
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/api/health')
    return response.data
  }

  // Config endpoint
  async getConfig() {
    const response = await this.client.get('/api/config')
    return response.data
  }
}

export const apiClient = new ApiClient()
