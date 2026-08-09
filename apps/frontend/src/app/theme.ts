import { createTheme } from '@mui/material/styles';

/**
 * LOSSLine dark theme — palette matched to the overview-section.png design.
 *
 * Background hierarchy:
 *   #0B0F1A  (default)  → page bg
 *   #111631  (paper)    → card surfaces
 *   #0E1225  (sidebar)  → sidebar bg (used directly)
 *
 * Accent:
 *   primary  → indigo/violet  #7C5CFC
 *   secondary → slate muted   #495057
 */
const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: '#0B0F1A',
      paper: '#111631',
    },
    primary: {
      main: '#7C5CFC',
      light: '#A78BFA',
      dark: '#5B3FD9',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#495057',
      light: '#868E96',
      dark: '#343A40',
    },
    error: {
      main: '#EF4444',
      light: '#F87171',
      dark: '#DC2626',
    },
    warning: {
      main: '#F59E0B',
      light: '#FBBF24',
      dark: '#D97706',
    },
    success: {
      main: '#22C55E',
      light: '#4ADE80',
      dark: '#16A34A',
    },
    text: {
      primary: '#F4F7FB',
      secondary: '#8B95A8',
      disabled: '#525C6C',
    },
    divider: 'rgba(255, 255, 255, 0.06)',
  },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
    h1: {
      fontSize: '1.5rem',
      fontWeight: 600,
      letterSpacing: '-0.02em',
      lineHeight: 1.3,
    },
    h2: {
      fontSize: '1.125rem',
      fontWeight: 600,
      letterSpacing: '-0.01em',
      lineHeight: 1.4,
    },
    h3: {
      fontSize: '0.9375rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: '0.8125rem',
      fontWeight: 600,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '0.875rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.8125rem',
      lineHeight: 1.5,
    },
    caption: {
      fontSize: '0.75rem',
      lineHeight: 1.4,
      color: '#8B95A8',
    },
    overline: {
      fontSize: '0.6875rem',
      fontWeight: 600,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      lineHeight: 1.4,
    },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0px 1px 3px rgba(0,0,0,0.12)',
    '0px 2px 6px rgba(0,0,0,0.12)',
    '0px 4px 12px rgba(0,0,0,0.14)',
    '0px 6px 16px rgba(0,0,0,0.16)',
    '0px 8px 24px rgba(0,0,0,0.18)',
    '0px 10px 28px rgba(0,0,0,0.18)',
    '0px 12px 32px rgba(0,0,0,0.20)',
    '0px 14px 36px rgba(0,0,0,0.20)',
    '0px 16px 40px rgba(0,0,0,0.22)',
    '0px 18px 44px rgba(0,0,0,0.22)',
    '0px 20px 48px rgba(0,0,0,0.24)',
    '0px 22px 52px rgba(0,0,0,0.24)',
    '0px 24px 56px rgba(0,0,0,0.24)',
    '0px 26px 60px rgba(0,0,0,0.24)',
    '0px 28px 64px rgba(0,0,0,0.24)',
    '0px 30px 68px rgba(0,0,0,0.24)',
    '0px 32px 72px rgba(0,0,0,0.24)',
    '0px 34px 76px rgba(0,0,0,0.24)',
    '0px 36px 80px rgba(0,0,0,0.24)',
    '0px 38px 84px rgba(0,0,0,0.24)',
    '0px 40px 88px rgba(0,0,0,0.24)',
    '0px 42px 92px rgba(0,0,0,0.24)',
    '0px 44px 96px rgba(0,0,0,0.24)',
    '0px 46px 100px rgba(0,0,0,0.24)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        * { box-sizing: border-box; }
        body {
          background: radial-gradient(ellipse at 80% 0%, rgba(124,92,252,0.07), transparent 40%), #0B0F1A;
        }
      `,
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(255,255,255,0.06)',
          transition: 'box-shadow 150ms ease',
        },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(255,255,255,0.06)',
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 10,
          textTransform: 'none',
          fontWeight: 500,
          fontSize: '0.875rem',
          padding: '8px 18px',
          transition: 'all 150ms ease',
        },
        contained: {
          '&:hover': {
            transform: 'translateY(-1px)',
            boxShadow: '0px 4px 16px rgba(124,92,252,0.3)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
          fontSize: '0.75rem',
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: { borderColor: 'rgba(255,255,255,0.06)' },
      },
    },
    MuiSkeleton: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
  },
});

export default theme;
