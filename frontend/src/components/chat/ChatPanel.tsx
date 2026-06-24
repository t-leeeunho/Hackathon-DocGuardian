import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, AlertTriangle, MessageSquare, Zap, Sparkles, Brain } from 'lucide-react';
import { CitationChip } from './CitationChip';
import { ScopeToggle } from './ScopeToggle';
import { useChat } from '../../hooks/useChat';
import type { GraphHighlightEvent, Citation, ChatAnswer } from '../../lib/types';

interface ChatPanelProps {
  onHighlight: (event: GraphHighlightEvent) => void;
  onCitationClick?: (citation: Citation) => void;
  defaultRepo?: string;
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.75 ? '#22d3a0' : value >= 0.5 ? '#f59e0b' : '#ef4444';
  const bg =
    value >= 0.75
      ? 'rgba(34,211,160,0.1)'
      : value >= 0.5
        ? 'rgba(245,158,11,0.1)'
        : 'rgba(239,68,68,0.1)';
  return (
    <span
      style={{
        padding: '2px 7px',
        borderRadius: 4,
        background: bg,
        color,
        fontSize: 11,
        fontWeight: 600,
        border: `1px solid ${color}30`,
        whiteSpace: 'nowrap',
      }}
    >
      {pct}% confident
    </span>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ padding: '12px 0' }}>
      {[80, 60, 90, 45].map((w, i) => (
        <div
          key={i}
          style={{
            height: 12,
            borderRadius: 4,
            background: 'linear-gradient(90deg, rgba(139,92,246,0.1) 0%, rgba(139,92,246,0.2) 50%, rgba(139,92,246,0.1) 100%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s infinite',
            marginBottom: 8,
            width: `${w}%`,
          }}
        />
      ))}
    </div>
  );
}

