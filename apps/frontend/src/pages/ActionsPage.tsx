import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Divider,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheck, faCircleCheck } from '@fortawesome/free-solid-svg-icons';
import { PageContainer } from '../components/layout/PageContainer';
import { IncidentCard } from '../components/incidents/IncidentCard';
import type { Incident } from '../types/api';

interface ActionsPageProps {
  incidents: Incident[];
  loading: boolean;
}

export const ActionsPage: React.FC<ActionsPageProps> = ({ incidents, loading }) => {
  const awaitingApproval = incidents.filter(i => i.status === 'AWAITING_APPROVAL');
  const approved = incidents.filter(i => i.status === 'ACTION_APPROVED');
  const resolved = incidents.filter(i => i.status === 'RESOLVED');

  return (
    <PageContainer>
      <Box sx={{ mb: 3 }}>
        <Typography variant="overline" sx={{ color: 'text.secondary' }}>
          Manager
        </Typography>
        <Typography variant="h1" sx={{ mt: 0.25 }}>
          Actions
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
          Incidents requiring or awaiting your decision
        </Typography>
      </Box>

      {/* Awaiting approval */}
      {awaitingApproval.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <FontAwesomeIcon icon={faCheck} style={{ fontSize: 13, color: '#E67700' }} />
            <Typography variant="h2">Awaiting approval</Typography>
            <Box
              sx={{
                minWidth: 20,
                height: 20,
                borderRadius: 10,
                bgcolor: '#FFF9DB',
                border: '1px solid #FFE066',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                px: 0.75,
              }}
            >
              <Typography sx={{ fontSize: '0.625rem', fontWeight: 700, color: '#E67700' }}>
                {awaitingApproval.length}
              </Typography>
            </Box>
          </Box>
          {awaitingApproval.map(inc => <IncidentCard key={inc.id} incident={inc} />)}
        </Box>
      )}

      {/* Approved */}
      {approved.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h2" sx={{ mb: 2 }}>Monitoring</Typography>
          {approved.map(inc => <IncidentCard key={inc.id} incident={inc} />)}
        </Box>
      )}

      {/* Resolved */}
      {resolved.length > 0 && (
        <Box>
          <Divider sx={{ mb: 3 }} />
          <Typography variant="h2" sx={{ mb: 2, color: 'text.secondary' }}>Resolved</Typography>
          {resolved.map(inc => <IncidentCard key={inc.id} incident={inc} />)}
        </Box>
      )}

      {awaitingApproval.length === 0 && approved.length === 0 && !loading && (
        <Paper sx={{ p: 5, textAlign: 'center' }}>
          <FontAwesomeIcon icon={faCircleCheck} style={{ fontSize: 28, color: '#2F9E44', marginBottom: 12 }} />
          <Typography variant="body1" sx={{ color: 'text.secondary', mt: 1.5 }}>
            No pending actions.
          </Typography>
        </Paper>
      )}
    </PageContainer>
  );
};
