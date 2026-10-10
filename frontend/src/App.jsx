import { useState, createContext, useContext, useCallback, useEffect } from 'react';
import { ThemeProvider, CssBaseline, Snackbar, Alert } from '@mui/material';
import { theme } from './theme.js';
import Layout from './Layout.jsx';
import Login from './Login.jsx';
import PulumiPage from './pulumi/PulumiPage.jsx';
import { authApi } from './api.js';

export const ToastContext = createContext(null);
export const useToast = () => useContext(ToastContext);
export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function consumeOidcCallback() {
  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash;
  if (!hash.startsWith('oidc=')) return { token: '', username: '', authError: '' };

  const params = new URLSearchParams(hash.slice('oidc='.length));
  const nextToken = params.get('token') || '';
  const nextUsername = params.get('username') || '';
  const authError = params.get('auth_error') || '';

  window.history.replaceState({}, '', `${window.location.pathname}${window.location.search}`);

  if (nextToken) {
    localStorage.setItem('pulumi_token', nextToken);
    if (nextUsername) localStorage.setItem('pulumi_username', nextUsername);
  }
  return { token: nextToken, username: nextUsername, authError };
}

export default function App() {
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });
  const showToast = useCallback((message, error = false) => {
    setSnack({ open: true, message, severity: error ? 'error' : 'success' });
  }, []);

  const [boot] = useState(() => consumeOidcCallback());
  const [token, setToken] = useState(
    () => boot.token || localStorage.getItem('pulumi_token') || '',
  );
  const [username, setUsername] = useState(
    () => boot.username || localStorage.getItem('pulumi_username') || '',
  );
  const [authError] = useState(() => boot.authError || '');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!token) { setReady(true); return; }
    authApi.me()
      .then(response => {
        if (response.status === 401) {
          localStorage.removeItem('pulumi_token');
          localStorage.removeItem('pulumi_username');
          setToken('');
          setUsername('');
        } else if (response.ok) {
          return response.json().then(data => {
            if (data.username) {
              localStorage.setItem('pulumi_username', data.username);
              setUsername(data.username);
            }
          });
        }
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []); // eslint-disable-line

  const signIn = (nextToken, nextUsername) => {
    localStorage.setItem('pulumi_token', nextToken);
    localStorage.setItem('pulumi_username', nextUsername);
    setToken(nextToken);
    setUsername(nextUsername);
  };
  const signOut = () => {
    localStorage.removeItem('pulumi_token');
    localStorage.removeItem('pulumi_username');
    setToken('');
    setUsername('');
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ToastContext.Provider value={showToast}>
        <AuthContext.Provider value={{ token, username, signIn, signOut }}>
          {!ready ? (
            <CenteredSpinner />
          ) : token ? (
            <Layout>
              <PulumiPage />
            </Layout>
          ) : (
            <Login authError={authError} />
          )}
        </AuthContext.Provider>
      </ToastContext.Provider>
      <Snackbar
        open={snack.open}
        autoHideDuration={3500}
        onClose={() => setSnack(current => ({ ...current, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snack.severity} variant="filled" sx={{ borderRadius: 2, fontWeight: 600 }}>
          {snack.message}
        </Alert>
      </Snackbar>
    </ThemeProvider>
  );
}

function CenteredSpinner() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: '#060c18' }}>
      <div style={{ width: 32, height: 32, border: '3px solid #6366f1', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
