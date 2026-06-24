import { useState, useCallback } from 'react';
import { FileTree } from './sidebar/FileTree';
import { DocGraph } from './graph/DocGraph';
import { ChatPanel } from './chat/ChatPanel';
import { ProvenancePanel } from './panels/ProvenancePanel';
import { ProposalPanel } from './panels/ProposalPanel';
import { MetricsPanel } from './panels/MetricsPanel';
import { DropOffArea } from './intake/DropOffArea';
import { useGraph } from '../hooks/useGraph';
import { useHighlight } from '../hooks/useHighlight';
import { api, ApiError } from '../lib/api';
import { fixtureProposal } from '../lib/fixtures';
import type { DocumentResponse, AgentProposal, Citation, GraphHighlightEvent } from '../lib/types';
import { Activity, RefreshCw, Wifi, WifiOff, Wand2, PanelRight, X } from 'lucide-react';

export function AppShell() {
  const { data: graphData, loading: graphLoading, offline, refresh: refreshGraph } = useGraph();
  const { highlight, emit: emitHighlight, clear: clearHighlight } = useHighlight();

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentResponse | null>(null);
  const [proposal, setProposal] = useState<AgentProposal | null>(null);
  const [proposalLoading, setProposalLoading] = useState(false);
  const [showProposal, setShowProposal] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatCollapsed, setChatCollapsed] = useState(false);

  const handleNodeClick = useCallback(async (docId: string) => {
    setSelectedDocId(docId);
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
    // docId is "<repoShortName>/<path>" — scope retrieval to that repo and name the
    // doc so the Curator/Guardian proposal is about THIS document, not the whole corpus.
    const repo = docId.includes('/') ? docId.split('/')[0] : undefined;
    const instruction =
      `Review "${docId}" for staleness, duplication, and conflicts with related ` +
      `documentation, and propose a single concrete fix.`;
    try {
      const result = await api.propose(docId, instruction, repo);
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

  const handleHighlight = useCallback((event: GraphHighlightEvent) => {
    emitHighlight(event);
  }, [emitHighlight]);

  const handleIngested = useCallback((docId: string) => {
    refreshGraph();
    handleNodeClick(docId);
  }, [refreshGraph, handleNodeClick]);

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
            width: sidebarCollapsed ? 0 : 256,
            minWidth: sidebarCollapsed ? 0 : 256,
            borderRight: '1px solid rgba(139,92,246,0.15)',
            overflowY: 'auto',
            overflowX: 'hidden',
            transition: 'width 0.3s ease, min-width 0.3s ease',
            flexShrink: 0,
            position: 'relative',
            zIndex: 5,
          }}
        >
          {!sidebarCollapsed && (
            <FileTree onFileSelect={handleFileSelect} selectedPath={selectedDocId ?? undefined} />
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
              zIndex: 10,
              borderLeft: 'none',
            }}
          >
            <div style={{ fontSize: 8, color: '#6b7280' }}>{sidebarCollapsed ? '›' : '‹'}</div>
          </button>
        </div>

        {/* Graph (center) */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <DocGraph
            data={graphData}
            highlight={highlight}
            onNodeClick={handleNodeClick}
            loading={graphLoading}
          />

          {/* Click to clear highlights */}
          {highlight.nodeIds.size > 0 && (
            <button
              onClick={clearHighlight}
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
          {/* Provenance panel */}
          {selectedDoc && (
            <ProvenancePanel
              doc={selectedDoc}
              onClose={() => { setSelectedDoc(null); setSelectedDocId(null); }}
            />
          )}

          {/* Proposal panel */}
          {showProposal && (
            <ProposalPanel
              proposal={proposal}
              loading={proposalLoading}
              onClose={() => { setShowProposal(false); setProposal(null); }}
              onHighlight={handleHighlight}
            />
          )}

          {/* Chat panel */}
          {!chatCollapsed && (
            <div style={{ width: 360, borderLeft: '1px solid rgba(139,92,246,0.15)' }}>
              <ChatPanel
                onHighlight={handleHighlight}
                onCitationClick={handleCitationClick}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
