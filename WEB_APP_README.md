# 🌐 Crypto Trading Web Application

A modern web interface for your crypto trading system, built with Flask backend and React frontend using Material-UI (MUI), secured with Auth0 authentication.

## 🏗️ Architecture

```
crypto-trading-web/
├── web/
│   ├── backend/           # Flask API with Auth0
│   │   ├── app.py         # Main Flask application
│   │   ├── auth/          # Auth0 integration & middleware
│   │   ├── api/           # REST API endpoints
│   │   ├── utils/         # Backend utilities
│   │   └── requirements.txt
│   └── frontend/          # React SPA with Material-UI
│       ├── src/
│       │   ├── components/ # React components (MUI-based)
│       │   ├── utils/     # API client & utilities
│       │   ├── hooks/     # Custom React hooks (useApiClient)
│       │   └── index.js   # Main app with Auth0Provider & MUI Theme
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

#### Frontend Configuration (`web/frontend/.env.local`)

Create your Auth0 Single Page Application (SPA) and configure the frontend environment:

```bash
REACT_APP_AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN_FROM_SPA_APP
REACT_APP_AUTH0_CLIENT_ID=YOUR_AUTH0_CLIENT_ID_FROM_SPA_APP
REACT_APP_AUTH0_AUDIENCE=YOUR_AUTH0_API_IDENTIFIER
```

**Variable Details:**
- **`REACT_APP_AUTH0_DOMAIN`**: Your Auth0 tenant domain (e.g., `dev-xxxxxxxx.eu.auth0.com`)
  - Find in: Auth0 Dashboard → Applications → (Your SPA Application) → Domain
- **`REACT_APP_AUTH0_CLIENT_ID`**: Client ID for your Auth0 Single Page Application
  - Find in: Auth0 Dashboard → Applications → (Your SPA Application) → Client ID
- **`REACT_APP_AUTH0_AUDIENCE`**: Unique identifier for your Auth0 API
  - Find in: Auth0 Dashboard → Applications → APIs → (Your API Name) → Identifier
  - **Critical**: This ensures the frontend requests an Access Token valid for your backend

#### Backend Configuration (`web/backend/.env`)

Configure the backend to validate Auth0 tokens:

```bash
AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN_FROM_SPA_APP
AUTH0_API_AUDIENCE=YOUR_AUTH0_API_IDENTIFIER
AUTH0_CLIENT_ID=YOUR_AUTH0_API_CLIENT_ID
AUTH0_CLIENT_SECRET=YOUR_AUTH0_API_CLIENT_SECRET
```

**Variable Details:**
- **`AUTH0_DOMAIN`**: Same as frontend `REACT_APP_AUTH0_DOMAIN`
- **`AUTH0_API_AUDIENCE`**: Same as frontend `REACT_APP_AUTH0_AUDIENCE`
- **`AUTH0_CLIENT_ID`**: Client ID for your Auth0 API
  - Find in: Auth0 Dashboard → Applications → APIs → (Your API Name) → Client ID
- **`AUTH0_CLIENT_SECRET`**: Client Secret for your Auth0 API ⚠️ **Keep Secret**
  - Find in: Auth0 Dashboard → Applications → APIs → (Your API Name) → Client Secret

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

### Application Settings (Single Page Application)
- **Application Type**: Single Page Application (SPA)
- **Allowed Callback URLs**: `http://localhost:3000`
- **Allowed Logout URLs**: `http://localhost:3000`
- **Allowed Web Origins**: `http://localhost:3000`
- **Allowed Origins (CORS)**: `http://localhost:3000`

### API Settings
- **Identifier**: `https://your-api-identifier` (use in `REACT_APP_AUTH0_AUDIENCE`)
- **Signing Algorithm**: RS256
- **Allow Skipping User Consent**: Yes (for development)
- **Token Expiration**: Configure as needed (default: 24 hours)

### Important Auth0 Setup Notes

**Token Type Configuration:**
- The backend expects **signed Access Tokens (JWS)**, not encrypted ones (JWE)
- Including the `audience` parameter in frontend configuration ensures correct token type
- If you see `alg: 'dir'` errors, it indicates an encrypted token - verify audience configuration

**Troubleshooting Auth0:**
- Always clear browser cookies and local storage when troubleshooting
- Verify all URLs in Auth0 dashboard match your local development setup
- Restart backend server after any `.env` changes
- Check Auth0 dashboard logs for detailed error information

## 🎨 Frontend Architecture & Material-UI Integration

