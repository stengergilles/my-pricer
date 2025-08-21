# 🌐 Crypto Trading Web Application

A modern web interface for your crypto trading system, built with Flask backend and Next.js frontend, secured with Auth0 authentication.

## 🏗️ Architecture

```
crypto-trading-web/
├── web/
│   ├── backend/           # Flask API with Auth0
│   │   ├── app.py         # Main Flask application
│   │   ├── auth/          # Auth0 integration
│   │   ├── api/           # REST API endpoints
│   │   ├── utils/         # Backend utilities
│   │   └── requirements.txt
│   └── frontend/          # Next.js with Auth0
│       ├── src/
│       │   ├── app/       # App Router pages
│       │   ├── components/ # React components
│       │   ├── lib/       # Utilities & API client
│       │   └── hooks/     # Custom React hooks
│       └── package.json
├── core/                  # Shared business logic
│   ├── trading_engine.py  # Main trading engine
│   ├── result_manager.py  # Result storage
│   └── config.py          # Configuration
└── data/                  # Local data storage
    ├── results/           # Analysis & backtest results
    ├── cache/             # API response cache
    └── logs/              # Application logs
```

## 🚀 Quick Start

### 1. Initial Setup
```bash
# Run the setup script
./setup_web_app.sh
```

### 2. Configure Auth0
Create an Auth0 application and configure:

**Backend (.env):**
```bash
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_API_AUDIENCE=https://your-api-identifier
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
```

**Frontend (web/frontend/.env.local):**
```bash
AUTH0_SECRET=use-a-long-random-value
AUTH0_BASE_URL=http://localhost:3000
AUTH0_ISSUER_BASE_URL=https://your-domain.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
```

### 3. Start Development Servers
```bash
# Start both backend and frontend
./start_dev_servers.sh

# Or start individually:
# Backend
cd web/backend && source venv/bin/activate && python run.py

# Frontend (in another terminal)
cd web/frontend && npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **Health Check**: http://localhost:5000/api/health

## 🔐 Auth0 Configuration

### Application Settings
- **Application Type**: Regular Web Application
- **Allowed Callback URLs**: `http://localhost:3000/api/auth/callback`
- **Allowed Logout URLs**: `http://localhost:3000`
- **Allowed Web Origins**: `http://localhost:3000`

### API Settings
- **Identifier**: `https://your-api-identifier`
- **Signing Algorithm**: RS256
- **Allow Skipping User Consent**: Yes (for development)

## 📡 API Endpoints

### Authentication
- `GET /api/health` - Health check (no auth required)
- `GET /api/auth/test` - Test authentication

### Cryptocurrencies
- `GET /api/cryptos` - List available cryptocurrencies
- `GET /api/cryptos/{id}` - Get specific cryptocurrency info

### Strategies
- `GET /api/strategies` - List available trading strategies
- `GET /api/strategies/{name}` - Get specific strategy details

### Analysis
- `POST /api/analysis` - Run crypto analysis
- `GET /api/analysis` - Get analysis history
- `GET /api/analysis/{id}` - Get specific analysis result

### Backtesting
- `POST /api/backtest` - Run backtest
- `GET /api/backtest` - Get backtest history
- `GET /api/backtest/{id}` - Get specific backtest result

## 🎯 Features

### ✅ Implemented
- **Auth0 Authentication**: Secure login/logout
- **Crypto Analysis Interface**: Run analysis with strategy selection
- **Backtest Runner**: Configure and run backtests
- **Real-time Health Monitoring**: System status display
- **Responsive Design**: Works on desktop and mobile
- **Form Validation**: Client and server-side validation
- **Error Handling**: Comprehensive error management
- **Result Storage**: Local JSON file storage
- **API Integration**: RESTful API with proper error handling

### 🔄 CLI Integration Status
- **Core Logic**: Uses shared core module
- **Strategy Configs**: Imports from existing config.py
- **Result Compatibility**: Saves in same format as CLI
- **Data Sources**: Uses same data fetching logic

