import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    background: {
      default: '#F7F7F8',
      paper: '#FFFFFF',
    },
    primary: {
      main: '#3B5BDB',
      light: '#748FFC',
      dark: '#2F49B5',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#495057',
      light: '#868E96',
      dark: '#343A40',
    },
    error: {
      main: '#E03131',
      light: '#FF6B6B',
      dark: '#C92A2A',
    },
    warning: {
      main: '#F59F00',
      light: '#FFD43B',
      dark: '#E67700',
    },
    success: {
      main: '#2F9E44',
      light: '#69DB7C',
      dark: '#237032',
    },
    text: {
      primary: '#1C1B1F',
      secondary: '#49454F',
      disabled: '#79747E',
    },
    divider: 'rgba(0,0,0,0.08)',
  },
  typography: {
    fontFamily: '"Inter", "Roboto", system-ui, -apple-system, sans-serif',
    h1: {
      fontSize: '1.75rem',
      fontWeight: 600,
      letterSpacing: '-0.02em',
      lineHeight: 1.3,
    },
    h2: {
      fontSize: '1.25rem',
      fontWeight: 600,
      letterSpacing: '-0.01em',
      lineHeight: 1.4,
    },
    h3: {
      fontSize: '1rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: '0.875rem',
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
      color: '#79747E',
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
    '0px 1px 3px rgba(0,0,0,0.06), 0px 1px 2px rgba(0,0,0,0.04)',
    '0px 2px 6px rgba(0,0,0,0.06), 0px 1px 3px rgba(0,0,0,0.04)',
    '0px 4px 12px rgba(0,0,0,0.06)',
    '0px 6px 16px rgba(0,0,0,0.07)',
    '0px 8px 24px rgba(0,0,0,0.08)',
    '0px 10px 28px rgba(0,0,0,0.08)',
    '0px 12px 32px rgba(0,0,0,0.09)',
    '0px 14px 36px rgba(0,0,0,0.09)',
    '0px 16px 40px rgba(0,0,0,0.10)',
    '0px 18px 44px rgba(0,0,0,0.10)',
    '0px 20px 48px rgba(0,0,0,0.11)',
    '0px 22px 52px rgba(0,0,0,0.11)',
    '0px 24px 56px rgba(0,0,0,0.12)',
    '0px 26px 60px rgba(0,0,0,0.12)',
    '0px 28px 64px rgba(0,0,0,0.12)',
    '0px 30px 68px rgba(0,0,0,0.13)',
    '0px 32px 72px rgba(0,0,0,0.13)',
    '0px 34px 76px rgba(0,0,0,0.14)',
    '0px 36px 80px rgba(0,0,0,0.14)',
    '0px 38px 84px rgba(0,0,0,0.14)',
    '0px 40px 88px rgba(0,0,0,0.15)',
    '0px 42px 92px rgba(0,0,0,0.15)',
    '0px 44px 96px rgba(0,0,0,0.15)',
    '0px 46px 100px rgba(0,0,0,0.15)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; }
        body { background-color: #F7F7F8; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 3px; }
      `,
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(0,0,0,0.06)',
          transition: 'box-shadow 150ms ease',
        },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(0,0,0,0.06)',
        },
        outlined: {
          border: '1px solid rgba(0,0,0,0.08)',
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
          '&:hover': { transform: 'translateY(-1px)', boxShadow: '0px 4px 12px rgba(59,91,219,0.25)' },
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
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          height: 6,
          backgroundColor: 'rgba(0,0,0,0.06)',
        },
      },
    },
    MuiListItem: {
      styleOverrides: {
        root: { paddingTop: 6, paddingBottom: 6 },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: { borderColor: 'rgba(0,0,0,0.06)' },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 12 },
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