### Technology Stack
- **React**: Single Page Application (SPA) architecture
- **Material-UI (MUI)**: Complete UI component library replacing Tailwind CSS
- **Auth0 React SDK**: Authentication integration with token management
- **Axios**: HTTP client with Auth0 token injection

### Key Components

#### Core Application (`web/frontend/src/index.js`)
```javascript
// Auth0Provider with audience parameter for API access
<Auth0Provider
  domain={process.env.REACT_APP_AUTH0_DOMAIN}
  clientId={process.env.REACT_APP_AUTH0_CLIENT_ID}
  authorizationParams={{
    redirect_uri: window.location.origin,
    audience: process.env.REACT_APP_AUTH0_AUDIENCE, // Critical for API tokens
  }}
>
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <App />
  </ThemeProvider>
</Auth0Provider>
```

#### Material-UI Theme Integration
- **Global Theme**: Consistent color palette and typography
- **CssBaseline**: Normalized browser styles
- **Responsive Design**: Mobile-first approach with MUI breakpoints
- **Custom Styled Components**: `StyledPaper`, `ResultBox` for consistent styling

#### Authentication Hook (`web/frontend/src/hooks/useApiClient.ts`)
```typescript
// Custom hook providing API client with Auth0 token injection
const useApiClient = () => {
  const { getAccessTokenSilently } = useAuth0();
  
  return useMemo(() => new ApiClient(getAccessTokenSilently), [getAccessTokenSilently]);
};
```

### Component Architecture

#### Refactored Components (Tailwind → MUI)
- **`App.js`**: Main layout using `AppBar`, `Toolbar`, `Container`, `Tabs`
- **`CryptoAnalysis.tsx`**: Form components using `TextField`, `Select`, `FormControl`
- **`BacktestRunner.tsx`**: Complex forms with `Grid`, `Paper`, `Alert` components
- **`HealthStatus.tsx`**: Status display with `CircularProgress`, `Typography`
- **Auth Components**: `LoginButton`, `LogoutButton` using MUI `Button` variants

#### Styling Approach
- **MUI `sx` prop**: Replaces Tailwind classes for component-level styling
- **Theme-based colors**: Consistent color scheme across components
- **Responsive utilities**: MUI breakpoint system for mobile compatibility
- **No custom CSS**: All styling through MUI's theming system

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
- **Auth0 Authentication**: Secure login/logout with proper token management
- **Material-UI Design System**: Complete UI overhaul from Tailwind to MUI
- **Crypto Analysis Interface**: Run analysis with strategy selection
- **Backtest Runner**: Configure and run backtests
- **Real-time Health Monitoring**: System status display
- **Responsive Design**: Mobile-first approach with MUI breakpoints
- **Form Validation**: Client and server-side validation
- **Error Handling**: Comprehensive error management with proper Auth0 integration
- **Result Storage**: Local JSON file storage
- **API Integration**: RESTful API with Auth0 token injection
- **Custom React Hooks**: `useApiClient` for seamless API authentication

### 🔄 CLI Integration Status
- **Core Logic**: Uses shared core module
- **Strategy Configs**: Imports from existing config.py
- **Result Compatibility**: Saves in same format as CLI
- **Data Sources**: Uses same data fetching logic
- **Material-UI Integration**: Complete frontend redesign for better UX
- **Enhanced Auth0**: Proper SPA configuration with API audience

**Note**: Frontend now uses Material-UI instead of Tailwind CSS for better platform compatibility and consistent theming. All Auth0 integration issues have been resolved with proper token handling.

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
2. **Frontend**: Add MUI-based component in `web/frontend/src/components/`
3. **Types**: Update TypeScript interfaces if using TypeScript
4. **API Client**: Update `web/frontend/src/utils/api.ts`
5. **Authentication**: Use `useApiClient` hook for authenticated requests

### Debugging
- **Backend Logs**: Check `data/logs/backend.log`
- **Frontend Console**: Browser developer tools
- **API Testing**: Use curl with Auth0 tokens or Postman
- **Auth Issues**: Check Auth0 dashboard logs and verify environment variables
- **MUI Theme Issues**: Check browser console for theme-related errors

## 📊 Data Flow

```
Frontend (React SPA) 
    ↓ Auth0 Access Token (with audience)
Backend (Flask API)
    ↓ Validates JWT Token (RS256)
Core Trading Engine
    ↓ Uses Existing CLI Logic
Result Manager
    ↓ Saves to JSON
Local File Storage
```

