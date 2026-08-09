import React, { useState, useEffect, useCallback } from 'react';
import { ThemeProvider, CssBaseline, Box } from '@mui/material';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import theme from './theme';
import { Sidebar } from '../components/layout/Sidebar';
import { OverviewPage } from '../pages/OverviewPage';
import { IncidentsPage } from '../pages/IncidentsPage';
import { IncidentDetailPage } from '../pages/IncidentDetailPage';
import { OutletsPage } from '../pages/OutletsPage';
import { ActionsPage } from '../pages/ActionsPage';
import { useIncidents } from '../hooks/useIncidents';
import { useRealtime } from '../hooks/useRealtime';
import { api } from '../api/client';
import type { Restaurant } from '../types/api';

function AppShell() {
  const { incidents, summary, loading, error, refresh } = useIncidents();
  const { status: connectionStatus } = useRealtime(refresh);
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [restaurantsLoading, setRestaurantsLoading] = useState(true);

  const loadRestaurants = useCallback(async () => {
    try {
      const list = await api.getRestaurants();
      setRestaurants(list);
    } catch {
      // Non-fatal
    } finally {
      setRestaurantsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRestaurants();
    // Refresh restaurants every 30s for auto-provisioned outlets
    const timer = window.setInterval(loadRestaurants, 30000);
    return () => clearInterval(timer);
  }, [loadRestaurants]);

  const activeCount = summary?.active_incident_count ?? 0;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: 'background.default' }}>
      <Sidebar
        activeIncidentCount={activeCount}
        connectionStatus={connectionStatus}
      />
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <Routes>
          <Route
            path="/"
            element={
              <OverviewPage
                incidents={incidents}
                summary={summary}
                restaurants={restaurants}
                loading={loading || restaurantsLoading}
                error={error}
                connectionStatus={connectionStatus}
              />
            }
          />
          <Route
            path="/incidents"
            element={
              <IncidentsPage
                incidents={incidents}
                loading={loading}
                error={error}
              />
            }
          />
          <Route path="/incidents/:id" element={<IncidentDetailPage />} />
          <Route
            path="/outlets"
            element={
              <OutletsPage
                restaurants={restaurants}
                incidents={incidents}
                loading={restaurantsLoading}
                error={error}
              />
            }
          />
          <Route
            path="/actions"
            element={
              <ActionsPage
                incidents={incidents}
                loading={loading}
              />
            }
          />
        </Routes>
      </Box>
    </Box>
  );
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </ThemeProvider>
  );
}
