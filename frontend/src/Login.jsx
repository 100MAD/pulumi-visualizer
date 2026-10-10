import { useEffect, useState } from 'react';
import {
  Box, Card, CardContent, TextField, Button, Typography, Alert,
  InputAdornment, IconButton, Divider,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import LayersIcon from '@mui/icons-material/Layers';
import LoginIcon from '@mui/icons-material/Login';
import { authApi } from './api.js';
import { useAuth } from './App.jsx';

export default function Login({ authError = '' }) {
  const { signIn } = useAuth();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState(authError);
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [config, setConfig] = useState({
    oidc_enabled: false,
    oidc_label: 'Sign in with SSO',
    password_login: true,
  });

  useEffect(() => {
    authApi.config()
      .then(({ ok, data }) => {
        if (ok) setConfig({
          oidc_enabled: !!data.oidc_enabled,
          oidc_label: data.oidc_label || 'Sign in with SSO',
          password_login: data.password_login !== false,
        });
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (authError) setError(authError);
  }, [authError]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await authApi.token(form.username, form.password);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setError(data.detail || data.non_field_errors?.[0] || 'Invalid credentials.');
        return;
      }
      const data = await response.json();
      signIn(data.token, form.username);
    } catch {
      setError('Network error — please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'radial-gradient(ellipse at 30% 40%,rgba(99,102,241,0.12) 0%,transparent 60%), radial-gradient(ellipse at 70% 60%,rgba(6,182,212,0.08) 0%,transparent 50%), #060c18',
      px: 2,
    }}>
      <Box sx={{ width: '100%', maxWidth: 420 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Box sx={{
            width: 64, height: 64, mx: 'auto', mb: 2,
            background: 'linear-gradient(135deg,#6366f1,#06b6d4)',
            borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 32px rgba(99,102,241,0.4)',
          }}>
            <LayersIcon sx={{ color: '#fff', fontSize: 36 }} />
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 800, background: 'linear-gradient(90deg,#818cf8,#06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Pulumi
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            State visualizer
          </Typography>
        </Box>

        <Card elevation={0}>
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 700 }}>Sign in</Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 2.5, borderRadius: 2 }}>{error}</Alert>
            )}

            {config.oidc_enabled && (
              <Button
                component="a"
                href={authApi.oidcLoginUrl}
                variant="contained"
                fullWidth
                size="large"
                startIcon={<LoginIcon />}
                sx={{
                  py: 1.4,
                  background: 'linear-gradient(135deg,#6366f1,#4f46e5)',
                  '&:hover': { background: 'linear-gradient(135deg,#818cf8,#6366f1)' },
                }}
              >
                {config.oidc_label}
              </Button>
            )}

            {config.oidc_enabled && config.password_login && (
              <Divider sx={{ my: 3, borderColor: 'rgba(148,163,184,0.16)', '&::before, &::after': { borderColor: 'rgba(148,163,184,0.16)' } }}>
                <Typography variant="caption" color="text.secondary">or</Typography>
              </Divider>
            )}

            {config.password_login && (
              <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Username"
                  autoComplete="username"
                  required
                  fullWidth
                  value={form.username}
                  onChange={event => setForm(current => ({ ...current, username: event.target.value }))}
                />
                <TextField
                  label="Password"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  fullWidth
                  value={form.password}
                  onChange={event => setForm(current => ({ ...current, password: event.target.value }))}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={() => setShowPw(value => !value)} edge="end">
                          {showPw ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                <Button
                  type="submit"
                  variant={config.oidc_enabled ? 'outlined' : 'contained'}
                  fullWidth
                  disabled={loading}
                  size="large"
                  sx={config.oidc_enabled ? { mt: 1, py: 1.4 } : {
                    mt: 1, py: 1.4,
                    background: 'linear-gradient(135deg,#6366f1,#4f46e5)',
                    '&:hover': { background: 'linear-gradient(135deg,#818cf8,#6366f1)' },
                  }}
                >
                  {loading ? 'Signing in…' : 'Sign In'}
                </Button>
              </Box>
            )}

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 3 }}>
              {config.oidc_enabled && !config.password_login
                ? 'Sign in with your organization identity provider'
                : 'Accounts are managed by administrators'}
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
