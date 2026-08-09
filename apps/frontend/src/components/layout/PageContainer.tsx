import React from 'react';
import { Box } from '@mui/material';

const SIDEBAR_WIDTH = 220;

interface PageContainerProps {
  children: React.ReactNode;
}

export const PageContainer: React.FC<PageContainerProps> = ({ children }) => (
  <Box
    sx={{
      ml: `${SIDEBAR_WIDTH}px`,
      minHeight: '100vh',
      backgroundColor: 'background.default',
    }}
  >
    <Box
      sx={{
        maxWidth: 1100,
        mx: 'auto',
        px: 4,
        py: 4,
      }}
    >
      {children}
    </Box>
  </Box>
);

export const SIDEBAR_WIDTH_PX = SIDEBAR_WIDTH;
