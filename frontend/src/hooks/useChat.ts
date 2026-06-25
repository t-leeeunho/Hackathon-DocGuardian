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

// Greetings / chit-chat shouldn't burn an Azure call — answer them locally.
const TRIVIAL = /^(hi|hello|hey|yo|hiya|sup|what'?s up|how are you|how'?s it going|thanks|thank you|thx|ty|ok|okay|cool|nice|lol|good (morning|afternoon|evening|night)|test|ping)\b[!.?]*$/i;

function isTrivial(q: string): boolean {
  return TRIVIAL.test(q.trim());
}

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

      // Trivial greeting -> instant local reply, no API / no Azure credit.
      if (isTrivial(question)) {
        const greeting: ChatMessage = {
          id: `a-${id}`,
          role: 'assistant',
          content:
            "\uD83D\uDC4B Hi! I'm DocGuardian's documentation assistant. Ask me about a " +
            'project\u2019s setup, build, configuration, or APIs — e.g. “How do I build ' +
            'Garnet from source?”',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, userMsg, greeting]);
        return;
      }

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
            focus: true,
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
