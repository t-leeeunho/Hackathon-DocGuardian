import { useState, useCallback } from 'react';
import type { ChatAnswer, Citation, GraphHighlightEvent } from '../lib/types';
import { api, ApiError } from '../lib/api';
import { fixtureChatAnswer } from '../lib/fixtures';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  answer?: ChatAnswer;
  loading?: boolean;
  error?: string;
  timestamp: Date;
}

type Scope = 'repo' | 'team' | 'company' | 'cluster' | 'summary-only' | 'source-required';

export function useChat(
  onHighlight: (event: GraphHighlightEvent) => void,
  defaultRepo?: string,
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [scope, setScope] = useState<Scope>('repo');
  const [loading, setLoading] = useState(false);

  const sendMessage = useCallback(
    async (question: string) => {
      const id = crypto.randomUUID();
      const userMsg: ChatMessage = {
        id: `u-${id}`,
        role: 'user',
        content: question,
        timestamp: new Date(),
      };
      const assistantId = `a-${id}`;
      const pendingMsg: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        loading: true,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, userMsg, pendingMsg]);
      setLoading(true);

      try {
        let answer: ChatAnswer;
        try {
          answer = await api.chat(question, defaultRepo);
        } catch (err) {
          if (err instanceof ApiError && (err.status === 503 || err.status === 0)) {
            // Offline / Azure not configured — use fixture
            answer = { ...fixtureChatAnswer, answer: fixtureChatAnswer.answer };
          } else {
            throw err;
          }
        }

        // Map citations → highlight event
        if (answer.citations.length > 0) {
          const event: GraphHighlightEvent = {
            reason: 'chat-evidence',
            nodeIds: [...new Set(answer.citations.map(c => c.docId))],
            intensity: Math.max(...answer.citations.map(c => c.relevance)),
            ttlMs: 8000,
          };
          onHighlight(event);
        }

        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, content: answer.answer, answer, loading: false }
              : m,
          ),
        );
      } catch (err) {
        const errMsg =
          err instanceof ApiError && err.status === 503
            ? 'Chat requires Azure OpenAI configuration. Running in demo mode.'
            : err instanceof Error
              ? err.message
              : 'Unknown error';

        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, content: '', loading: false, error: errMsg }
              : m,
          ),
        );
      } finally {
        setLoading(false);
      }
    },
    [defaultRepo, onHighlight],
  );

  const citationHighlight = useCallback(
    (citation: Citation) => {
      onHighlight({
        reason: 'chat-evidence',
        nodeIds: [citation.docId],
        intensity: citation.relevance,
        ttlMs: 5000,
      });
    },
    [onHighlight],
  );

  return { messages, scope, setScope, loading, sendMessage, citationHighlight };
}
