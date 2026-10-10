import { useMemo, useState } from 'react';
import {
  Box, Card, CardContent, Chip, CircularProgress, IconButton, Tab, Tabs, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography,
} from '@mui/material';
import LayersIcon from '@mui/icons-material/Layers';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { pulumiApi } from '../api.js';
import { relativeTime } from '../utils.js';
import { useToast } from '../App.jsx';
import { Changes, PropertyValue } from './properties.jsx';
import UpdateDiffDialog from './UpdateDiff.jsx';

const RESULT_COLOR = { succeeded: 'success', failed: 'error' };

export default function StackView({ loc, stack, resources, updates, error, onTab, onOpenResource }) {
  const showToast = useToast();
  const identity = `${loc.backend}/${loc.project}/${loc.stack}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(identity);
      showToast('Copied');
    } catch {
      showToast('Could not copy', true);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, mb: 0.75 }}>
        <Box sx={{
          width: 36, height: 36, borderRadius: 2,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(99,102,241,0.14)',
        }}>
          <LayersIcon sx={{ color: 'primary.light', fontSize: 20 }} />
        </Box>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>{loc.stack}</Typography>
        {stack?.locked && <Chip label="locked" size="small" color="warning" />}
        <Tooltip title="Copy name">
          <IconButton size="small" onClick={copy} sx={{ color: 'text.secondary' }}>
            <ContentCopyIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      <StatusLine update={stack?.last_update} />
      <Tabs
        value={loc.tab}
        onChange={(_, value) => onTab(value)}
        sx={{ mb: 2, minHeight: 40, '& .MuiTabs-indicator': { height: 2 } }}
      >
        <Tab value="overview" label="Overview" sx={{ fontSize: '0.8rem', minHeight: 40 }} />
        <Tab value="updates" label="Updates" sx={{ fontSize: '0.8rem', minHeight: 40 }} />
        <Tab
          value="resources"
          sx={{ fontSize: '0.8rem', minHeight: 40 }}
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
              Resources
              <Chip label={stack?.resource_count ?? 0} size="small" />
            </Box>
          }
        />
        <Tab value="settings" label="Settings" sx={{ fontSize: '0.8rem', minHeight: 40 }} />
      </Tabs>
      {loc.tab === 'overview' && <Overview stack={stack} />}
      {loc.tab === 'updates' && (updates === null ? (error ? null : <TabSpinner />) : <Updates loc={loc} updates={updates} />)}
      {loc.tab === 'resources' && (resources === null ? (error ? null : <TabSpinner />) : <Resources resources={resources} onOpen={onOpenResource} />)}
      {loc.tab === 'settings' && <Settings stack={stack} />}
    </Box>
  );
}

function StatusLine({ update }) {
  if (!update) {
    return (
      <Typography variant="body2" sx={{ mb: 2 }}>
        <Box component="span" sx={{ fontWeight: 700 }}>Status:</Box> no updates recorded
      </Typography>
    );
  }
  const color = update.result === 'succeeded' ? 'success.main' : update.result === 'failed' ? 'error.main' : 'warning.main';
  const when = relativeTime(update.end_time || update.start_time);
  return (
    <Typography variant="body2" sx={{ mb: 2 }}>
      <Box component="span" sx={{ fontWeight: 700 }}>Status:</Box>
      {' '}Update #{update.version ?? '—'}
      {update.kind ? ` (${update.kind})` : ''} {update.result}
      {when ? ` ${when}` : ''}
      <Box component="span" sx={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', bgcolor: color, ml: 1 }} />
    </Typography>
  );
}

function Overview({ stack }) {
  const outputs = stack?.outputs || {};
  const types = stack?.types || [];
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2.5 }}>
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ fontSize: '1rem', mb: 1.5 }}>Outputs</Typography>
          {Object.keys(outputs).length === 0
            ? <Empty text="No outputs" />
            : <PropertyValue value={outputs} />}
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ fontSize: '1rem', mb: 1.5 }}>Resources</Typography>
          {types.length === 0 ? <Empty text="No resources" /> : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Type</TableCell>
                  <TableCell align="right">Count</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {types.map(row => (
                  <TableRow key={row.type}>
                    <TableCell sx={{ fontSize: '0.8rem', fontFamily: 'ui-monospace, monospace' }}>{row.type}</TableCell>
                    <TableCell align="right">{row.count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}

function Updates({ loc, updates }) {
  const rows = updates || [];
  const [open, setOpen] = useState(false);
  const [diff, setDiff] = useState(null);
  const [diffError, setDiffError] = useState('');
  const [diffLoading, setDiffLoading] = useState(false);

  const openDiff = async (row) => {
    if (!row.id) return;
    setOpen(true);
    setDiff(null);
    setDiffError('');
    setDiffLoading(true);
    const response = await pulumiApi.updateDiff(loc.backend, loc.project, loc.stack, row.id);
    setDiffLoading(false);
    if (!response.ok) {
      setDiffError(response.data?.error || 'Failed to load the update diff');
      return;
    }
    setDiff(response.data);
  };

  return (
    <Card>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>Kind</TableCell>
              <TableCell>Result</TableCell>
              <TableCell>Message</TableCell>
              <TableCell>Changes</TableCell>
              <TableCell align="right">Time</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow><TableCell colSpan={6}><Empty text="No updates" /></TableCell></TableRow>
            ) : rows.map(row => (
              <TableRow key={row.id || row.start_time}>
                <TableCell>{row.version ?? '—'}</TableCell>
                <TableCell sx={{ fontSize: '0.8rem' }}>{row.kind || '—'}</TableCell>
                <TableCell>
                  <Chip label={row.result || 'unknown'} size="small" color={RESULT_COLOR[row.result] || 'warning'} />
                </TableCell>
                <TableCell sx={{ fontSize: '0.8rem', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.message || '—'}</TableCell>
                <TableCell>
                  <Tooltip title={row.id ? 'Show what changed' : ''}>
                    <Box
                      onClick={() => openDiff(row)}
                      sx={{ cursor: row.id ? 'pointer' : 'default', display: 'inline-flex', '&:hover': row.id ? { opacity: 0.8 } : undefined }}
                    >
                      <Changes changes={row.resource_changes} />
                    </Box>
                  </Tooltip>
                </TableCell>
                <TableCell align="right" sx={{ fontSize: '0.75rem', color: 'text.disabled' }}>{relativeTime(row.end_time || row.start_time)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <UpdateDiffDialog
        open={open}
        loading={diffLoading}
        error={diffError}
        diff={diff}
        onClose={() => setOpen(false)}
      />
    </Card>
  );
}

function Resources({ resources, onOpen }) {
  const [query, setQuery] = useState('');
  const rows = resources || [];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter(row =>
      row.name?.toLowerCase().includes(needle)
      || row.type?.toLowerCase().includes(needle)
      || row.urn?.toLowerCase().includes(needle)
    );
  }, [rows, query]);

  return (
    <Card>
      <CardContent sx={{ pb: 1 }}>
        <TextField
          placeholder="Search name, type, or URN"
          value={query}
          onChange={event => setQuery(event.target.value)}
          fullWidth
        />
      </CardContent>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell align="right">Modified</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow><TableCell colSpan={3}><Empty text={rows.length ? 'No matching resources' : 'No resources'} /></TableCell></TableRow>
            ) : filtered.map(row => (
              <TableRow key={row.urn} hover sx={{ cursor: 'pointer' }} onClick={() => onOpen(row.urn)}>
                <TableCell sx={{ fontSize: '0.85rem', fontWeight: 600 }}>{row.name}</TableCell>
                <TableCell sx={{ fontSize: '0.8rem', fontFamily: 'ui-monospace, monospace' }}>{row.type}</TableCell>
                <TableCell align="right" sx={{ fontSize: '0.75rem', color: 'text.disabled' }}>{relativeTime(row.modified) || '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Card>
  );
}

function Settings({ stack }) {
  const config = stack?.config || {};
  const entries = Object.entries(config);
  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ fontSize: '1rem', mb: 1.5 }}>Config</Typography>
          {entries.length === 0 ? <Empty text="No config recorded for the latest update" /> : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Key</TableCell>
                  <TableCell>Value</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {entries.map(([key, entry]) => (
                  <TableRow key={key}>
                    <TableCell sx={{ fontSize: '0.8rem', fontFamily: 'ui-monospace, monospace' }}>{key}</TableCell>
                    <TableCell>{entry?.secret ? <Chip label="secret" size="small" color="warning" /> : <PropertyValue value={entry?.value} />}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ fontSize: '1rem', mb: 1.5 }}>Backend</Typography>
          <Typography variant="body2" color="text.secondary">Name</Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>{stack?.backend || '—'}</Typography>
          <Typography variant="body2" color="text.secondary">Bucket</Typography>
          <Typography variant="body2">{stack?.bucket || '—'}</Typography>
        </CardContent>
      </Card>
    </Box>
  );
}

function TabSpinner() {
  return <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={24} /></Box>;
}

function Empty({ text }) {
  return <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>{text}</Typography>;
}
