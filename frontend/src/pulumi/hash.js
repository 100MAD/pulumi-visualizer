const TABS = ['overview', 'updates', 'resources', 'settings'];

export function parseHash(hash) {
  const raw = (hash || '').replace(/^#/, '');
  const [pathPart, queryPart = ''] = raw.split('?');
  const params = new URLSearchParams(queryPart);
  let parts = [];
  try {
    parts = pathPart.split('/').filter(Boolean).map(decodeURIComponent);
  } catch {
    parts = [];
  }
  const loc = {
    backend: '',
    project: '',
    stack: '',
    urn: '',
    tab: params.get('tab') || 'overview',
  };
  if (parts[0] !== 'backends') return loc;
  if (parts[1]) loc.backend = parts[1];
  if (parts[2] === 'projects' && parts[3]) loc.project = parts[3];
  if (parts[4] === 'stacks' && parts[5]) loc.stack = parts[5];
  if (parts[6] === 'resources' && parts[7]) loc.urn = parts.slice(7).join('/');
  if (!TABS.includes(loc.tab)) loc.tab = 'overview';
  return loc;
}

export function buildHash(loc) {
  const parts = ['backends'];
  if (!loc.backend) return '#/' + parts.join('/');
  parts.push(encodeURIComponent(loc.backend));
  if (!loc.project) return '#/' + parts.join('/');
  parts.push('projects', encodeURIComponent(loc.project));
  if (!loc.stack) return '#/' + parts.join('/');
  parts.push('stacks', encodeURIComponent(loc.stack));
  if (loc.urn) parts.push('resources', encodeURIComponent(loc.urn));
  const base = '#/' + parts.join('/');
  if (loc.tab && loc.tab !== 'overview') return `${base}?tab=${encodeURIComponent(loc.tab)}`;
  return base;
}
