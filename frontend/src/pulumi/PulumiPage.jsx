import { useEffect, useRef, useState } from 'react';
import {
  Alert, Box, Breadcrumbs, Card, CardContent, CircularProgress, Link, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from '@mui/material';
import { pulumiApi } from '../api.js';
import { relativeTime } from '../utils.js';
import { buildHash, parseHash } from './hash.js';
import StackView from './StackView.jsx';
import ResourceView from './ResourceView.jsx';

export default function PulumiPage() {
  const [loc, setLoc] = useState(() => parseHash(window.location.hash));
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [updated, setUpdated] = useState(null);
  const [backends, setBackends] = useState(null);
  const [projects, setProjects] = useState(null);
  const [stacks, setStacks] = useState(null);
  const [stack, setStack] = useState(null);
  const [resources, setResources] = useState(null);
  const [updates, setUpdates] = useState(null);
  const [resource, setResource] = useState(null);

  useEffect(() => {
    const apply = () => setLoc(parseHash(window.location.hash));
    window.addEventListener('hashchange', apply);
    return () => window.removeEventListener('hashchange', apply);
  }, []);

  const go = (next) => {
    const hash = buildHash(next);
    if (window.location.hash !== hash) window.location.hash = hash;
  };

  const viewKey = [loc.backend, loc.project, loc.stack, loc.urn, loc.tab].join('\n');
  const placeKey = [loc.backend, loc.project, loc.stack, loc.urn].join('\n');
  const placeRef = useRef('');

  useEffect(() => {
    let stopped = false;
    let inflight = false;
    const placeChanged = placeRef.current !== placeKey;
    placeRef.current = placeKey;
    if (placeChanged) {
      setError('');
      setLoading(true);
      setBackends(null);
      setProjects(null);
      setStacks(null);
      setStack(null);
      setResources(null);
      setUpdates(null);
      setResource(null);
    }

    const load = async () => {
      if (stopped || document.hidden || inflight) return;
      inflight = true;
      try {
        const fail = (response) => {
          if (!stopped) setError(response.data?.error || 'Failed to load Pulumi state');
        };
        if (!loc.backend) {
          const response = await pulumiApi.backends();
          if (stopped) return;
          if (!response.ok) { fail(response); return; }
          setBackends(response.data.backends || []);
        } else if (!loc.project) {
          const response = await pulumiApi.projects(loc.backend);
          if (stopped) return;
          if (!response.ok) { fail(response); return; }
          setProjects(response.data.projects || []);
        } else if (!loc.stack) {
          const response = await pulumiApi.stacks(loc.backend, loc.project);
          if (stopped) return;
          if (!response.ok) { fail(response); return; }
          setStacks(response.data.stacks || []);
        } else if (loc.urn) {
          const response = await pulumiApi.resource(loc.backend, loc.project, loc.stack, loc.urn);
          if (stopped) return;
          if (!response.ok) { fail(response); return; }
          setResource(response.data);
        } else {
          const stackResponse = await pulumiApi.stack(loc.backend, loc.project, loc.stack);
          if (stopped) return;
          if (!stackResponse.ok) { fail(stackResponse); return; }
          setStack(stackResponse.data);
          if (loc.tab === 'resources') {
            const response = await pulumiApi.resources(loc.backend, loc.project, loc.stack);
            if (stopped) return;
            if (!response.ok) { fail(response); return; }
            setResources(response.data.resources || []);
          }
          if (loc.tab === 'updates') {
            const response = await pulumiApi.updates(loc.backend, loc.project, loc.stack);
            if (stopped) return;
            if (!response.ok) { fail(response); return; }
            setUpdates(response.data.updates || []);
          }
        }
        if (!stopped) {
          setError('');
          setUpdated(new Date());
        }
      } catch {
        if (!stopped) setError('Network error');
      } finally {
        inflight = false;
        if (!stopped) setLoading(false);
      }
    };

    load();
    const timer = setInterval(load, 5000);
    const onVisible = () => { if (!document.hidden) load(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      stopped = true;
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [viewKey, placeKey, loc]);

  const primaryReady = loc.urn ? resource !== null : loc.stack ? stack !== null : loc.project ? stacks !== null : loc.backend ? projects !== null : backends !== null;
  const showSpinner = loading && !primaryReady;

  return (
    <Box>
      {loc.backend ? <Crumbs loc={loc} resource={resource} go={go} /> : (
        <>
          <Typography variant="h5" sx={{ mb: 0.5 }}>Stacks</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Pulumi state by backend, project, stack, and resource
          </Typography>
        </>
      )}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {showSpinner ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}><CircularProgress size={24} /></Box>
      ) : (
        <Body
          loc={loc}
          backends={backends}
          projects={projects}
          stacks={stacks}
          stack={stack}
          resources={resources}
          updates={updates}
          resource={resource}
          error={error}
          go={go}
        />
      )}
      {updated && !showSpinner && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
          Updated {relativeTime(updated)}
        </Typography>
      )}
    </Box>
  );
}

function Body({ loc, backends, projects, stacks, stack, resources, updates, resource, error, go }) {
  if (!loc.backend) {
    if (backends === null) return null;
    return <BackendList rows={backends} onOpen={name => go({ backend: name })} />;
  }
  if (!loc.project) {
    if (projects === null) return null;
    return <ProjectList rows={projects} onOpen={name => go({ backend: loc.backend, project: name })} />;
  }
  if (!loc.stack) {
    if (stacks === null) return null;
    return (
      <StackList
        rows={stacks}
        onOpen={name => go({ backend: loc.backend, project: loc.project, stack: name, tab: 'overview' })}
      />
    );
  }
  if (loc.urn) {
    if (!resource) return null;
    return <ResourceView resource={resource} onOpen={urn => go({ ...loc, urn })} />;
  }
  if (!stack) return null;
  return (
    <StackView
      loc={loc}
      stack={stack}
      resources={resources}
      updates={updates}
      onTab={tab => go({ ...loc, tab, urn: '' })}
      onOpenResource={urn => go({ ...loc, tab: 'resources', urn })}
      error={error}
    />
  );
}

function Crumbs({ loc, resource, go }) {
  const items = [{ label: 'Backends', to: {} }];
  if (loc.backend) items.push({ label: loc.backend, to: { backend: loc.backend } });
  if (loc.project) items.push({ label: loc.project, to: { backend: loc.backend, project: loc.project } });
  if (loc.stack) {
    items.push({
      label: loc.stack,
      to: { backend: loc.backend, project: loc.project, stack: loc.stack, tab: loc.tab === 'resources' ? 'resources' : 'overview' },
    });
  }
  if (loc.urn) {
    const label = resource?.name || loc.urn.split('::').slice(3).join('::') || loc.urn;
    items.push({ label, to: null });
  }
  return (
    <Breadcrumbs separator="/" sx={{ mb: 2 }}>
      {items.map((item, index) => {
        const last = index === items.length - 1;
        if (last) {
          return <Typography key={index} color="text.primary" sx={{ fontWeight: 700, fontSize: '0.85rem' }}>{item.label}</Typography>;
        }
        return (
          <Link
            key={index}
            component="button"
            type="button"
            underline="hover"
            color="text.secondary"
            onClick={() => go(item.to)}
            sx={{ fontSize: '0.85rem' }}
          >
            {item.label}
          </Link>
        );
      })}
    </Breadcrumbs>
  );
}

function BackendList({ rows, onOpen }) {
  if (!rows.length) {
    return <EmptyCard text="No backends configured. Set PULUMI_STATE_BACKENDS on the API." />;
  }
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2.5 }}>
      {rows.map(row => (
        <Card key={row.name} onClick={() => onOpen(row.name)} sx={{ cursor: 'pointer' }}>
          <CardContent>
            <Typography variant="h6" sx={{ fontSize: '1rem' }}>{row.name}</Typography>
            <Typography variant="body2" color="text.secondary">
              {row.bucket}{row.prefix ? ` / ${row.prefix}` : ''}
            </Typography>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}

function ProjectList({ rows, onOpen }) {
  return (
    <SimpleTable
      empty="No projects in this backend"
      columns={['Project', 'Stacks']}
      rows={rows}
      rowKey={row => row.name}
      onRow={row => onOpen(row.name)}
      cells={row => [row.name, row.stack_count]}
    />
  );
}

function StackList({ rows, onOpen }) {
  return (
    <SimpleTable
      empty="No stacks in this project"
      columns={['Stack', 'Resources', 'Last update', 'Updated']}
      rows={rows}
      rowKey={row => row.name}
      onRow={row => onOpen(row.name)}
      cells={row => [
        row.name,
        row.resource_count,
        row.last_update ? `#${row.last_update.version ?? '—'} ${row.last_update.kind || ''} ${row.last_update.result || ''}`.trim() : '—',
        relativeTime(row.updated_at) || '—',
      ]}
    />
  );
}

function SimpleTable({ columns, rows, rowKey, cells, onRow, empty }) {
  return (
    <Card>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              {columns.map(column => <TableCell key={column}>{column}</TableCell>)}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length}>
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>{empty}</Typography>
                </TableCell>
              </TableRow>
            ) : rows.map(row => (
              <TableRow key={rowKey(row)} hover sx={{ cursor: 'pointer' }} onClick={() => onRow(row)}>
                {cells(row).map((cell, index) => (
                  <TableCell key={columns[index]} sx={{ fontSize: '0.85rem' }}>{cell}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Card>
  );
}

function EmptyCard({ text }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{text}</Typography>
      </CardContent>
    </Card>
  );
}
