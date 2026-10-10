import { Box, Card, CardContent, Chip, Typography } from '@mui/material';
import { PropertyValue } from './properties.jsx';

export default function ResourceView({ resource, onOpen }) {
  if (!resource) return null;
  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>{resource.name}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5, fontFamily: 'ui-monospace, monospace' }}>
        {resource.type}
      </Typography>
      {resource.id ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>ID {resource.id}</Typography>
      ) : <Box sx={{ mb: 2 }} />}
      <Box sx={{ display: 'grid', gap: 2.5 }}>
        <Section title="Outputs">
          <PropertyValue value={resource.outputs || {}} />
        </Section>
        <Section title="Inputs">
          <PropertyValue value={resource.inputs || {}} />
        </Section>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ fontSize: '1rem', mb: 1.5 }}>Dependencies</Typography>
            {resource.parent ? (
              <Box sx={{ mb: 1 }}>
                <Typography variant="caption" color="text.secondary">Parent</Typography>
                <UrnLink urn={resource.parent} onOpen={onOpen} />
              </Box>
            ) : null}
            {(resource.dependencies || []).length === 0 && !resource.parent
              ? <Typography variant="body2" color="text.secondary">None</Typography>
              : (resource.dependencies || []).map(urn => <UrnLink key={urn} urn={urn} onOpen={onOpen} />)}
            {resource.provider ? (
              <Box sx={{ mt: 1.5 }}>
                <Typography variant="caption" color="text.secondary">Provider</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'ui-monospace, monospace', fontSize: '0.75rem', wordBreak: 'break-all' }}>
                  {resource.provider}
                </Typography>
              </Box>
            ) : null}
            {resource.protect ? <Chip label="protected" size="small" sx={{ mt: 1.5 }} /> : null}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}

function Section({ title, children }) {
  const empty = children?.props?.value && typeof children.props.value === 'object' && Object.keys(children.props.value).length === 0;
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ fontSize: '1rem', mb: 1.5 }}>{title}</Typography>
        {empty ? <Typography variant="body2" color="text.secondary">None</Typography> : children}
      </CardContent>
    </Card>
  );
}

function UrnLink({ urn, onOpen }) {
  const name = urn.split('::').slice(3).join('::') || urn;
  return (
    <Typography
      variant="body2"
      onClick={() => onOpen(urn)}
      sx={{ fontFamily: 'ui-monospace, monospace', fontSize: '0.8rem', color: 'primary.light', cursor: 'pointer', wordBreak: 'break-all', '&:hover': { textDecoration: 'underline' } }}
    >
      {name}
    </Typography>
  );
}
