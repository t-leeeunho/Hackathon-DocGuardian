import { Sparkles, Play, Compass, MessageSquareText, Upload, Network } from 'lucide-react';
import { useTour } from '../../hooks/useTour';
import { useDemo } from '../../hooks/useDemo';
import { SpotlightOverlay } from './SpotlightOverlay';

/**
 * First-run experience. Shows a welcome card that offers either a hands-on coach-
 * mark tour or the auto-pilot demo, then drives the `SpotlightOverlay` through the
 * tour steps. Inert once dismissed, and never competes with the running demo.
 */
const FEATURES = [
  { icon: Network, text: 'A living knowledge graph of all your docs' },
  { icon: MessageSquareText, text: 'Grounded answers with citations — evidence or silence' },
  { icon: Upload, text: 'Drop in docs or URLs; we rewrite & file them' },
];

export function WelcomeTour() {
  const tour = useTour();
  const demo = useDemo();

  // The demo owns the screen when it's running.
  if (demo.active) return null;
  if (tour.phase === 'off') return null;

  if (tour.phase === 'steps' && tour.step) {
    return (
      <SpotlightOverlay
        anchor={tour.step.anchor}
        title={tour.step.title}
        body={tour.step.body}
        step={tour.index + 1}
        total={tour.total}
        onNext={tour.next}
        onBack={tour.prev}
        onSkip={tour.skip}
      />
    );
  }

  // phase === 'welcome'
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1400,
        background: 'rgba(8,8,12,0.74)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        className="glass-panel-elevated animate-fade-in-up"
        style={{
          width: 'min(460px, 100%)',
          padding: '26px 26px 22px',
          borderRadius: 18,
          border: '1px solid rgba(139,92,246,0.4)',
          background: 'rgba(13,13,18,0.97)',
          boxShadow: '0 24px 70px rgba(0,0,0,0.6), 0 0 40px rgba(139,92,246,0.18)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 11,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 50%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(139,92,246,0.5)',
              flexShrink: 0,
            }}
          >
            <Sparkles size={20} color="white" />
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.01em' }}>
              Welcome to DocGuardian <span style={{ color: '#a78bfa' }}>AI</span>
            </div>
            <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
              The docs that govern themselves.
            </div>
          </div>
        </div>

        <div style={{ fontSize: 13, lineHeight: 1.55, color: '#cbd5e1', marginBottom: 16 }}>
          DocGuardian ingests your engineering docs, detects what's stale, duplicate or
          conflicting, and proposes evidence-backed fixes you approve. Here's what you can do:
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
          {FEATURES.map(({ icon: Icon, text }) => (
            <div key={text} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: 7,
                  background: 'rgba(139,92,246,0.14)',
                  border: '1px solid rgba(139,92,246,0.28)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Icon size={14} color="#a78bfa" />
              </div>
              <span style={{ fontSize: 12.5, color: '#cbd5e1' }}>{text}</span>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={tour.beginTour}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 7,
              flex: 1,
              padding: '11px 16px',
              borderRadius: 10,
              background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
              border: 'none',
              cursor: 'pointer',
              color: 'white',
              fontSize: 13,
              fontWeight: 700,
              boxShadow: '0 0 18px rgba(139,92,246,0.4)',
            }}
          >
            <Compass size={15} /> Take the quick tour
          </button>
          <button
            onClick={() => {
              tour.skip();
              demo.start();
            }}
            title="Watch the auto-pilot demo"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '11px 14px',
              borderRadius: 10,
              background: 'rgba(34,211,160,0.14)',
              border: '1px solid rgba(34,211,160,0.32)',
              cursor: 'pointer',
              color: '#34d399',
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            <Play size={14} /> Demo
          </button>
        </div>

        <button
          onClick={tour.skip}
          style={{
            display: 'block',
            margin: '12px auto 0',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: '#64748b',
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          Skip — I'll explore on my own
        </button>
      </div>
    </div>
  );
}
