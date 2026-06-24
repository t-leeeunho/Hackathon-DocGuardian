import { ChevronDown } from 'lucide-react';

const SCOPES = [
  { value: 'repo', label: 'Repo' },
  { value: 'team', label: 'Team' },
  { value: 'company', label: 'Company' },
  { value: 'cluster', label: 'Cluster' },
  { value: 'summary-only', label: 'Summary only' },
  { value: 'source-required', label: 'Source required' },
] as const;

type ScopeValue = typeof SCOPES[number]['value'];

interface ScopeToggleProps {
  value: ScopeValue;
  onChange: (v: ScopeValue) => void;
}

export function ScopeToggle({ value, onChange }: ScopeToggleProps) {
  const current = SCOPES.find(s => s.value === value);
  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <select
        value={value}
        onChange={e => onChange(e.target.value as ScopeValue)}
        style={{
          appearance: 'none',
          background: 'rgba(139,92,246,0.1)',
          border: '1px solid rgba(139,92,246,0.25)',
          borderRadius: 6,
          color: '#a78bfa',
          fontSize: 12,
          padding: '4px 28px 4px 10px',
          cursor: 'pointer',
          outline: 'none',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        {SCOPES.map(s => (
          <option key={s.value} value={s.value} style={{ background: '#12121a', color: '#e2e8f0' }}>
            {s.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={12}
        style={{
          position: 'absolute',
          right: 8,
          top: '50%',
          transform: 'translateY(-50%)',
          color: '#a78bfa',
          pointerEvents: 'none',
        }}
      />
      <span style={{ display: 'none' }}>{current?.label}</span>
    </div>
  );
}