export function ChatPanel({ onHighlight, onCitationClick, defaultRepo }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const [openTraces, setOpenTraces] = useState<Record<string, boolean>>({});
  const bottomRef = useRef<HTMLDivElement>(null);
  const { messages, scope, setScope, loading, sendMessage, citationHighlight } = useChat(
    onHighlight,
    defaultRepo,
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput('');
    sendMessage(q);
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCitationClick = (citation: Citation) => {
    citationHighlight(citation);
    onCitationClick?.(citation);
  };

  // Re-blink the cited nodes AND fly the camera there (only on Show traces).
  const replayTraces = (answer: ChatAnswer) => {
    if (!answer.citations.length) return;
    onHighlight({
      reason: 'chat-evidence',
      nodeIds: [...new Set(answer.citations.map((c) => c.docId))],
      intensity: Math.max(...answer.citations.map((c) => c.relevance)),
      ttlMs: 8000,
      focus: true,
    });
  };

  const toggleTraces = (id: string, answer: ChatAnswer) => {
    setOpenTraces((prev) => ({ ...prev, [id]: !prev[id] }));
    replayTraces(answer); // always re-blink when clicked
  };

  return (
    <div
      className="glass-panel-elevated"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 16px 10px',
          borderBottom: '1px solid rgba(139,92,246,0.15)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 12px rgba(139,92,246,0.4)',
          }}
        >
          <MessageSquare size={14} color="white" />
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>DocGuardian Chat</div>
          <div style={{ fontSize: 10, color: '#64748b' }}>Evidence-backed answers</div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <ScopeToggle value={scope} onChange={setScope} />
        </div>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 12,
              opacity: 0.5,
              padding: '40px 20px',
              textAlign: 'center',
            }}
          >
            <Zap size={32} color="#8b5cf6" />
            <div style={{ fontSize: 14, color: '#94a3b8' }}>
              Ask anything about your documentation
            </div>
            <div style={{ fontSize: 11, color: '#64748b' }}>
              Answers are grounded in document evidence
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div
            key={msg.id}
            className="animate-fade-in-up"
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
              gap: 6,
            }}
          >
            {msg.role === 'user' ? (
              <div
                style={{
                  maxWidth: '85%',
                  padding: '8px 12px',
                  borderRadius: '12px 12px 2px 12px',
                  background: 'linear-gradient(135deg, rgba(139,92,246,0.25), rgba(59,130,246,0.2))',
                  border: '1px solid rgba(139,92,246,0.3)',
                  color: '#e2e8f0',
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              >
                {msg.content}
              </div>
            ) : (
              <div style={{ width: '100%' }}>
                {msg.loading ? (
                  <div
                    style={{
                      padding: '10px 12px',
                      background: 'rgba(255,255,255,0.03)',
                      borderRadius: '2px 12px 12px 12px',
                      border: '1px solid rgba(139,92,246,0.1)',
                    }}
                  >
                    <LoadingSkeleton />
                  </div>
                ) : msg.error ? (
                  <div
                    style={{
                      padding: '10px 12px',
                      background: 'rgba(239,68,68,0.08)',
                      border: '1px solid rgba(239,68,68,0.2)',
                      borderRadius: '2px 12px 12px 12px',
                      color: '#fca5a5',
                      fontSize: 12,
                      display: 'flex',
                      gap: 8,
                      alignItems: 'flex-start',
                    }}
                  >
                    <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                    {msg.error}
                  </div>
                ) : msg.answer ? (
                  <div
                    style={{
                      padding: '12px 14px',
                      background: 'rgba(255,255,255,0.03)',
                      borderRadius: '2px 12px 12px 12px',
                      border: '1px solid rgba(139,92,246,0.1)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 10,
                    }}
                  >
                    {/* Human review warning */}
                    {msg.answer.needsHumanReview && (
                      <div
                        style={{
                          padding: '8px 10px',
                          background: 'rgba(245,158,11,0.1)',
                          border: '1px solid rgba(245,158,11,0.3)',
                          borderRadius: 6,
                          display: 'flex',
                          gap: 8,
                          alignItems: 'center',
                          fontSize: 11,
                          color: '#fcd34d',
                        }}
                      >
                        <AlertTriangle size={12} />
                        <strong>Needs human review</strong> — confidence below threshold
                      </div>
                    )}

                    {/* Answer text */}
                    <div className="prose-cosmic" style={{ fontSize: 13, lineHeight: 1.6 }}>
                      <ReactMarkdown>{msg.answer.answer}</ReactMarkdown>
                    </div>

                    {/* Meta row */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <ConfidenceBadge value={msg.answer.confidence} />
                      {msg.answer.scope && (
                        <span
                          style={{
                            padding: '2px 7px',
                            borderRadius: 4,
                            background: 'rgba(59,130,246,0.1)',
                            color: '#93c5fd',
                            fontSize: 11,
                            border: '1px solid rgba(59,130,246,0.2)',
                          }}
                        >
                          {msg.answer.scope}
                        </span>
                      )}
                      {msg.answer.citations.length > 0 && (
                        <button
                          onClick={() => toggleTraces(msg.id, msg.answer!)}
                          style={{
                            marginLeft: 'auto',
                            display: 'inline-flex', alignItems: 'center', gap: 5,
                            padding: '3px 9px', borderRadius: 6, cursor: 'pointer',
                            fontSize: 11, fontWeight: 600, color: '#c4b5fd',
                            background: 'rgba(139,92,246,0.14)',
                            border: '1px solid rgba(139,92,246,0.3)',
                          }}
                        >
                          <Sparkles size={11} />
                          {openTraces[msg.id] ? 'Hide traces' : 'Show traces'}
                        </button>
                      )}
                    </div>

                    {/* Reasoning trace ("how I derived this") */}
                    {openTraces[msg.id] && msg.answer.reasoning && (
                      <div
                        style={{
                          display: 'flex', gap: 8, alignItems: 'flex-start',
                          padding: '8px 10px', borderRadius: 8,
                          background: 'rgba(139,92,246,0.06)',
                          border: '1px solid rgba(139,92,246,0.18)',
                          fontSize: 12, color: '#c4b5fd', lineHeight: 1.55,
                        }}
                      >
                        <Brain size={13} style={{ flexShrink: 0, marginTop: 1, color: '#a78bfa' }} />
                        <span><strong style={{ color: '#a78bfa' }}>Reasoning:</strong> {msg.answer.reasoning}</span>
                      </div>
                    )}

                    {/* Citations */}
                    {msg.answer.citations.length > 0 && (
                      <div>
                        <div
                          style={{
                            fontSize: 10,
                            color: '#64748b',
                            marginBottom: 6,
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                          }}
                        >
                          Evidence sources
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {msg.answer.citations.map((c, i) => (
                            <CitationChip
                              key={c.chunkId ?? `${c.docId}-${i}`}
                              citation={c}
                              index={i}
                              onClick={handleCitationClick}
                              onHover={citationHighlight}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : msg.content ? (
                  <div
                    style={{
                      padding: '10px 12px',
                      background: 'rgba(255,255,255,0.03)',
                      borderRadius: '2px 12px 12px 12px',
                      border: '1px solid rgba(139,92,246,0.1)',
                      fontSize: 13,
                      lineHeight: 1.55,
                      color: '#cbd5e1',
                    }}
                  >
                    {msg.content}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: '10px 12px 12px',
          borderTop: '1px solid rgba(139,92,246,0.15)',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'flex-end',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(139,92,246,0.2)',
            borderRadius: 10,
            padding: '8px 10px',
          }}
        >
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about your documentation…"
            rows={1}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#e2e8f0',
              fontSize: 13,
              resize: 'none',
              maxHeight: 100,
              overflowY: 'auto',
              lineHeight: 1.5,
              fontFamily: 'system-ui, sans-serif',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: input.trim() && !loading
                ? 'linear-gradient(135deg, #8b5cf6, #3b82f6)'
                : 'rgba(255,255,255,0.06)',
              border: 'none',
              cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              flexShrink: 0,
              boxShadow: input.trim() && !loading
                ? '0 0 12px rgba(139,92,246,0.4)'
                : 'none',
            }}
          >
            <Send size={14} color={input.trim() && !loading ? 'white' : '#4b5563'} />
          </button>
        </div>
      </div>
    </div>
  );
}
