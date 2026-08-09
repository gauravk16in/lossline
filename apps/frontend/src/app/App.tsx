import React from 'react';
import { ThemeProvider, CssBaseline, Box } from '@mui/material';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import theme from './theme';
import { Sidebar } from '../components/layout/Sidebar';
import { OverviewPage } from '../pages/OverviewPage';
import { ForecastsPage } from '../pages/ForecastsPage';
import { RisksPage } from '../pages/RisksPage';
import { DecisionsPage } from '../pages/DecisionsPage';
import '../styles.css';
import { DashboardProvider } from '../state/DashboardContext';
import { OrganizationSwitcher, SignIn, SignedIn, SignedOut, UserButton, useAuth } from '@clerk/react';
import { setSessionTokenProvider } from '../api/client';
import { useEffect } from 'react';

/**
 * AppShell — wraps sidebar + routed content.
 * Four screens implemented: Overview, Forecasts, Risks, Decisions.
 */
function AppShell() {
  return (
    <Box
      sx={{
        display: 'flex',
        minHeight: '100vh',
        backgroundColor: 'background.default',
      }}
    >
      <Sidebar />
      <Box
        component="main"
        sx={{
          flex: 1,
          overflow: 'auto',
          minWidth: 0,
        }}
      >
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/forecasts" element={<ForecastsPage />} />
          <Route path="/risks" element={<RisksPage />} />
          <Route path="/decisions" element={<DecisionsPage />} />
          <Route path="*" element={<OverviewPage />} />
          {/* Future routes:
            <Route path="/outlets"   element={<OutletsPage />} />
            <Route path="/settings"  element={<SettingsPage />} />
          */}
        </Routes>
      </Box>
    </Box>
  );
}

function AuthenticatedApp() {
  const { getToken } = useAuth();
  useEffect(() => { setSessionTokenProvider(getToken); }, [getToken]);
  return <>
    <SignedOut><Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}><SignIn /></Box></SignedOut>
    <SignedIn>
      <Box sx={{ position: 'fixed', zIndex: 1400, top: 14, right: 18, display: 'flex', gap: 1, alignItems: 'center' }}>
        <OrganizationSwitcher hidePersonal afterSelectOrganizationUrl="/" /><UserButton />
      </Box>
      <DashboardProvider><AppShell /></DashboardProvider>
    </SignedIn>
  </>;
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthenticatedApp />
      </BrowserRouter>
    </ThemeProvider>
  );
}
