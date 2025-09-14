export class ApiClient {
  public baseUrl: string;
  private getAccessToken?: () => Promise<string | undefined>;

  constructor(getAccessToken?: () => Promise<string | undefined>) {
    this.getAccessToken = getAccessToken;

    this.baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';

    // Bind methods to the instance to preserve 'this' context
    this.getCryptos = this.getCryptos.bind(this);
    this.getCrypto = this.getCrypto.bind(this);
    this.getCryptoStatus = this.getCryptoStatus.bind(this); // New method
    this.getStrategies = this.getStrategies.bind(this);
    this.getStrategy = this.getStrategy.bind(this);
    this.runAnalysis = this.runAnalysis.bind(this);
    this.getAnalysis = this.getAnalysis.bind(this);
    this.getAnalysisHistory = this.getAnalysisHistory.bind(this);
    this.runBacktest = this.runBacktest.bind(this);
    this.getBacktest = this.getBacktest.bind(this);
    this.getBacktestHistory = this.getBacktestHistory.bind(this);
    this.healthCheck = this.healthCheck.bind(this);
    this.getPaperTradingStatus = this.getPaperTradingStatus.bind(this);
    this.getConfig = this.getConfig.bind(this);
    this.getJobs = this.getJobs.bind(this);
    this.scheduleJob = this.scheduleJob.bind(this);
    this.deleteJob = this.deleteJob.bind(this);
    this.getJobLogs = this.getJobLogs.bind(this);
  }

  private async request(method: string, endpoint: string, data?: any) {
    const url = `${this.baseUrl}${endpoint}`;
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (this.getAccessToken) {
      const token = await this.getAccessToken();
      if (token) {
        (options.headers as Record<string, string>).Authorization = `Bearer ${token}`;
      }
    }

    if (data) {
      options.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, options);

      if (!response.ok) {
        const errorBody = await response.text();
        let errorMessage = `HTTP error! status: ${response.status}`;
        let errorJson: any = {};
        try {
          errorJson = JSON.parse(errorBody);
          errorMessage = errorJson.error || errorJson.message || errorMessage;
        } catch (e) {
          errorMessage = `${errorMessage}, body: ${errorBody}`;
        }
        const errorToThrow = new Error(errorMessage);
        (errorToThrow as any).response = {
          status: response.status,
          data: errorJson
        };
        throw errorToThrow;
      }

      // Handle cases where response might be empty (e.g., 204 No Content)
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        return await response.json();
      } else {
        return {}; // Return empty object for non-JSON responses (e.g., 200 OK with no content)
      }
    } catch (error: any) {
      // console.error('ApiClient Fetch Error:', error); // Removed for production
      throw error;
    } finally {
    }
  }

  // Crypto endpoints
  async getCryptos(params?: { volatile?: boolean; min_volatility?: number; limit?: number; force_refresh?: boolean }) {
    const queryParams = new URLSearchParams();
    if (params?.volatile) queryParams.append('volatile', 'true');
    if (params?.min_volatility) queryParams.append('min_volatility', params.min_volatility.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.force_refresh) queryParams.append('force_refresh', 'true');

    const queryString = queryParams.toString();
    return this.request('GET', `/api/cryptos${queryString ? `?${queryString}` : ''}`);
  }

  async getCrypto(cryptoId: string) {
    return this.request('GET', `/api/cryptos/${cryptoId}`);
  }

  async getCryptoStatus(cryptoId: string) {
    return this.request('GET', `/api/crypto_status/${cryptoId}`);
  }

  // Strategy endpoints
  async getStrategies() {
    return this.request('GET', '/api/strategies');
  }

  async getStrategy(strategyName: string) {
    return this.request('GET', `/api/strategies/${strategyName}`);
  }

  // Analysis endpoints
  async runAnalysis(data: {
    crypto_id: string
    strategy_name?: string
    timeframe?: number
    parameters?: Record<string, any>
  }) {
    return this.request('POST', '/api/analysis', data);
  }

  async getAnalysis(analysisId: string) {
    return this.request('GET', `/api/analysis/${analysisId}`);
  }

  async getAnalysisHistory(cryptoId?: string, limit = 50) {
    const params = new URLSearchParams();
    if (cryptoId) params.append('crypto_id', cryptoId);
    params.append('limit', limit.toString());
    return this.request('GET', `/api/analysis?${params.toString()}`);
  }

  // Backtest endpoints
  async runBacktest(data: {
    crypto_id: string
    strategy_name: string
    parameters: Record<string, any>
    timeframe?: number
  }) {
    return this.request('POST', '/api/backtest', data);
  }

  async getBacktest(backtestId: string) {
    return this.request('GET', `/api/backtest/${backtestId}`);
  }

  async getBacktestHistory(cryptoId?: string, strategyName?: string, limit = 50, optimized_params?: boolean) {
    const params = new URLSearchParams();
    if (cryptoId) params.append('crypto_id', cryptoId);
    if (strategyName) params.append('strategy_name', strategyName);
    params.append('limit', limit.toString());
    if (optimized_params) params.append('optimized_params', 'true');
    return this.request('GET', `/api/backtest?${params.toString()}`);
  }

  // Health check
  async healthCheck() {
    return this.request('GET', '/api/health');
  }

  // Paper Trading status
  async getPaperTradingStatus() {
    return this.request('GET', '/api/paper-trading/status');
  }

  // Config endpoint
  async getConfig() {
    return this.request('GET', '/api/config');
  }

  // Scheduler endpoints
  async getJobs() {
    return this.request('GET', '/api/scheduler/jobs');
  }

  async scheduleJob(data: any) {
    return this.request('POST', '/api/scheduler/schedule', data);
  }

  async deleteJob(jobId: string) {
    return this.request('DELETE', `/api/scheduler/jobs/${jobId}`);
  }

  async getJobLogs(jobId: string) {
    return this.request('GET', `/api/scheduler/jobs/${jobId}/logs`);
  }
}
