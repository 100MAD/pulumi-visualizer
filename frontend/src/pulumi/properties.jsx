import { Box, Chip, Typography } from '@mui/material';

export function isSecret(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value)
    && value.secret === true && Object.keys(value).length === 1;
}

export function PropertyValue({ value, depth = 0 }) {
  if (isSecret(value)) return <Chip label="secret" size="small" color="warning" />;
  if (value === null || value === undefined || value === '') {
    return <Typography variant="body2" color="text.secondary">—</Typography>;
  }
  if (typeof value !== 'object') {
    return (
      <Typography variant="body2" sx={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace', wordBreak: 'break-all', fontSize: '0.8rem' }}>
        {String(value)}
      </Typography>
    );
  }
  if (Array.isArray(value)) {
    if (!value.length) return <Typography variant="body2" color="text.secondary">[]</Typography>;
    return (
      <Box>
        {value.map((item, index) => (
          <Box key={index} sx={{ display: 'flex', gap: 1, mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 16 }}>{index}</Typography>
            <Box sx={{ minWidth: 0 }}><PropertyValue value={item} depth={depth + 1} /></Box>
          </Box>
        ))}
      </Box>
    );
  }
  const entries = Object.entries(value);
  if (!entries.length) return <Typography variant="body2" color="text.secondary">{'{}'}</Typography>;
  return (
    <Box sx={{ pl: depth ? 1.5 : 0, borderLeft: depth ? '1px solid rgba(148,163,184,0.15)' : 'none' }}>
      {entries.map(([key, item]) => (
        <Box key={key} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'minmax(90px, 200px) 1fr' }, gap: 1, py: 0.45 }}>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem', wordBreak: 'break-word' }}>{key}</Typography>
          <PropertyValue value={item} depth={depth + 1} />
        </Box>
      ))}
    </Box>
  );
}

export function Changes({ changes }) {
  const create = num(changes, 'create') + num(changes, 'create-replacement') + num(changes, 'import');
  const update = num(changes, 'update') + num(changes, 'replace');
  const remove = num(changes, 'delete') + num(changes, 'delete-replaced');
  if (!create && !update && !remove) {
    return <Typography variant="body2" color="text.secondary">—</Typography>;
  }
  return (
    <Box sx={{ fontSize: '0.8rem', fontWeight: 700 }}>
      {create ? <Box component="span" sx={{ color: 'success.main', mr: 1 }}>+{create}</Box> : null}
      {update ? <Box component="span" sx={{ color: 'warning.main', mr: 1 }}>~{update}</Box> : null}
      {remove ? <Box component="span" sx={{ color: 'error.main' }}>-{remove}</Box> : null}
    </Box>
  );
}

function num(changes, key) {
  const value = changes?.[key];
  return typeof value === 'number' ? value : 0;
}
