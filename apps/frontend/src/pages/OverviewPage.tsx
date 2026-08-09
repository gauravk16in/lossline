import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  Skeleton,
  Alert,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faTriangleExclamation,
  faIndianRupeeSign,
  faStore,
  faCircleCheck,
} from '@fortawesome/free-solid-svg-icons';
import { PageContainer } from '../components/layout/PageContainer';
import { IncidentCard } from '../components/incidents/IncidentCard';
import { OutletHealthList } from '../components/outlets/OutletHealthList';
import type { Incident, AnalyticsSummary, Restaurant } from '../types/api';
import { ConnectionBadge } from '../components/common/ConnectionBadge';

interface KpiCardProps {
  label: string;
  value: string | number;
  icon: typeof faTriangleExclamation;
  iconColor: string;
  iconBg: string;
  loading?: boolean;
}

function KpiCard({ label, value, icon, iconColor, iconBg, loading }: KpiCardProps) {
  return (
    <Paper sx={{ p: 2.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
        <Box
          sx={{
            width: 36,
            height: 36,
            borderRadius: '10px',
            backgroundColor: iconBg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <FontAwesomeIcon icon={icon} style={{ fontSize: 14, color: iconColor }} />
        </Box>
        <Box>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.25 }}>
            {label}
          </Typography>
          {loading ? (
            <Skeleton width={48} height={28} />
          ) : (
            <Typography
              sx={{
                fontSize: '1.5rem',
                fontWeight: 700,
                lineHeight: 1,
                color: 'text.primary',
                letterSpacing: '-0.02em',
              }}
            >
              {value}
            </Typography>
          )}
        </Box>
      </Box>
    </Paper>
  );
}

interface OverviewPageProps {
  incidents: Incident[];
  summary: AnalyticsSummary | null;
  restaurants: Restaurant[];
  loading: boolean;
  error: string | null;
  connectionStatus: 'connecting' | 'live' | 'reconnecting';
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  incidents,
  summary,
  restaurants,
  loading,
  error,
  connectionStatus,
}) => {
  const activeIncidents = incidents.filter(
    inc => !['RESOLVED', 'ACTION_REJECTED'].includes(inc.status)
  );

  return (
    <PageContainer>
      {/* Page header */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="overline" sx={{ color: 'text.secondary' }}>
            LOSSLine
          </Typography>
          <Typography variant="h1" sx={{ mt: 0.25 }}>
            Operational Intelligence
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Synthetic live scenario · Meghana Indiranagar
          </Typography>
        </Box>
        <Box sx={{ mt: 0.5 }}>
          <ConnectionBadge status={connectionStatus} />
        </Box>
      </Box>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* KPI row */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KpiCard
            label="Active incidents"
            value={loading ? '—' : summary?.active_incident_count ?? 0}
            icon={faTriangleExclamation}
            iconColor={summary?.active_incident_count ? '#E03131' : '#2F9E44'}
            iconBg={summary?.active_incident_count ? '#FFF5F5' : '#EBFBEE'}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KpiCard
            label="Revenue at risk"
            value={
              loading
                ? '—'
                : summary?.estimated_exposure
                ? `\u20B9${Math.round(summary.estimated_exposure).toLocaleString('en-IN')}`
                : '\u20B90'
            }
            icon={faIndianRupeeSign}
            iconColor={summary?.estimated_exposure ? '#C92A2A' : '#2F9E44'}
            iconBg={summary?.estimated_exposure ? '#FFF5F5' : '#EBFBEE'}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KpiCard
            label="Outlets monitoring"
            value={loading ? '—' : restaurants.length}
            icon={faStore}
            iconColor="#1864AB"
            iconBg="#E7F5FF"
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KpiCard
            label="Resolved today"
            value={loading ? '—' : summary?.resolved_incident_count ?? 0}
            icon={faCircleCheck}
            iconColor="#2F9E44"
            iconBg="#EBFBEE"
            loading={loading}
          />
        </Grid>
      </Grid>

      {/* Main content: two-column layout */}
      <Grid container spacing={3}>
        {/* Left: Incidents needing attention */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h2">
              Needs attention
            </Typography>
            {activeIncidents.length > 0 && (
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                {activeIncidents.length} incident{activeIncidents.length > 1 ? 's' : ''}
              </Typography>
            )}
          </Box>

          {loading ? (
            <>
              <Skeleton variant="rectangular" height={140} sx={{ borderRadius: 2, mb: 1.5 }} />
              <Skeleton variant="rectangular" height={140} sx={{ borderRadius: 2 }} />
            </>
          ) : activeIncidents.length === 0 ? (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <FontAwesomeIcon icon={faCircleCheck} style={{ fontSize: 28, color: '#2F9E44', marginBottom: 12 }} />
              <Typography variant="body1" sx={{ color: 'text.secondary', mt: 1.5 }}>
                All outlets operating normally.
              </Typography>
            </Paper>
          ) : (
            activeIncidents.map(inc => (
              <IncidentCard key={inc.id} incident={inc} />
            ))
          )}
        </Grid>

        {/* Right: Outlet health */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Typography variant="h2" sx={{ mb: 2 }}>
            Outlet health
          </Typography>
          <OutletHealthList
            restaurants={restaurants}
            incidents={incidents}
            loading={loading}
          />
        </Grid>
      </Grid>
    </PageContainer>
  );
};
