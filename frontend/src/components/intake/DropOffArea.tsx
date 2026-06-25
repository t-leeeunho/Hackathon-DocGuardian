import { useState, useRef } from 'react';
import { Upload, FileText, Zap, X, CheckCircle, AlertTriangle, Sparkles, FolderTree, Globe, Link2 } from 'lucide-react';
import { api, ApiError } from '../../lib/api';
import type { DocumentIntakeResponse, UrlIngestResult } from '../../lib/types';

type QueuedDoc = {
  filename: string;
  content: string;
};

type BatchSummary = {
  total: number;
  succeeded: number;
  failed: number;
  failures: string[];
};

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
  const [mode, setMode] = useState<'doc' | 'url'>('doc');
  const [text, setText] = useState('');
  const [filename, setFilename] = useState('');
  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState(8);
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentIntakeResponse | null>(null);
  const [queuedDocs, setQueuedDocs] = useState<QueuedDoc[]>([]);
  const [batchSummary, setBatchSummary] = useState<BatchSummary | null>(null);
  const [urlResult, setUrlResult] = useState<UrlIngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setText('');
    setFilename('');
    setUrl('');
    setResult(null);
    setQueuedDocs([]);
    setBatchSummary(null);
    setUrlResult(null);
    setProgress(null);
    setError(null);
  };

  const isSupportedTextFile = (file: File) => {
    const name = file.name.toLowerCase();
    return file.type.startsWith('text/') || name.endsWith('.md') || name.endsWith('.txt');
  };

  const readDocsFromFiles = async (files: File[]): Promise<QueuedDoc[]> => {
    const supported = files.filter((f) => isSupportedTextFile(f));
    const docs = await Promise.all(
      supported.map(async (file) => {
        const withPath = file as File & { webkitRelativePath?: string };
        const relPath = withPath.webkitRelativePath?.trim();
        const filenameWithPath = relPath && relPath.length > 0 ? relPath : file.name;
        const content = await file.text();
        return { filename: filenameWithPath, content };
      }),
    );
    return docs.filter((d) => d.content.trim().length > 0);
  };

  const uploadFolder = () => {
    const picker = document.createElement('input');
    picker.type = 'file';
    picker.multiple = true;
    picker.accept = '.md,.txt,text/*';
    (picker as HTMLInputElement & { webkitdirectory?: boolean }).webkitdirectory = true;
    picker.onchange = async () => {
      const files = Array.from(picker.files ?? []);
      if (!files.length) return;
      setError(null);
      setResult(null);
      setBatchSummary(null);
      try {
        const docs = await readDocsFromFiles(files);
        if (!docs.length) {
          setQueuedDocs([]);
          setError('No supported text or markdown files found in that folder.');
          return;
        }
        setText('');
        setFilename('');
        setQueuedDocs(docs);
      } catch {
        setError('Failed to read folder files.');
      }
    };
    picker.click();
  };

  const ingestAsyncJob = async (docContent: string, docFilename?: string) => {
    const job = await api.ingestDocumentAsync(docContent, docFilename || undefined);
    let current = job;
    while (current.status === 'queued' || current.status === 'processing') {
      await new Promise((r) => setTimeout(r, 800));
      current = await api.getJob(job.jobId);
    }
    if (current.status === 'succeeded' && current.result) {
      return current.result as DocumentIntakeResponse;
    }
    throw new Error(current.error || 'Ingestion failed and was rolled back.');
  };

  const submit = async () => {
    if (!text.trim() && queuedDocs.length === 0) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    setBatchSummary(null);
    try {
      if (queuedDocs.length > 0) {
        const failures: string[] = [];
        const total = queuedDocs.length;
        let succeeded = 0;
        let firstDocId: string | null = null;

        for (let i = 0; i < queuedDocs.length; i += 1) {
          const doc = queuedDocs[i];
          setProgress(`Ingesting ${i + 1}/${total}: ${doc.filename}`);
          try {
            const res = await ingestAsyncJob(doc.content, doc.filename);
            succeeded += 1;
            if (!firstDocId) firstDocId = res.docId;
            setResult(res);
          } catch (err) {
            const msg = err instanceof Error ? err.message : 'Failed to ingest document.';
            failures.push(`${doc.filename}: ${msg}`);
          }
        }

        const failed = total - succeeded;
        setBatchSummary({ total, succeeded, failed, failures });
        if (failed === total) {
          setError('Folder ingest failed. See failures below.');
        }
        if (firstDocId) onIngested?.(firstDocId);
      } else {
        const res = await ingestAsyncJob(text, filename || undefined);
        setResult(res);
        onIngested?.(res.docId);
      }
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
      setProgress(null);
    }
  };

  const submitUrl = async () => {
    const u = url.trim();
    if (!u || submitting) return;
    setSubmitting(true);
    setError(null);
    setUrlResult(null);
    setResult(null);
    setProgress('Crawling the site…');
    try {
      const job = await api.ingestUrl(u, maxPages);
      let current = job;
      while (current.status === 'queued' || current.status === 'processing') {
        await new Promise((r) => setTimeout(r, 1000));
        current = await api.getJob(job.jobId);
        if (current.message) setProgress(current.message);
      }
      if (current.status === 'succeeded' && current.result) {
        const res = current.result as UrlIngestResult;
        setUrlResult(res);
        if (res.docs?.length) onIngested?.(res.docs[0].docId);
      } else {
        setError(current.error || 'Import failed.');
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError('Backend not reachable.');
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to import from URL.');
      }
    } finally {
      setSubmitting(false);
      setProgress(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = Array.from(e.dataTransfer.files ?? []);
    if (!dropped.length) return;

    setError(null);
    setResult(null);
    setBatchSummary(null);

    if (dropped.length === 1 && !((dropped[0] as File & { webkitRelativePath?: string }).webkitRelativePath)) {
      const file = dropped[0];
      if (!isSupportedTextFile(file)) {
        setError('Only text and markdown files are supported.');
        return;
      }
      setQueuedDocs([]);
      setFilename(file.name);
      file.text().then(setText).catch(() => setError('Failed to read file.'));
      return;
    }

    readDocsFromFiles(dropped)
      .then((docs) => {
        if (!docs.length) {
          setQueuedDocs([]);
          setError('No supported text or markdown files found in the dropped folder/files.');
          return;
        }
        setText('');
        setFilename('');
        setQueuedDocs(docs);
      })
      .catch(() => setError('Failed to read dropped folder/files.'));
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setQueuedDocs([]);
    setBatchSummary(null);
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
        width: 'min(620px, 100vw)',
        maxWidth: '100vw',
        height: '100vh',
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
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Add Documentation</div>
          <div style={{ fontSize: 10, color: '#64748b' }}>Paste, upload, or import from a URL</div>
        </div>
        <button
          onClick={() => { setOpen(false); reset(); }}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b', padding: 4, borderRadius: 4 }}
        >
          <X size={16} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Source mode toggle */}
        <div style={{ display: 'flex', gap: 6, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(139,92,246,0.15)', borderRadius: 8, padding: 4 }}>
          {([['doc', 'Document', FileText], ['url', 'Website URL', Globe]] as const).map(([m, label, Icon]) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(null); }}
              style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                padding: '6px 8px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', border: 'none',
                background: mode === m ? 'linear-gradient(135deg, rgba(139,92,246,0.25), rgba(59,130,246,0.2))' : 'transparent',
                color: mode === m ? '#c4b5fd' : '#64748b', transition: 'all 0.15s',
              }}
            >
              <Icon size={13} /> {label}
            </button>
          ))}
        </div>

        {mode === 'doc' && (
          <>
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
            Drag & drop files/folders or <span style={{ color: '#a78bfa', textDecoration: 'underline' }}>click to browse</span>
          </div>
          <div style={{ fontSize: 11, color: '#4b5563' }}>Markdown and plain text only. Folders supported.</div>
          <input
            ref={fileRef}
            type="file"
            accept=".md,.txt,text/*"
            style={{ display: 'none' }}
            onChange={handleFileInput}
          />
        </div>

        <button
          onClick={uploadFolder}
          style={{
            width: '100%',
            padding: '8px 10px',
            borderRadius: 8,
            fontSize: 12,
            fontWeight: 600,
            background: 'rgba(59,130,246,0.1)',
            border: '1px solid rgba(59,130,246,0.25)',
            color: '#93c5fd',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <FolderTree size={13} /> Upload Folder
        </button>

        {queuedDocs.length > 0 && (
          <div style={{ padding: '10px 12px', borderRadius: 8, background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 12, color: '#bfdbfe', fontWeight: 600 }}>
              {queuedDocs.length} file{queuedDocs.length !== 1 ? 's' : ''} queued from folder
            </div>
            <div style={{ maxHeight: 100, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {queuedDocs.slice(0, 8).map((doc) => (
                <div key={doc.filename} style={{ fontSize: 11, color: '#93c5fd', fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {doc.filename}
                </div>
              ))}
              {queuedDocs.length > 8 && (
                <div style={{ fontSize: 10, color: '#60a5fa' }}>+{queuedDocs.length - 8} more</div>
              )}
            </div>
          </div>
        )}

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
          </>
        )}

        {mode === 'url' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ border: '2px dashed rgba(139,92,246,0.2)', borderRadius: 10, padding: '18px 16px', textAlign: 'center', background: 'rgba(255,255,255,0.02)' }}>
              <Globe size={26} color="#6b7280" style={{ margin: '0 auto 8px' }} />
              <div style={{ fontSize: 13, color: '#94a3b8' }}>Import a docs site by URL</div>
              <div style={{ fontSize: 11, color: '#4b5563', marginTop: 4 }}>
                Crawls the page <strong>and its sub-pages</strong>, then the Librarian rewrites &amp; files each one.
              </div>
            </div>

            <div>
              <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 4 }}>Website URL</label>
              <input
                value={url}
                onChange={e => setUrl(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') submitUrl(); }}
                placeholder="https://microsoft.github.io/garnet/docs"
                style={{
                  width: '100%', padding: '8px 10px', background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(139,92,246,0.15)', borderRadius: 6, color: '#e2e8f0',
                  fontSize: 12, outline: 'none', fontFamily: 'monospace',
                }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <label style={{ fontSize: 11, color: '#64748b' }}>Max pages</label>
              <input
                type="number" min={1} max={40} value={maxPages}
                onChange={e => setMaxPages(Math.max(1, Math.min(40, Number(e.target.value) || 8)))}
                style={{
                  width: 64, padding: '5px 8px', background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(139,92,246,0.15)', borderRadius: 6, color: '#e2e8f0', fontSize: 12, outline: 'none',
                }}
              />
              <span style={{ fontSize: 10, color: '#475569' }}>follows links under the URL's path</span>
            </div>

            <button
              onClick={() => setUrl('https://microsoft.github.io/garnet/docs')}
              style={{
                padding: '6px 10px', borderRadius: 6, fontSize: 11, background: 'rgba(59,130,246,0.08)',
                border: '1px solid rgba(59,130,246,0.2)', color: '#93c5fd', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 5, justifyContent: 'center',
              }}
            >
              <Link2 size={11} /> Use Garnet docs sample
            </button>
          </div>
        )}

        {/* Live progress */}
        {submitting && progress && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#a78bfa', padding: '8px 10px', background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.18)', borderRadius: 8 }}>
            <div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(139,92,246,0.2)', borderTopColor: '#8b5cf6', animation: 'spin 1s linear infinite', flexShrink: 0 }} />
            {progress}
          </div>
        )}

        {/* URL import result */}
        {urlResult && (
          <div style={{ padding: '12px 14px', background: 'rgba(34,211,160,0.08)', border: '1px solid rgba(34,211,160,0.2)', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#34d399', fontSize: 13, fontWeight: 600 }}>
              <CheckCircle size={16} /> Imported {urlResult.imported} page{urlResult.imported !== 1 ? 's' : ''}
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              from <code style={{ color: '#93c5fd', fontFamily: 'monospace' }}>{urlResult.startUrl}</code> → filed under <code style={{ color: '#a78bfa', fontFamily: 'monospace' }}>{urlResult.namespace}/</code>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 170, overflowY: 'auto' }}>
              {urlResult.docs.map(d => (
                <button
                  key={d.docId}
                  onClick={() => onIngested?.(d.docId)}
                  title={d.url}
                  style={{ textAlign: 'left', display: 'flex', alignItems: 'center', gap: 6, padding: '5px 8px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 6, cursor: 'pointer', width: '100%' }}
                >
                  <Sparkles size={11} color="#c084fc" style={{ flexShrink: 0 }} />
                  <span style={{ fontSize: 11, color: '#cbd5e1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.title || d.docId.split('/').pop()}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: '#475569', flexShrink: 0 }}>{d.chunks}c</span>
                </button>
              ))}
            </div>
            {urlResult.errors && urlResult.errors.length > 0 && (
              <div style={{ fontSize: 10, color: '#fca5a5' }}>{urlResult.errors.length} page(s) failed to import</div>
            )}
          </div>
        )}

        {/* Result */}
        {mode === 'doc' && result && (
          <div style={{
            padding: '12px 14px',
            background: 'rgba(34,211,160,0.08)',
            border: '1px solid rgba(34,211,160,0.2)',
            borderRadius: 8,
            display: 'flex', flexDirection: 'column', gap: 8,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#34d399', fontSize: 13, fontWeight: 600 }}>
              <CheckCircle size={16} /> Ingested successfully
            </div>

            {result.aiRewritten && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 11, color: '#c4b5fd',
                background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)',
                borderRadius: 6, padding: '5px 8px',
              }}>
                <Sparkles size={12} /> Rewritten into an AI-agent-friendly document
              </div>
            )}

            {result.title && (
              <div style={{ fontSize: 12, color: '#e2e8f0', fontWeight: 600 }}>{result.title}</div>
            )}

            {/* Where the agent filed it */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94a3b8' }}>
              <FolderTree size={12} color="#64748b" />
              {result.originalPath && result.suggestedPath && result.originalPath !== result.suggestedPath ? (
                <span>
                  <code style={{ color: '#fca5a5', fontFamily: 'monospace' }}>{result.originalPath}</code>
                  <span style={{ color: '#475569' }}> → </span>
                  <code style={{ color: '#6ee7b7', fontFamily: 'monospace' }}>{result.suggestedPath}</code>
                </span>
              ) : (
                <code style={{ color: '#a78bfa', fontFamily: 'monospace' }}>{result.docId}</code>
              )}
            </div>

            {result.rationale && (
              <div style={{ fontSize: 11, color: '#64748b', lineHeight: 1.5 }}>{result.rationale}</div>
            )}

            <div style={{ fontSize: 11, color: '#64748b' }}>
              {result.chunks} chunks · {result.edges} edges
              {result.category ? <> · <span style={{ color: '#93c5fd' }}>{result.category}</span></> : null}
            </div>
          </div>
        )}

        {mode === 'doc' && batchSummary && (
          <div style={{
            padding: '12px 14px',
            background: batchSummary.failed > 0 ? 'rgba(245,158,11,0.08)' : 'rgba(34,211,160,0.08)',
            border: `1px solid ${batchSummary.failed > 0 ? 'rgba(245,158,11,0.25)' : 'rgba(34,211,160,0.2)'}`,
            borderRadius: 8,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: batchSummary.failed > 0 ? '#fcd34d' : '#34d399', fontSize: 13, fontWeight: 600 }}>
              {batchSummary.failed > 0 ? <AlertTriangle size={16} /> : <CheckCircle size={16} />}
              Folder ingest complete
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              {batchSummary.succeeded}/{batchSummary.total} succeeded
              {batchSummary.failed > 0 ? ` · ${batchSummary.failed} failed` : ''}
            </div>
            {batchSummary.failures.length > 0 && (
              <div style={{ maxHeight: 120, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
                {batchSummary.failures.map((failure) => (
                  <div key={failure} style={{ fontSize: 10, color: '#fca5a5', fontFamily: 'monospace' }}>{failure}</div>
                ))}
              </div>
            )}
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
        {(() => {
          const canSubmit = mode === 'url' ? Boolean(url.trim()) : Boolean(text.trim()) || queuedDocs.length > 0;
          const active = canSubmit && !submitting;
          return (
            <button
              onClick={mode === 'url' ? submitUrl : submit}
              disabled={!active}
              style={{
                width: '100%', padding: '9px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
                background: active ? 'linear-gradient(135deg, #8b5cf6, #3b82f6)' : 'rgba(255,255,255,0.06)',
                border: 'none', cursor: active ? 'pointer' : 'not-allowed',
                color: active ? 'white' : '#4b5563',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                boxShadow: active ? '0 0 20px rgba(139,92,246,0.3)' : 'none',
                transition: 'all 0.2s',
              }}
            >
              {submitting ? (
                <>
                  <div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.2)', borderTopColor: 'white', animation: 'spin 1s linear infinite' }} />
                  {mode === 'url' ? 'Importing…' : 'Ingesting…'}
                </>
              ) : mode === 'url' ? (
                <>
                  <Globe size={14} /> Import from URL
                </>
              ) : (
                <>
                  <Upload size={14} /> Ingest Document
                </>
              )}
            </button>
          );
        })()}
      </div>
    </div>
  );
}
