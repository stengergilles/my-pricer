import React from 'react';
import { Box, Typography, AppBar, Toolbar, IconButton, Container, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import MenuIcon from '@mui/icons-material/Menu';
import LogoutIcon from '@mui/icons-material/Logout';
import { APP_TITLE } from './utils/constants.ts';
import { HealthStatus } from './components/HealthStatus.tsx';

const HeaderContent = ({ user, logout, handleDrawerToggle }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <AppBar position="static" color="default" elevation={1}>
      <Toolbar>
        <Container maxWidth="xl" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}> {/* Left side: Title and Welcome message */}
            <Box>
              <Typography variant="h5" component="h1" sx={{ fontWeight: 'bold', color: 'text.primary' }}>
                {APP_TITLE}
              </Typography>
              <Typography variant="body2" color="text.secondary" >
                Welcome back, {user.name}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: 'center', gap: 2 }}> {/* Right side: HealthStatus, LogoutIcon, and mobile hamburger */}
            <HealthStatus />
            <IconButton
              color="inherit"
              onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
              aria-label="logout"
            >
              <LogoutIcon />
            </IconButton>
            {isMobile && (
              <IconButton
                color="inherit"
                aria-label="open drawer"
                edge="start"
                onClick={handleDrawerToggle}
              >
                <MenuIcon />
              </IconButton>
            )}
          </Box>
        </Container>
      </Toolbar>
    </AppBar>
  );
};

export default HeaderContent;