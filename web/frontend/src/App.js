import React, { useState, useEffect, Suspense, lazy } from 'react';
import { HashRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Typography, Container, Paper, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import HomeIcon from '@mui/icons-material/Home';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import BarChartIcon from '@mui/icons-material/BarChart';
import ScheduleIcon from '@mui/icons-material/Schedule';

// Import components that were in page.tsx
import { LoginButton } from './components/auth/LoginButton.tsx';
import { useAuth0 } from '@auth0/auth0-react';
import { ApiLoadingProvider } from './contexts/ApiLoadingContext.tsx';
import { ConfigProvider } from './contexts/ConfigContext.tsx';
import { APP_TITLE } from './utils/constants.ts';
import PaperTradingStatus from './components/PaperTradingStatus.tsx';
import HeaderContent from './HeaderContent.js';

const CryptoAnalysis = lazy(() => import('./components/CryptoAnalysis.tsx').then(module => ({ default: module.CryptoAnalysis })));
const BacktestRunner = lazy(() => import('./components/BacktestRunner.tsx').then(module => ({ default: module.BacktestRunner })));
const VolatileCryptoList = lazy(() => import('./components/VolatileCryptoList.tsx').then(module => ({ default: module.VolatileCryptoList })));
const ScheduleTab = lazy(() => import('./components/ScheduleTab.tsx').then(module => ({ default: module.ScheduleTab })));


// Styled components for navigation tabs



function AppContent() {
  const { user, isLoading: auth0Loading, logout } = useAuth0();
  const navigate = useNavigate();
  const theme = useTheme(); // Re-evaluate useTheme here for desktop navigation
  const isMobile = useMediaQuery(theme.breakpoints.down('sm')); // Re-evaluate isMobile here for desktop navigation
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selectedCryptoForBacktest, setSelectedCryptoForBacktest] = useState(null);
  const [backtestResult, setBacktestResult] = useState(null);

  useEffect(() => {
    document.title = APP_TITLE;
  }, []);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleRunBacktest = (cryptoId) => {
    setSelectedCryptoForBacktest(cryptoId);
    navigate('/backtest');
  };

  if (auth0Loading) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <CircularProgress size={80} thickness={5} />
      </Box>
    );
  }

  if (!user) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: (theme) => theme.palette.grey[50],
        }}
      >
        <Container maxWidth="sm">
          <Paper elevation={3} sx={{ padding: 4, textAlign: 'center', borderRadius: 2 }}>
            <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold', color: 'text.primary' }}>
              {APP_TITLE}
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph sx={{ marginBottom: 4 }}>
              Advanced cryptocurrency trading analysis and backtesting platform
            </Typography>
            <LoginButton />
          </Paper>
        </Container>
      </Box>
    );
  }

  const drawer = (
    <Box onClick={handleDrawerToggle} sx={{ textAlign: 'center' }}>
      <Typography variant="h6" sx={{ my: 2 }}>
        {APP_TITLE}
      </Typography>
      <List>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/">
            <ListItemIcon><HomeIcon /></ListItemIcon>
            <ListItemText primary="Paper Trader" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/volatile">
            <ListItemIcon><TrendingUpIcon /></ListItemIcon>
            <ListItemText primary="Volatile Cryptos" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/analysis">
            <ListItemIcon><AnalyticsIcon /></ListItemIcon>
            <ListItemText primary="Analysis" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/backtest">
            <ListItemIcon><BarChartIcon /></ListItemIcon>
            <ListItemText primary="Backtest" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/schedule">
            <ListItemIcon><ScheduleIcon /></ListItemIcon>
            <ListItemText primary="Schedule" />
          </ListItemButton>
        </ListItem>
      </List>
    </Box>
  );

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: (theme) => theme.palette.grey[50] }}>
      <HeaderContent user={user} logout={logout} handleDrawerToggle={handleDrawerToggle} />

      <Drawer
        anchor="bottom"
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: 'block', sm: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', height: 'auto' },
        }}
      >
        {drawer}
      </Drawer>

      {!isMobile && (
        <Box component="nav" sx={{ display: 'block' }}>
          <List sx={{ display: 'flex', flexDirection: 'row', padding: 0 }}>
            <ListItem disablePadding sx={{ width: 'auto' }}>
              <ListItemButton component={Link} to="/">
                <ListItemText primary="Paper Trader" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding sx={{ width: 'auto' }}>
              <ListItemButton component={Link} to="/volatile">
                <ListItemText primary="Volatile Cryptos" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding sx={{ width: 'auto' }}>
              <ListItemButton component={Link} to="/analysis">
                <ListItemText primary="Analysis" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding sx={{ width: 'auto' }}>
              <ListItemButton component={Link} to="/backtest">
                <ListItemText primary="Backtest" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding sx={{ width: 'auto' }}>
              <ListItemButton component={Link} to="/schedule">
                <ListItemText primary="Schedule" />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
      )}

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Box sx={{ p: 2 }}>
          <Suspense fallback={<CircularProgress />}>
            <Routes>
              <Route path="/" element={<ConfigProvider><PaperTradingStatus /></ConfigProvider>} />
              <Route path="/volatile" element={<ConfigProvider><VolatileCryptoList /></ConfigProvider>} />
              <Route path="/analysis" element={<ConfigProvider><CryptoAnalysis onRunBacktest={handleRunBacktest} /></ConfigProvider>} />
              <Route path="/backtest" element={<ConfigProvider><BacktestRunner selectedCrypto={selectedCryptoForBacktest} onSetResult={setBacktestResult} initialResult={backtestResult} /></ConfigProvider>} />
              <Route path="/schedule" element={<ConfigProvider><ScheduleTab /></ConfigProvider>} />
            </Routes>
          </Suspense>
        </Box>
      </Container>
    </Box>
  );
}

function App() {
  return (
    <Router>
      <ApiLoadingProvider>
        <AppContent />
      </ApiLoadingProvider>
    </Router>
  );
}

export default App;