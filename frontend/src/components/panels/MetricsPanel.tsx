import { useState, useEffect } from 'react';
import { BarChart2, CheckCircle, AlertTriangle, Link, Shield, Zap } from 'lucide-react';
import { fixtureMetrics } from '../../lib/fixtures';
import type { MetricsDTO } from '../../lib/types';

function AnimatedNumber({ target }: { target: number }) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const duration = 1200;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }, [target]);

  return <span className="animate-count-up">{value}</span>;
}

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
  subtitle?: string;
}

function MetricCard({ icon, label, value, color, subtitle }: MetricCardProps) {
  return (
    <div
      style={{
        padding: '12px 14px',
        background: 'rgba(255,255,255,0.03)',
        border: `1px solid ${color}20`,
        borderRadius: 10,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flex: '1 1 auto',
        minWidth: 120,
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          background: `${color}15`,
          border: `1px solid ${color}25`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          boxShadow: `0 0 12px ${color}20`,
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 20, fontWeight: 700, color, lineHeight: 1 }}>
          <AnimatedNumber target={value} />
        </div>
        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{label}</div>
        {subtitle && <div style={{ fontSize: 10, color: '#4b5563', marginTop: 1 }}>{subtitle}</div>}
      </div>
    </div>
  );
}

interface MetricsPanelProps {
  compact?: boolean;
}

export function MetricsPanel({ compact = false }: MetricsPanelProps) {
  const metrics: MetricsDTO = fixtureMetrics;

  if (compact) {
    // Inline header strip
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {[
          { label: 'Stale', value: `${metrics.staleFixed}/${metrics.staleDetected}`, color: '#f59e0b', icon: <Zap size={11} color="#f59e0b" /> },
          { label: 'Conflicts', value: `${metrics.conflictsResolved}/${metrics.conflictsDetected}`, color: '#8b5cf6', icon: <AlertTriangle size={11} color="#8b5cf6" /> },
          { label: 'Dupes', value: metrics.duplicatesRemoved, color: '#22d3a0', icon: <CheckCircle size={11} color="#22d3a0" /> },
          { label: 'Verified', value: metrics.docsWithVerificationStamp, color: '#3b82f6', icon: <Shield size={11} color="#3b82f6" /> },
        ].map(item => (
          <div
            key={item.label}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '3px 9px', borderRadius: 5,
              background: `${item.color}10`,
              border: `1px solid ${item.color}20`,
            }}
          >
            {item.icon}
            <span style={{ fontSize: 11, color: item.color, fontWeight: 700 }}>{item.value}</span>
            <span style={{ fontSize: 10, color: '#4b5563' }}>{item.label}</span>
          </div>
        ))}
        <span style={{
          padding: '1px 5px', borderRadius: 3,
          background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.15)',
          color: '#78716c', fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em',
        }}>
          demo
        </span>
      </div>
    );
  }

  return (
    <div style={{ padding: '10px 16px 12px' }}>
      {/* Demo label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <BarChart2 size={13} color="#64748b" />
        <span style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
          Governance Metrics
        </span>
        <span style={{
          marginLeft: 'auto',
          padding: '1px 7px',
          borderRadius: 3,
          background: 'rgba(245,158,11,0.1)',
          border: '1px solid rgba(245,158,11,0.2)',
          color: '#fbbf24',
          fontSize: 9,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          Demo data
        </span>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        <MetricCard
          icon={<Zap size={16} color="#f59e0b" />}
          label="Stale Fixed"
          value={metrics.staleFixed}
          color="#f59e0b"
          subtitle={`of ${metrics.staleDetected} detected`}
        />
        <MetricCard
          icon={<Link size={16} color="#ef4444" />}
          label="Links Resolved"
          value={metrics.brokenLinksResolved}
          color="#ef4444"
        />
        <MetricCard
          icon={<AlertTriangle size={16} color="#8b5cf6" />}
          label="Conflicts Fixed"
          value={metrics.conflictsResolved}
          color="#8b5cf6"
          subtitle={`of ${metrics.conflictsDetected} found`}
        />
        <MetricCard
          icon={<CheckCircle size={16} color="#22d3a0" />}
          label="Duplicates Removed"
          value={metrics.duplicatesRemoved}
          color="#22d3a0"
        />
        <MetricCard
          icon={<Shield size={16} color="#3b82f6" />}
          label="Docs Verified"
          value={metrics.docsWithVerificationStamp}
          color="#3b82f6"
        />
      </div>
    </div>
  );
}
