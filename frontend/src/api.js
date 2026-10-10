const token = () => localStorage.getItem('pulumi_token') || '';

async function call(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: { Authorization: `Token ${token()}`, 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  let data;
  try { const t = await res.text(); data = t ? JSON.parse(t) : {}; }
  catch { data = {}; }
  return { ok: res.ok, status: res.status, data };
}

export const authApi = {
  config: () => fetch('/api/auth/config/').then(async (res) => {
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, data };
  }),
  token: (username, password) => fetch('/api/auth/token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }),
  me: () => fetch('/api/auth/me/', { headers: { Authorization: `Token ${token()}` } }),
  oidcLoginUrl: '/api/auth/oidc/login/',
};

export const pulumiApi = {
  backends: () => call('GET', '/api/pulumi/backends/'),
  projects: backend => call('GET', `/api/pulumi/backends/${encodeURIComponent(backend)}/projects/`),
  stacks: (backend, project) => call('GET', `/api/pulumi/backends/${encodeURIComponent(backend)}/projects/${encodeURIComponent(project)}/stacks/`),
  stack: (backend, project, stack) => call('GET', `/api/pulumi/backends/${encodeURIComponent(backend)}/projects/${encodeURIComponent(project)}/stacks/${encodeURIComponent(stack)}/`),
  resources: (backend, project, stack) => call('GET', `/api/pulumi/backends/${encodeURIComponent(backend)}/projects/${encodeURIComponent(project)}/stacks/${encodeURIComponent(stack)}/resources/`),
  resource: (backend, project, stack, urn) => call('GET', `/api/pulumi/backends/${encodeURIComponent(backend)}/projects/${encodeURIComponent(project)}/stacks/${encodeURIComponent(stack)}/resources/detail/?urn=${encodeURIComponent(urn)}`),
  updates: (backend, project, stack) => call('GET', `/api/pulumi/backends/${encodeURIComponent(backend)}/projects/${encodeURIComponent(project)}/stacks/${encodeURIComponent(stack)}/updates/`),
  updateDiff: (backend, project, stack, id) => call('GET', `/api/pulumi/backends/${encodeURIComponent(backend)}/projects/${encodeURIComponent(project)}/stacks/${encodeURIComponent(stack)}/updates/diff/?id=${encodeURIComponent(id)}`),
};