## 🛡️ Security Features

- **Auth0 JWT Validation**: All API endpoints protected with proper RS256 validation
- **SPA Token Management**: Secure token storage and automatic refresh
- **CORS Configuration**: Restricted to frontend origin
- **Input Validation**: Server-side parameter validation
- **Error Sanitization**: No sensitive data in error responses
- **Audience Validation**: API tokens scoped to specific backend audience
- **Secure Token Exchange**: Proper Auth0 SPA → API token flow

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
# or serve the build directory with a static server
```

### Environment Variables
Update URLs and configuration for production:
- **Frontend**: Update `REACT_APP_AUTH0_DOMAIN`, `REACT_APP_AUTH0_CLIENT_ID`, `REACT_APP_AUTH0_AUDIENCE`
- **Backend**: Update `AUTH0_DOMAIN`, `AUTH0_API_AUDIENCE`, and other Auth0 credentials
- **CORS Settings**: Update allowed origins in backend configuration
- **Auth0 Dashboard**: Update callback URLs, web origins, and logout URLs for production domain

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
- Check Auth0 SPA configuration (not Regular Web Application)
- Verify callback URLs match exactly: `http://localhost:3000`
- Ensure `REACT_APP_AUTH0_AUDIENCE` is set correctly
- Clear browser cookies and local storage
- Check Auth0 dashboard logs for detailed errors

**Backend API Errors**
- Verify backend server is running on correct port
- Check Auth0 API configuration and audience settings
- Ensure backend `.env` file has correct Auth0 credentials
- Check backend logs for JWT validation errors
- Restart backend server after `.env` changes

**Frontend Build/Runtime Errors**
- Run `npm install` to update dependencies
- Check for MUI theme-related errors in console
- Verify all environment variables are set
- Ensure `useApiClient` hook is used for API calls
- Check for missing MUI component imports

**Token/Authentication Issues**
- Verify `audience` parameter is included in Auth0Provider
- Check that backend expects signed (JWS) not encrypted (JWE) tokens
- Clear Auth0 session: logout and clear browser storage
- Verify API identifier matches between frontend and backend config

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

## 🔄 Recent Updates & Improvements

### Frontend Refactoring (Tailwind → Material-UI)
**Completed**: Complete migration from Tailwind CSS to Material-UI (MUI)

**Reasoning**: Platform compatibility issues with Tailwind (Rust dependency) led to adoption of MUI for better stability and consistent theming.

**Key Changes**:
- All components refactored to use MUI components (`Button`, `TextField`, `AppBar`, etc.)
- Replaced Tailwind `className` with MUI `sx` prop styling
- Implemented global MUI theme with `ThemeProvider` and `CssBaseline`
- Created custom styled components (`StyledPaper`, `ResultBox`) for consistency
- Removed all custom CSS files in favor of MUI's theming system

### Auth0 Integration Fixes
**Completed**: Resolved all Auth0 authentication and token validation issues

**Frontend Improvements**:
- Added `audience` parameter to `Auth0Provider` for proper API token requests
- Created `useApiClient` custom hook for seamless token injection
- Updated all components to use authenticated API client
- Fixed import path issues and module resolution

**Backend Improvements**:
- Fixed JWT token validation to handle signed tokens (JWS) correctly
- Improved error handling in `requires_auth` decorator
- Enhanced logging for better debugging
- Resolved `TypeError: Object of type Response is not JSON serializable` issues

**Configuration Updates**:
- Simplified environment variable setup with clear documentation
- Added troubleshooting guide for common Auth0 issues
- Updated Auth0 application type to Single Page Application (SPA)

### Architecture Improvements
- **Token Flow**: Proper SPA → API token exchange with audience validation
- **Error Handling**: Comprehensive error management across frontend and backend
- **Development Experience**: Better debugging tools and clearer setup instructions
- **Security**: Enhanced JWT validation and proper CORS configuration

---

## 🎉 Success!

You now have a complete web application that:
- ✅ **Preserves CLI functionality** - All existing tools still work
- ✅ **Modern Material-UI interface** - Responsive, accessible, and consistent design
- ✅ **Secure Auth0 authentication** - Proper SPA integration with API token management
- ✅ **Shared core logic** - No code duplication
- ✅ **Robust error handling** - Comprehensive debugging and troubleshooting
- ✅ **Easy to restart** - Comprehensive documentation and setup scripts
- ✅ **Production ready** - Proper security, validation, and deployment guidance

**Ready for development and testing!** 🚀
