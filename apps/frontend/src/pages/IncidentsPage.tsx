import React, { useState } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Skeleton,
  Alert,
  Paper,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCircleCheck } from '@fortawesome/free-solid-svg-icons';
import { PageContainer } from '../components/layout/PageContainer';
import { IncidentCard } from '../components/incidents/IncidentCard';
import type { Incident } from '../types/api';

interface IncidentsPageProps {
  incidents: Incident[];
  loading: boolean;
  error: string | null;
}

const FILTERS = [
  { label: 'All', value: null },
  { label: 'Awaiting approval', value: 'AWAITING_APPROVAL' },
  { label: 'Approved', value: 'ACTION_APPROVED' },
  { label: 'Resolved', value: 'RESOLVED' },
  { label: 'Rejected', value: 'ACTION_REJECTED' },
] as const;

export const IncidentsPage: React.FC<IncidentsPageProps> = ({
  incidents,
  loading,
  error,
}) => {
  const [filterIdx, setFilterIdx] = useState(0);
  const currentFilter = FILTERS[filterIdx].value;

  const filtered = currentFilter
    ? incidents.filter(i => i.status === currentFilter)
    : incidents;

  return (
    <PageContainer>
      <Box sx={{ mb: 3 }}>
        <Typography variant="overline" sx={{ color: 'text.secondary' }}>
          Intelligence
        </Typography>
        <Typography variant="h1" sx={{ mt: 0.25 }}>
          Incidents
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
          All detected operational anomalies and their status
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Filter tabs */}
      <Box sx={{ mb: 3, borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
        <Tabs
          value={filterIdx}
          onChange={(_, v: number) => setFilterIdx(v)}
          sx={{
            minHeight: 40,
            '& .MuiTab-root': {
              fontSize: '0.8125rem',
              fontWeight: 500,
              minHeight: 40,
              textTransform: 'none',
              color: 'text.secondary',
              px: 2,
              '&.Mui-selected': { color: 'primary.main', fontWeight: 600 },
            },
            '& .MuiTabs-indicator': {
              height: 2,
              borderRadius: '2px 2px 0 0',
            },
          }}
        >
          {FILTERS.map((f, i) => (
            <Tab
              key={i}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  {f.label}
                  {f.value === null
                    ? incidents.length > 0 && (
                        <Box
                          sx={{
                            minWidth: 18,
                            height: 18,
                            borderRadius: 9,
                            bgcolor: 'rgba(0,0,0,0.08)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            px: 0.5,
                          }}
                        >
                          <Typography sx={{ fontSize: '0.625rem', fontWeight: 700, color: 'text.secondary' }}>
                            {incidents.length}
                          </Typography>
                        </Box>
                      )
                    : null}
                </Box>
              }
            />
          ))}
        </Tabs>
      </Box>

      {loading ? (
        <>
          <Skeleton variant="rectangular" height={150} sx={{ borderRadius: 2, mb: 1.5 }} />
          <Skeleton variant="rectangular" height={150} sx={{ borderRadius: 2 }} />
        </>
      ) : filtered.length === 0 ? (
        <Paper sx={{ p: 5, textAlign: 'center' }}>
          <FontAwesomeIcon icon={faCircleCheck} style={{ fontSize: 28, color: '#2F9E44', marginBottom: 12 }} />
          <Typography variant="body1" sx={{ color: 'text.secondary', mt: 1.5 }}>
            {currentFilter ? `No incidents with status "${FILTERS[filterIdx].label}".` : 'No incidents detected yet.'}
          </Typography>
        </Paper>
      ) : (
        filtered.map(inc => <IncidentCard key={inc.id} incident={inc} />)
      )}
    </PageContainer>
  );
};
