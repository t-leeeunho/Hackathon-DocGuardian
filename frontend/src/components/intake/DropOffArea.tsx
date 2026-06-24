import { useState, useRef } from 'react';
import { Upload, FileText, Zap, X, CheckCircle, AlertTriangle } from 'lucide-react';
import { api, ApiError } from '../../lib/api';
import type { DocumentIntakeResponse } from '../../lib/types';

interface DropOffAreaProps {
  onIngested?: (docId: string) => void;
}

const SAMPLE_CONFLICT = `# Deployment Guide — v1.2

## Requirements

Run the following to install dependencies:

\`\`\`bash
pip install -r requirements.txt
python setup.py install
\`\`\`

## Starting the Server

Use this command (legacy):

\`\`\`bash
python manage.py runserver --port 8080
\`\`\`

> NOTE: Some scripts still reference \`npm run dev\` — this is outdated.
`;

const SAMPLE_STALE = `# API Authentication

Last updated: March 2022

## Using API Keys

Send your API key in the \`Authorization\` header:

\`\`\`
Authorization: Bearer <your-api-key>
\`\`\`

The old v1 endpoint \`/api/v1/auth\` is still documented here but has been
decommissioned since Q4 2023. The current endpoint is \`/api/v3/auth\`.
`;

export function DropOffArea({ onIngested }: DropOffAreaProps) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [filename, setFilename] = useState('');
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<DocumentIntakeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setText('');
    setFilename('');
    setResult(null);
    setError(null);
  };

  const submit = async () => {
    if (!text.trim()) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.ingestDocument(text, filename || undefined);
      setResult(res);
      onIngested?.(res.docId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 415) {
        setError('Unsupported file format — text/markdown only.');
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to ingest document.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    if (!file.type.startsWith('text/') && !file.name.endsWith('.md') && !file.name.endsWith('.txt')) {
      setError('Only text and markdown files are supported.');
      return;
    }
    setFilename(file.name);
    file.text().then(setText).catch(() => setError('Failed to read file.'));
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFilename(file.name);
    file.text().then(setText).catch(() => setError('Failed to read file.'));
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 14px',
          background: 'linear-gradient(135deg, rgba(139,92,246,0.15), rgba(59,130,246,0.1))',
          border: '1px solid rgba(139,92,246,0.3)',
          borderRadius: 8,
          cursor: 'pointer',
          color: '#a78bfa',
          fontSize: 13,
          fontWeight: 600,
          transition: 'all 0.2s',
          boxShadow: '0 0 12px rgba(139,92,246,0.1)',
        }}
        onMouseOver={e => {
          (e.currentTarget as HTMLElement).style.boxShadow = '0 0 20px rgba(139,92,246,0.3)';
          (e.currentTarget as HTMLElement).style.borderColor = 'rgba(139,92,246,0.5)';
        }}
        onMouseOut={e => {
          (e.currentTarget as HTMLElement).style.boxShadow = '0 0 12px rgba(139,92,246,0.1)';
          (e.currentTarget as HTMLElement).style.borderColor = 'rgba(139,92,246,0.3)';
        }}
      >
        <Upload size={14} />
        Drop Document
      </button>
    );
  }

  return (
    <div
      className="glass-panel-elevated animate-slide-in-right"
      style={{
        position: 'fixed',
        right: 0,
        top: 0,
        bottom: 0,
        width: 440,
        zIndex: 50,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid rgba(139,92,246,0.15)',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        flexShrink: 0,
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 12px rgba(99,102,241,0.4)',
        }}>
          <Upload size={14} color="white" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Drop Document</div>
          <div style={{ fontSize: 10, color: '#64748b' }}>Ingest into DocGuardian</div>
        </div>
        <button
          onClick={() => { setOpen(false); reset(); }}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b', padding: 4, borderRadius: 4 }}
        >
          <X size={16} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          style={{
            border: `2px dashed ${dragging ? 'rgba(139,92,246,0.6)' : 'rgba(139,92,246,0.2)'}`,
            borderRadius: 10,
            padding: '20px 16px',
            textAlign: 'center',
            cursor: 'pointer',
            background: dragging ? 'rgba(139,92,246,0.08)' : 'rgba(255,255,255,0.02)',
            transition: 'all 0.2s',
          }}
        >
          <FileText size={28} color="#6b7280" style={{ margin: '0 auto 8px' }} />
          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 4 }}>
            Drag & drop a file or <span style={{ color: '#a78bfa', textDecoration: 'underline' }}>click to browse</span>
          </div>
          <div style={{ fontSize: 11, color: '#4b5563' }}>Markdown and plain text only</div>
          <input
            ref={fileRef}
            type="file"
            accept=".md,.txt,text/*"
            style={{ display: 'none' }}
            onChange={handleFileInput}
          />
        </div>

        {/* Filename */}
        <div>
          <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 4 }}>
            Filename (optional)
          </label>
          <input
            value={filename}
            onChange={e => setFilename(e.target.value)}
            placeholder="my-document.md"
            style={{
              width: '100%',
              padding: '7px 10px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(139,92,246,0.15)',
              borderRadius: 6,
              color: '#e2e8f0',
              fontSize: 12,
              outline: 'none',
              fontFamily: 'monospace',
            }}
          />
        </div>

        {/* Textarea */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 4 }}>
            Or paste text directly
          </label>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Paste documentation content here…"
            style={{
              flex: 1,
              minHeight: 180,
              padding: '10px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(139,92,246,0.15)',
              borderRadius: 6,
              color: '#e2e8f0',
              fontSize: 12,
              resize: 'vertical',
              fontFamily: 'monospace',
              outline: 'none',
              lineHeight: 1.6,
            }}
          />
        </div>

        {/* Sample buttons */}
        <div>
          <div style={{ fontSize: 11, color: '#4b5563', marginBottom: 6 }}>Demo samples:</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => { setText(SAMPLE_CONFLICT); setFilename('deploy-conflict.md'); }}
              style={{
                flex: 1, padding: '6px 10px', borderRadius: 6, fontSize: 11,
                background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                color: '#fca5a5', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                justifyContent: 'center',
              }}
            >
              <Zap size={11} /> Conflict Doc
            </button>
            <button
              onClick={() => { setText(SAMPLE_STALE); setFilename('auth-stale.md'); }}
              style={{
                flex: 1, padding: '6px 10px', borderRadius: 6, fontSize: 11,
                background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)',
                color: '#fcd34d', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={11} /> Stale Doc
            </button>
          </div>
        </div>

        {/* Result */}
        {result && (
          <div style={{
            padding: '12px 14px',
            background: 'rgba(34,211,160,0.08)',
            border: '1px solid rgba(34,211,160,0.2)',
            borderRadius: 8,
            display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#34d399', fontSize: 13, fontWeight: 600 }}>
              <CheckCircle size={16} /> Ingested successfully
            </div>
            <div style={{ fontSize: 12, color: '#94a3b8' }}>
              <code style={{ color: '#a78bfa', fontFamily: 'monospace' }}>{result.docId}</code>
            </div>
            <div style={{ fontSize: 11, color: '#64748b' }}>
              {result.chunks} chunks · {result.edges} edges
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            padding: '10px 12px',
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.2)',
            borderRadius: 8,
            display: 'flex', gap: 8, alignItems: 'flex-start',
            color: '#fca5a5', fontSize: 12,
          }}>
            <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
            {error}
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{ padding: '10px 16px', borderTop: '1px solid rgba(139,92,246,0.1)', flexShrink: 0 }}>
        <button
          onClick={submit}
          disabled={!text.trim() || submitting}
          style={{
            width: '100%', padding: '9px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
            background: text.trim() && !submitting
              ? 'linear-gradient(135deg, #8b5cf6, #3b82f6)'
              : 'rgba(255,255,255,0.06)',
            border: 'none', cursor: text.trim() && !submitting ? 'pointer' : 'not-allowed',
            color: text.trim() && !submitting ? 'white' : '#4b5563',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            boxShadow: text.trim() && !submitting ? '0 0 20px rgba(139,92,246,0.3)' : 'none',
            transition: 'all 0.2s',
          }}
        >
          {submitting ? (
            <>
              <div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.2)', borderTopColor: 'white', animation: 'spin 1s linear infinite' }} />
              Ingesting…
            </>
          ) : (
            <>
              <Upload size={14} />
              Ingest Document
            </>
          )}
        </button>
      </div>
    </div>
  );
}