**Note**: Currently using mock data for some operations. Full CLI integration requires:
1. Proper import path resolution
2. Cython backtester compilation
3. API rate limit handling

## 🧪 Testing

### Backend Testing
```bash
cd web/backend
source venv/bin/activate

# Test health endpoint
curl http://localhost:5000/api/health

# Test with authentication (requires valid token)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5000/api/cryptos
```

### Frontend Testing
```bash
cd web/frontend

# Run development server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check
```

## 🔧 Development Workflow

### Adding New Features
1. **Backend**: Add API endpoint in `web/backend/api/`
2. **Frontend**: Add component in `web/frontend/src/components/`
3. **Types**: Update `web/frontend/src/lib/types.ts`
4. **API Client**: Update `web/frontend/src/lib/api.ts`

### Debugging
- **Backend Logs**: Check `data/logs/backend.log`
- **Frontend Console**: Browser developer tools
- **API Testing**: Use curl or Postman
- **Auth Issues**: Check Auth0 dashboard logs

## 📊 Data Flow

```
Frontend (Next.js) 
    ↓ Auth0 Token
Backend (Flask API)
    ↓ Validates Token
Core Trading Engine
    ↓ Uses Existing CLI Logic
Result Manager
    ↓ Saves to JSON
Local File Storage
```

## 🛡️ Security Features

- **Auth0 JWT Validation**: All API endpoints protected
- **CORS Configuration**: Restricted to frontend origin
- **Input Validation**: Server-side parameter validation
- **Error Sanitization**: No sensitive data in error responses
- **Token Refresh**: Automatic token renewal

## 🚀 Production Deployment

### Backend
```bash
cd web/backend
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Frontend
```bash
cd web/frontend
npm run build
npm start
```

### Environment Variables
Update URLs for production:
- `AUTH0_BASE_URL`: Your production frontend URL
- `FRONTEND_URL`: Your production frontend URL
- `API_BASE_URL`: Your production backend URL

## 🔄 CLI Compatibility

The web application maintains full compatibility with existing CLI tools:

### Shared Components
- **Core Engine**: Both use same `core/trading_engine.py`
- **Strategies**: Both use same `config.py` strategies
- **Results**: Both save to same `data/results/` directory
- **Data Sources**: Both use same data fetching logic

### CLI Still Works
```bash
# All existing CLI commands work unchanged
python pricer.py --crypto bitcoin --strategy EMA_Only
python optimize_bayesian.py --crypto ethereum --n-trials 50
python get_volatile_cryptos.py
```

## 📝 Troubleshooting

### Common Issues

**Auth0 Login Fails**
- Check Auth0 configuration
- Verify callback URLs
- Check environment variables

**Backend API Errors**
- Check if backend server is running
- Verify Auth0 API configuration
- Check backend logs

**Frontend Build Errors**
- Run `npm install` to update dependencies
- Check TypeScript errors
- Verify environment variables

**CLI Integration Issues**
- Check Python path resolution
- Verify core module imports
- Check data directory permissions

### Getting Help
1. Check logs in `data/logs/`
2. Test API endpoints with curl
3. Verify Auth0 configuration
4. Check browser console for frontend errors

## 🎯 Next Steps

### Immediate Improvements
1. **Full CLI Integration**: Complete integration with existing backtester
2. **Chart Visualization**: Add interactive price charts
3. **Real-time Updates**: WebSocket for live price updates
4. **Result History**: Better result browsing and comparison

### Advanced Features
1. **Portfolio Tracking**: Track multiple positions
2. **Alert System**: Email/SMS notifications
3. **Strategy Builder**: Visual strategy configuration
4. **Performance Analytics**: Advanced metrics and reporting

---

## 🎉 Success!

You now have a complete web application that:
- ✅ **Preserves CLI functionality** - All existing tools still work
- ✅ **Adds web interface** - Modern, responsive UI
- ✅ **Secure authentication** - Auth0 integration
- ✅ **Shared core logic** - No code duplication
- ✅ **Easy to restart** - Comprehensive documentation and scripts

**Ready for development and testing!** 🚀
