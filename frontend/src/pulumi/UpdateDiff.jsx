import {
  Box, Chip, CircularProgress, Dialog, DialogContent, DialogTitle, IconButton, Table,
  TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { isSecret } from './properties.jsx';

const OP_COLOR = { create: 'success', update: 'warning', delete: 'error', add: 'success', remove: 'error', replace: 'warning' };
const OP_LABEL = { create: 'create', update: 'update', delete: 'delete', add: '+', remove: '−', replace: '~' };

export default function UpdateDiffDialog({ open, loading, error, diff, onClose }) {
  const title = diff?.message || (diff ? `Update #${diff.version ?? '—'}` : 'Update diff');
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pr: 6 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h6" sx={{ fontSize: '1rem' }} noWrap>{title}</Typography>
          {diff && (
            <Typography variant="caption" color="text.secondary">
              #{diff.version ?? '—'} {diff.kind || 'update'} {diff.result || ''}
            </Typography>
          )}
        </Box>
        <IconButton onClick={onClose} sx={{ position: 'absolute', right: 12, top: 12 }} aria-label="Close">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ maxHeight: '70vh' }}>
        {loading && <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={24} /></Box>}
        {!loading && error && <Typography variant="body2" color="error">{error}</Typography>}
        {!loading && !error && diff && !diff.available && (
          <Typography variant="body2" color="text.secondary">
            This update has no stored checkpoint to compare.
          </Typography>
        )}
        {!loading && !error && diff?.available && diff.changes.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No input or output changes between this checkpoint and the previous one.
          </Typography>
        )}
        {!loading && !error && diff?.available && diff.changes.map(change => (
          <Box key={change.urn} sx={{ mb: 2.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.75, flexWrap: 'wrap' }}>
              <Chip label={OP_LABEL[change.op] || change.op} size="small" color={OP_COLOR[change.op] || 'default'} />
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{change.name}</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'ui-monospace, monospace' }}>{change.type}</Typography>
            </Box>
            {change.before_id !== undefined && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.75 }}>
                id {change.before_id || '—'} → {change.after_id || '—'}
              </Typography>
            )}
            <PropertyTable title="Inputs" rows={change.inputs} />
            <PropertyTable title="Outputs" rows={change.outputs} />
          </Box>
        ))}
      </DialogContent>
    </Dialog>
  );
}

function PropertyTable({ title, rows }) {
  if (!rows?.length) return null;
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>{title}</Typography>
      <Table size="small" sx={{ tableLayout: 'fixed', width: '100%' }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: 36 }} />
            <TableCell sx={{ width: 200 }}>Property</TableCell>
            <TableCell>Before</TableCell>
            <TableCell>After</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map(row => (
            <TableRow key={row.key}>
              <TableCell sx={{ color: row.op === 'remove' ? 'error.main' : row.op === 'add' ? 'success.main' : 'warning.main', fontWeight: 700, verticalAlign: 'top' }}>
                {OP_LABEL[row.op]}
              </TableCell>
              <TableCell sx={{ fontFamily: 'ui-monospace, monospace', fontSize: '0.8rem', verticalAlign: 'top', overflowWrap: 'anywhere' }}>{row.key}</TableCell>
              <TableCell sx={{ verticalAlign: 'top', minWidth: 0 }}>{row.op === 'add' ? <Muted /> : <DiffValue value={row.before} />}</TableCell>
              <TableCell sx={{ verticalAlign: 'top', minWidth: 0 }}>{row.op === 'remove' ? <Muted /> : <DiffValue value={row.after} />}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

function Structured({ value }) {
  if (Array.isArray(value)) {
    if (!value.length) return <Typography variant="body2" color="text.secondary">[]</Typography>;
    return (
      <Box sx={{ display: 'grid', gap: 0.75 }}>
        {value.map((item, index) => (
          <Box key={index}>{typeof item === 'object' && item !== null ? <Structured value={item} /> : <Scalar value={item} />}</Box>
        ))}
      </Box>
    );
  }
  const entries = Object.entries(value);
  if (!entries.length) return <Typography variant="body2" color="text.secondary">{'{}'}</Typography>;
  return (
    <Box sx={{ display: 'grid', gap: 0.35 }}>
      {entries.map(([key, item]) => (
        <Box key={key} sx={{ display: 'flex', gap: 1, alignItems: 'baseline', minWidth: 0 }}>
          <Typography variant="body2" color="text.secondary" sx={{ flex: '0 0 auto', fontSize: '0.75rem' }}>{key}</Typography>
          <Box sx={{ minWidth: 0 }}>
            {item !== null && typeof item === 'object' ? <Structured value={item} /> : <Scalar value={item} />}
          </Box>
        </Box>
      ))}
    </Box>
  );
}

function Scalar({ value }) {
  return (
    <Typography variant="body2" sx={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', overflowWrap: 'break-word' }}>
      {String(value)}
    </Typography>
  );
}

function Muted() {
  return <Typography variant="body2" color="text.secondary">—</Typography>;
}

function DiffValue({ value }) {
  if (isSecret(value)) return <Chip label="secret" size="small" color="warning" />;
  if (value === null || value === undefined || value === '') return <Muted />;
  if (Array.isArray(value) && value.every(item => item === null || ['string', 'number', 'boolean'].includes(typeof item))) {
    if (!value.length) return <Typography variant="body2" color="text.secondary">[]</Typography>;
    return (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {value.map((item, index) => (
          <Chip key={index} size="small" variant="outlined" label={String(item)} />
        ))}
      </Box>
    );
  }
  if (typeof value === 'object') return <Structured value={value} />;
  return <Scalar value={value} />;
}
