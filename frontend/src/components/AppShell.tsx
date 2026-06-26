import { useState, useCallback, useEffect } from 'react';
import { FileTree } from './sidebar/FileTree';
import { DocGraph } from './graph/DocGraph';
import { ChatPanel } from './chat/ChatPanel';
import { DocumentViewer } from './panels/DocumentViewer';
import { ProposalPanel } from './panels/ProposalPanel';
import { MetricsPanel } from './panels/MetricsPanel';
import { TrendsPanel } from './panels/TrendsPanel';
import { AnalysisPanel } from './panels/AnalysisPanel';
import { DropOffArea } from './intake/DropOffArea';
import { ResizeHandle } from './ResizeHandle';
import { useGraph } from '../hooks/useGraph';
import { useHighlight } from '../hooks/useHighlight';
import { useStream } from '../hooks/useStream';
import { usePanelWidth } from '../hooks/usePanelWidth';
import { useDemo } from '../hooks/useDemo';
import { DemoControlBar } from './demo/DemoControlBar';
import { DemoCaption } from './demo/DemoCaption';
import { api, ApiError } from '../lib/api';
import { fixtureProposal } from '../lib/fixtures';
import { pickProblemTarget } from '../lib/demoScript';
import type { DocumentResponse, AgentProposal, Citation, GraphHighlightEvent, StreamEvent } from '../lib/types';
import { Activity, RefreshCw, Wifi, WifiOff, Wand2, PanelRight, X, BarChart3, Play, CheckCircle2 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export function AppShell() {
  const { data: graphData, loading: graphLoading, offline, refresh: refreshGraph } = useGraph();
  const { highlight, emit: emitHighlight, clear: clearHighlight } = useHighlight();
  const demo = useDemo();

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentResponse | null>(null);
  const [proposal, setProposal] = useState<AgentProposal | null>(null);
  const [proposalLoading, setProposalLoading] = useState(false);
  const [showProposal, setShowProposal] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const [citedDocIds, setCitedDocIds] = useState<string[]>([]);
  const [resizing, setResizing] = useState(false);
  const [showInsights, setShowInsights] = useState(false);
  const [insightsTab, setInsightsTab] = useState<'corpus' | 'doc'>('corpus');
  const [approved, setApproved] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  // Drag-resizable, persisted panel widths (compact defaults).
  const sidebar = usePanelWidth('sidebar', 220, 150, 480);
  const docPanel = usePanelWidth('doc', 380, 300, 680);
  const chat = usePanelWidth('chat', 300, 240, 600);

  const handleNodeClick = useCallback(async (docId: string) => {
    setSelectedDocId(docId);
    // Selecting a node also focuses the per-doc Insights tab (if the drawer is open).
    setInsightsTab('doc');
    try {
      const doc = await api.getDocument(docId);
      setSelectedDoc(doc);
    } catch {
      setSelectedDoc(null);
    }
  }, []);

  const handleCitationClick = useCallback((citation: Citation) => {
    handleNodeClick(citation.docId);
  }, [handleNodeClick]);

  const handleFileSelect = useCallback((path: string) => {
    handleNodeClick(path);
  }, [handleNodeClick]);

  const handlePropose = useCallback(async (docId: string) => {
    setProposalLoading(true);
    setShowProposal(true);
    setProposal(null);
    setApproved(false);
    try {
      const result = await api.propose(docId, 'Review this document for staleness and conflicts.');
      setProposal(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        // Demo fallback
        setProposal({ ...fixtureProposal, targetDocId: docId });
      } else {
        setProposal(fixtureProposal);
      }
    } finally {
      setProposalLoading(false);
    }
  }, []);

  const handleApprove = useCallback(async () => {
    setApproved(true);
    setToast('Change approved — provenance recorded.');
    window.setTimeout(() => setToast(null), 4200);
    const id = proposal?.proposalId;
    if (id) {
      try {
        await fetch(`${API_BASE}/proposals/${encodeURIComponent(id)}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approver: 'demo@docguardian' }),
        });
      } catch {
        /* offline demo — optimistic success is fine */
      }
    }
  }, [proposal]);

  const handleReject = useCallback(() => {
    setShowProposal(false);
    setProposal(null);
    setApproved(false);
  }, []);

  const handleHighlight = useCallback((event: GraphHighlightEvent) => {
    emitHighlight(event);
    // Persist the chat-referenced docs as a sidebar highlight until cleared or
    // the next answer (the graph highlight itself auto-clears on its TTL).
    if (event.reason === 'chat-evidence') {
      setCitedDocIds(event.nodeIds);
    }
  }, [emitHighlight]);

  const handleIngested = useCallback((docId: string) => {
    refreshGraph();
    handleNodeClick(docId);
  }, [refreshGraph, handleNodeClick]);

  const toggleInsights = useCallback(() => {
    setShowInsights((v) => {
      const next = !v;
      // Open onto the doc tab if something is selected, else the corpus dashboard.
      if (next) setInsightsTab(selectedDocId ? 'doc' : 'corpus');
      return next;
    });
  }, [selectedDocId]);

  // Register the guided-demo drivers so the auto-pilot can drive real handlers.
  const { registerDriver } = demo;
  useEffect(() => {
    registerDriver({
      selectDoc: handleNodeClick,
      highlight: (nodeIds, opts) =>
        handleHighlight({
          reason: 'chat-evidence',
          nodeIds,
          intensity: opts?.intensity ?? 0.9,
          ttlMs: 9000,
          focus: opts?.focus,
        }),
      clearHighlight: () => {
        clearHighlight();
        setCitedDocIds([]);
      },
      openInsights: (tab) => {
        setShowInsights(true);
        setInsightsTab(tab);
      },
      closeInsights: () => setShowInsights(false),
      propose: (docId) => {
        setShowInsights(false);
        const target = docId ?? selectedDocId;
        if (target) handlePropose(target);
      },
      approve: () => handleApprove(),
      pickProblemNode: () => pickProblemTarget(graphData),
    });
  }, [registerDriver, handleNodeClick, handleHighlight, clearHighlight, handlePropose, handleApprove, selectedDocId, graphData]);

  // Live updates: refresh the graph when the backend reports an ingest finished,
  // a graph change, or an approved proposal (README §8B WS /stream).
  useStream(useCallback((event: StreamEvent) => {
    if (
      event.type === 'graph' ||
      event.type === 'metrics' ||
      (event.type === 'ingest' && event.status === 'ready') ||
      event.type === 'proposal'
    ) {
      refreshGraph();
    }
  }, [refreshGraph]));

  const selectedNode =
    selectedDocId != null ? graphData.nodes.find((n) => n.id === selectedDocId) ?? null : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: '#0d0d12', overflow: 'hidden' }}>
      {/* ── Header ── */}
      <header
        className="glass-panel"
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          height: 48,
          borderBottom: '1px solid rgba(139,92,246,0.2)',
          flexShrink: 0,
          gap: 14,
          zIndex: 20,
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 50%, #06b6d4 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 16px rgba(139,92,246,0.5)',
            flexShrink: 0,
          }}>
            <Activity size={16} color="white" />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.01em' }}>
              DocGuardian <span style={{ color: '#8b5cf6' }}>AI</span>
            </div>
          </div>
        </div>

        {/* Status indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginLeft: 8 }}>
          {offline ? (
            <WifiOff size={12} color="#f59e0b" />
          ) : (
            <Wifi size={12} color="#22d3a0" />
          )}
          <span style={{ fontSize: 11, color: offline ? '#f59e0b' : '#22d3a0' }}>
            {offline ? 'Demo mode' : 'Live'}
          </span>
        </div>

        {/* Graph stats */}
        <div style={{ fontSize: 11, color: '#4b5563', marginLeft: 4 }}>
          {graphData.nodes.length} nodes · {graphData.edges.length} edges
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Metrics strip */}
        <MetricsPanel compact />

        {/* Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Guided demo */}
          <button
            onClick={demo.start}
            title="Run the guided auto-pilot demo"
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 12px', borderRadius: 7, fontSize: 12, fontWeight: 600,
              background: 'linear-gradient(135deg, rgba(34,211,160,0.18), rgba(59,130,246,0.14))',
              border: '1px solid rgba(34,211,160,0.35)',
              cursor: 'pointer', color: '#34d399', transition: 'all 0.2s',
            }}
          >
            <Play size={12} /> Demo
          </button>

          {/* Insights toggle */}
          <button
            onClick={toggleInsights}
            title="Toggle Insights dashboard"
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 12px', borderRadius: 7, fontSize: 12, fontWeight: 600,
              background: showInsights
                ? 'linear-gradient(135deg, rgba(139,92,246,0.25), rgba(59,130,246,0.18))'
                : 'rgba(255,255,255,0.05)',
              border: `1px solid ${showInsights ? 'rgba(139,92,246,0.4)' : 'rgba(139,92,246,0.15)'}`,
              cursor: 'pointer', color: showInsights ? '#a78bfa' : '#64748b',
              transition: 'all 0.2s',
            }}
          >
            <BarChart3 size={13} /> Insights
          </button>

          {/* Propose button for selected doc */}
          {selectedDocId && (
            <button
              onClick={() => handlePropose(selectedDocId)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '5px 12px', borderRadius: 7, fontSize: 12, fontWeight: 600,
                background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(59,130,246,0.15))',
                border: '1px solid rgba(139,92,246,0.3)',
                cursor: 'pointer', color: '#a78bfa',
                transition: 'all 0.2s',
              }}
            >
              <Wand2 size={12} /> Propose Fix
            </button>
          )}

          {/* DropOff */}
          <DropOffArea onIngested={handleIngested} />

          {/* Refresh */}
          <button
            onClick={refreshGraph}
            title="Refresh graph"
            style={{
              width: 30, height: 30, borderRadius: 7,
              background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(139,92,246,0.15)',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#64748b', transition: 'all 0.2s',
            }}
          >
            <RefreshCw size={13} />
          </button>

          {/* Toggle chat */}
          <button
            onClick={() => setChatCollapsed(c => !c)}
            title="Toggle chat"
            style={{
              width: 30, height: 30, borderRadius: 7,
              background: chatCollapsed ? 'rgba(139,92,246,0.15)' : 'rgba(255,255,255,0.05)',
              border: `1px solid ${chatCollapsed ? 'rgba(139,92,246,0.35)' : 'rgba(139,92,246,0.15)'}`,
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: chatCollapsed ? '#a78bfa' : '#64748b', transition: 'all 0.2s',
            }}
          >
            <PanelRight size={13} />
          </button>
        </div>
      </header>

      {/* ── Main body ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {/* Sidebar */}
        <div
          className="glass-panel"
          style={{
            width: sidebarCollapsed ? 0 : sidebar.width,
            minWidth: sidebarCollapsed ? 0 : sidebar.width,
            borderRight: '1px solid rgba(139,92,246,0.15)',
            overflowY: 'auto',
            overflowX: 'hidden',
            transition: resizing ? 'none' : 'width 0.3s ease, min-width 0.3s ease',
            flexShrink: 0,
            position: 'relative',
            zIndex: 5,
          }}
        >
          {!sidebarCollapsed && (
            <FileTree onFileSelect={handleFileSelect} selectedPath={selectedDocId ?? undefined} highlightedPaths={citedDocIds} />
          )}

          {/* Collapse toggle */}
          <button
            onClick={() => setSidebarCollapsed(c => !c)}
            style={{
              position: 'absolute',
              top: '50%',
              right: -10,
              transform: 'translateY(-50%)',
              width: 20,
              height: 40,
              borderRadius: '0 6px 6px 0',
              background: 'rgba(18,18,26,0.9)',
              border: '1px solid rgba(139,92,246,0.2)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#64748b',
              zIndex: 30,
              borderLeft: 'none',
            }}
          >
            <div style={{ fontSize: 8, color: '#6b7280' }}>{sidebarCollapsed ? '›' : '‹'}</div>
          </button>
        </div>

        {/* Sidebar resize handle */}
        {!sidebarCollapsed && (
          <ResizeHandle
            onResize={sidebar.resize}
            onReset={sidebar.reset}
            onDragStart={() => setResizing(true)}
            onDragEnd={() => setResizing(false)}
          />
        )}

        {/* Graph (center) */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <DocGraph
            data={graphData}
            highlight={highlight}
            onNodeClick={handleNodeClick}
            loading={graphLoading}
          />

          {/* Click to clear highlights */}
          {(highlight.nodeIds.size > 0 || citedDocIds.length > 0) && (
            <button
              onClick={() => { clearHighlight(); setCitedDocIds([]); }}
              style={{
                position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)',
                padding: '4px 12px', borderRadius: 20,
                background: 'rgba(18,18,26,0.85)', border: '1px solid rgba(139,92,246,0.3)',
                color: '#a78bfa', fontSize: 11, cursor: 'pointer', zIndex: 10,
                backdropFilter: 'blur(8px)',
              }}
            >
              <X size={10} style={{ display: 'inline', marginRight: 4 }} />
              Clear highlights
            </button>
          )}
        </div>

        {/* Right panels */}
        <div style={{ display: 'flex', gap: 0, flexShrink: 0, position: 'relative', zIndex: 5 }}>
          {/* Document viewer (AI doc + original/references toggle) */}
          {selectedDoc && (
            <>
              <ResizeHandle
                onResize={(dx) => docPanel.resize(-dx)}
                onReset={docPanel.reset}
                onDragStart={() => setResizing(true)}
                onDragEnd={() => setResizing(false)}
              />
              <DocumentViewer
                doc={selectedDoc}
                edges={graphData.edges}
                nodes={graphData.nodes}
                width={docPanel.width}
                onClose={() => { setSelectedDoc(null); setSelectedDocId(null); }}
                onNavigate={handleNodeClick}
              />
            </>
          )}

          {/* Proposal panel */}
          {showProposal && (
            <ProposalPanel
              proposal={proposal}
              loading={proposalLoading}
              onClose={() => { setShowProposal(false); setProposal(null); setApproved(false); }}
              onHighlight={handleHighlight}
              onApprove={handleApprove}
              onReject={handleReject}
              approved={approved}
            />
          )}

          {/* Insights drawer (Trends dashboard + per-doc Analysis) */}
          {showInsights && (
            <div
              className="glass-panel-elevated animate-slide-in-right"
              style={{ width: 440, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            >
              {/* Drawer header */}
              <div
                style={{
                  padding: '12px 14px',
                  borderBottom: '1px solid rgba(139,92,246,0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 0 12px rgba(139,92,246,0.4)',
                  }}
                >
                  <BarChart3 size={14} color="white" />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Insights</div>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Documentation analysis</div>
                </div>
                <button
                  onClick={() => setShowInsights(false)}
                  title="Close Insights"
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b', padding: 4, borderRadius: 4, display: 'flex' }}
                >
                  <X size={16} />
                </button>
              </div>

              {/* Tabs */}
              <div style={{ display: 'flex', gap: 6, padding: '8px 12px', borderBottom: '1px solid rgba(139,92,246,0.1)', flexShrink: 0 }}>
                <InsightsTabButton active={insightsTab === 'corpus'} onClick={() => setInsightsTab('corpus')}>
                  Corpus Trends
                </InsightsTabButton>
                <InsightsTabButton
                  active={insightsTab === 'doc'}
                  disabled={!selectedDocId}
                  onClick={() => selectedDocId && setInsightsTab('doc')}
                >
                  This Document
                </InsightsTabButton>
              </div>

              {/* Body */}
              <div style={{ flex: 1, overflowY: 'auto' }}>
                {insightsTab === 'corpus' ? (
                  <TrendsPanel onSelectDoc={handleNodeClick} />
                ) : selectedDocId ? (
                  <AnalysisPanel docId={selectedDocId} node={selectedNode} />
                ) : (
                  <div style={{ padding: 24, textAlign: 'center', color: '#64748b', fontSize: 12, lineHeight: 1.6 }}>
                    Select a document in the graph to see its analysis.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Chat panel */}
          {!chatCollapsed && (
            <>
              <ResizeHandle
                onResize={(dx) => chat.resize(-dx)}
                onReset={chat.reset}
                onDragStart={() => setResizing(true)}
                onDragEnd={() => setResizing(false)}
              />
              <div style={{ width: chat.width, borderLeft: '1px solid rgba(139,92,246,0.15)' }}>
                <ChatPanel
                  onHighlight={handleHighlight}
                  onCitationClick={handleCitationClick}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Guided demo overlays (inert unless active) */}
      <DemoCaption />
      <DemoControlBar />

      {toast && (
        <div
          className="animate-fade-in-up"
          style={{
            position: 'fixed', top: 60, left: '50%', transform: 'translateX(-50%)',
            zIndex: 1002, padding: '10px 18px', borderRadius: 10,
            background: 'rgba(34,211,160,0.14)', border: '1px solid rgba(34,211,160,0.4)',
            color: '#34d399', fontSize: 13, fontWeight: 600,
            boxShadow: '0 8px 30px rgba(0,0,0,0.45)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}
        >
          <CheckCircle2 size={15} /> {toast}
        </div>
      )}
    </div>
  );
}

function InsightsTabButton({
  active,
  disabled,
  onClick,
  children,
}: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        flex: 1,
        padding: '6px 10px',
        borderRadius: 7,
        fontSize: 12,
        fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        background: active ? 'rgba(139,92,246,0.18)' : 'transparent',
        border: `1px solid ${active ? 'rgba(139,92,246,0.4)' : 'rgba(139,92,246,0.12)'}`,
        color: disabled ? '#3f4654' : active ? '#a78bfa' : '#64748b',
        transition: 'all 0.2s',
      }}
    >
      {children}
    </button>
  );
}
