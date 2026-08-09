import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Skeleton,
  Alert,
  Grid,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faStore } from '@fortawesome/free-solid-svg-icons';
import { PageContainer } from '../components/layout/PageContainer';
import { OutletHealthList } from '../components/outlets/OutletHealthList';
import type { Restaurant, Incident } from '../types/api';

interface OutletsPageProps {
  restaurants: Restaurant[];
  incidents: Incident[];
  loading: boolean;
  error: string | null;
}

export const OutletsPage: React.FC<OutletsPageProps> = ({
  restaurants,
  incidents,
  loading,
  error,
}) => {
  return (
    <PageContainer>
      <Box sx={{ mb: 3 }}>
        <Typography variant="overline" sx={{ color: 'text.secondary' }}>
          Operations
        </Typography>
        <Typography variant="h1" sx={{ mt: 0.25 }}>
          Outlets
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
          {loading ? 'Loading\u2026' : `${restaurants.length} outlet${restaurants.length !== 1 ? 's' : ''} monitored`}
        </Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Grid container spacing={2}>
          {[1, 2, 3].map(i => (
            <Grid key={i} size={{ xs: 12, md: 6 }}>
              <Skeleton variant="rectangular" height={100} sx={{ borderRadius: 2 }} />
            </Grid>
          ))}
        </Grid>
      ) : restaurants.length === 0 ? (
        <Paper sx={{ p: 5, textAlign: 'center' }}>
          <FontAwesomeIcon icon={faStore} style={{ fontSize: 28, color: '#868E96', marginBottom: 12 }} />
          <Typography variant="body1" sx={{ color: 'text.secondary', mt: 1.5 }}>
            No outlets registered yet. Start a demo scenario to provision outlets.
          </Typography>
        </Paper>
      ) : (
        <Box>
          <OutletHealthList
            restaurants={restaurants}
            incidents={incidents}
            loading={loading}
          />
        </Box>
      )}
    </PageContainer>
  );
};
