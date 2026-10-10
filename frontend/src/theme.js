import { createTheme, alpha } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary:    { main: '#6366f1', light: '#818cf8', dark: '#4f46e5' },
    secondary:  { main: '#06b6d4' },
    error:      { main: '#f87171' },
    warning:    { main: '#fbbf24' },
    success:    { main: '#34d399' },
    info:       { main: '#60a5fa' },
    background: { default: '#060c18', paper: '#0b1929' },
    text:       { primary: '#e2e8f0', secondary: '#94a3b8' },
    divider:    'rgba(148,163,184,0.1)',
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: '"Inter","Roboto","Helvetica Neue",sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 500 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        body { scrollbar-width: thin; scrollbar-color: #1e293b transparent; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
      `,
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          background: 'rgba(11,25,41,0.8)',
          border: '1px solid rgba(148,163,184,0.08)',
          backdropFilter: 'blur(12px)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundImage: 'none',
          background: 'rgba(6,12,24,0.92)',
          backdropFilter: 'blur(24px)',
          borderRight: '1px solid rgba(148,163,184,0.08)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          background: 'rgba(6,12,24,0.85)',
          backdropFilter: 'blur(24px)',
          borderBottom: '1px solid rgba(148,163,184,0.08)',
          boxShadow: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 8, fontWeight: 600, textTransform: 'none' },
        contained: {
          boxShadow: 'none',
          '&:hover': { boxShadow: '0 4px 20px rgba(99,102,241,0.35)' },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 6, fontWeight: 700, fontSize: '0.68rem' },
      },
    },
    MuiTextField: {
      defaultProps: { size: 'small' },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
            '& fieldset': { borderColor: 'rgba(148,163,184,0.18)' },
            '&:hover fieldset': { borderColor: 'rgba(148,163,184,0.35)' },
          },
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          mx: 1,
          '&.Mui-selected': {
            background: 'rgba(99,102,241,0.15)',
            '&:hover': { background: 'rgba(99,102,241,0.22)' },
          },
        },
      },
    },
    MuiTab: {
      styleOverrides: { root: { textTransform: 'none', fontWeight: 600, minWidth: 'auto' } },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderBottom: '1px solid rgba(148,163,184,0.08)' },
        head: { fontWeight: 700, color: '#94a3b8', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.08em' },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundImage: 'none',
          background: '#0d1f35',
          border: '1px solid rgba(148,163,184,0.1)',
          backdropFilter: 'blur(24px)',
        },
      },
    },
  },
});
