import React, { useEffect, useState, useRef } from 'react';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import { 
  Plus, 
  Trash2, 
  Send, 
  MessageSquare, 
  Compass, 
  Info,
  BookOpen,
  User,
  Cpu,
  Brain,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  FileText
} from 'lucide-react';

interface ChatSession {
  session_uuid: string;
  title: string;
  created_at: string;
}

interface ChatMessage {
  id: number;
  sender_type: 'user' | 'assistant';
  content: string;
  rag_sources?: any[];
  latency_ms?: number;
  tokens_used?: number;
}

export const AIAssistant: React.FC = () => {
  const { user } = useAuthStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionUuid, setActiveSessionUuid] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSourcesForMsg, setShowSourcesForMsg] = useState<number | null>(null);

  // Ticket Helper States
  const [ticketId, setTicketId] = useState('');
  const [ticketHelperResult, setTicketHelperResult] = useState<any | null>(null);
  const [helperLoading, setHelperLoading] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (activeSessionUuid) {
      fetchMessages(activeSessionUuid);
    } else {
      setMessages([]);
    }
  }, [activeSessionUuid]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchSessions = async () => {
    try {
      const response = await api.get('/ai/sessions');
      setSessions(response.data.data);
      if (response.data.data.length > 0 && !activeSessionUuid) {
        setActiveSessionUuid(response.data.data[0].session_uuid);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMessages = async (sessionUuid: string) => {
    try {
      const response = await api.get(`/ai/sessions/${sessionUuid}`);
      const backendMessages = response.data.data || [];
      const formatted = backendMessages.map((m: any) => ({
        id: m.id,
        sender_type: m.role,
        content: m.content,
        rag_sources: m.rag_sources,
        latency_ms: m.latency_ms,
        tokens_used: m.tokens_used
      }));
      setMessages(formatted);
    } catch (e) {
      console.error(e);
    }
  };

  const startNewChat = () => {
    setActiveSessionUuid(null);
    setMessages([]);
  };

  const handleDeleteSession = async (uuid: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/ai/sessions/${uuid}`);
      setSessions(prev => prev.filter(s => s.session_uuid !== uuid));
      if (activeSessionUuid === uuid) {
        startNewChat();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;

    const userMessageContent = inputText;
    setInputText('');
    setIsLoading(true);

    // Append user message locally
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      sender_type: 'user',
      content: userMessageContent
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const response = await api.post('/ai/chat', {
        query: userMessageContent,
        session_uuid: activeSessionUuid || undefined
      });

      const data = response.data.data;
      if (!activeSessionUuid && data.session_uuid) {
        setActiveSessionUuid(data.session_uuid);
        fetchSessions();
      }

      // Add assistant response
      const assistantMsg: ChatMessage = {
        id: Date.now() + 1,
        sender_type: 'assistant',
        content: data.response,
        rag_sources: data.sources,
        latency_ms: data.latency_ms,
        tokens_used: data.tokens_used
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Ticket Assistant helper triggers
  const handleTriage = async () => {
    if (!ticketId) return;
    setHelperLoading(true);
    setTicketHelperResult(null);
    try {
      const response = await api.get(`/ai/tickets/${ticketId}/classification`);
      setTicketHelperResult({ type: 'triage', data: response.data.data });
    } catch (err: any) {
      // Try classifying fresh
      try {
        const response = await api.post(`/ai/tickets/${ticketId}/classify`);
        setTicketHelperResult({ type: 'triage', data: response.data.data });
      } catch (innerErr: any) {
        setTicketHelperResult({ type: 'error', message: innerErr.response?.data?.error?.message || 'Error executing AI classification' });
      }
    } finally {
      setHelperLoading(false);
    }
  };

  const handleTriageFeedback = async (accepted: boolean) => {
    if (!ticketId || !ticketHelperResult?.data) return;
    try {
      await api.post(`/ai/tickets/${ticketId}/classification/feedback`, {
        accepted,
        override_category: ticketHelperResult.data.predicted_category,
        override_priority: ticketHelperResult.data.predicted_priority
      });
      alert('Thank you for your feedback! The AI model classification logic will adapt.');
    } catch (e) {
      console.error(e);
    }
  };

  const handleDraftResponse = async () => {
    if (!ticketId) return;
    setHelperLoading(true);
    setTicketHelperResult(null);
    try {
      const response = await api.post(`/ai/tickets/${ticketId}/suggest-response`);
      setTicketHelperResult({ type: 'draft', content: response.data.data.suggestion });
    } catch (err: any) {
      setTicketHelperResult({ type: 'error', message: err.response?.data?.error?.message || 'Error generating suggested response' });
    } finally {
      setHelperLoading(false);
    }
  };

  const handleSummarize = async () => {
    if (!ticketId) return;
    setHelperLoading(true);
    setTicketHelperResult(null);
    try {
      const response = await api.post(`/ai/tickets/${ticketId}/summarize`);
      setTicketHelperResult({ type: 'summary', content: response.data.data.summary });
    } catch (err: any) {
      setTicketHelperResult({ type: 'error', message: err.response?.data?.error?.message || 'Error generating thread summary' });
    } finally {
      setHelperLoading(false);
    }
  };

  const isStaff = user && ['agent', 'manager', 'admin', 'super_admin'].includes(user.role);

  return (
    <div className="chat-page">
      {/* Sessions list panel */}
      <div className="chat-sidebar">
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)' }}>
          <button className="btn btn-primary" style={{ width: '100%' }} onClick={startNewChat}>
            <Plus size={16} />
            <span>New Chat</span>
          </button>
        </div>

        <div className="chat-session-list">
          {sessions.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1rem' }}>No conversations yet</div>
          ) : (
            sessions.map(s => (
              <div 
                key={s.session_uuid} 
                className={`chat-session-item ${activeSessionUuid === s.session_uuid ? 'active' : ''}`}
                onClick={() => setActiveSessionUuid(s.session_uuid)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden' }}>
                  <MessageSquare size={16} style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title}</span>
                </div>
                <button 
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                  onClick={(e) => handleDeleteSession(s.session_uuid, e)}
                >
                  <Trash2 size={14} className="hover-red" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main chat window */}
      <div className="chat-area">
        {messages.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', textAlign: 'center', gap: '1.5rem' }}>
            <div className="avatar" style={{ width: '64px', height: '64px', fontSize: '2rem' }}>AI</div>
            <div>
              <h2>IntelliBot</h2>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', marginTop: '0.5rem' }}>
                Ask questions to query ingestion articles & technical files. IntelliBot uses context retrieval (RAG) to write precise guides.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
              <div className="card" style={{ padding: '0.75rem 1rem', fontSize: '0.85rem', maxWidth: '240px', cursor: 'pointer' }} onClick={() => setInputText('How do I reset my company VPN password?')}>
                "VPN Password Reset procedure"
              </div>
              <div className="card" style={{ padding: '0.75rem 1rem', fontSize: '0.85rem', maxWidth: '240px', cursor: 'pointer' }} onClick={() => setInputText('What is the standard SLA policy for critical tickets?')}>
                "Standard SLA policy response timings"
              </div>
            </div>
          </div>
        ) : (
          <div className="chat-messages">
            {messages.map(msg => (
              <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', alignSelf: msg.sender_type === 'user' ? 'flex-end' : 'flex-start', width: '100%', alignItems: msg.sender_type === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {msg.sender_type === 'assistant' ? (
                    <>
                      <Cpu size={12} style={{ color: 'var(--primary)' }} />
                      <span>IntelliBot</span>
                    </>
                  ) : (
                    <>
                      <User size={12} />
                      <span>You</span>
                    </>
                  )}
                </div>
                
                <div className={`message-bubble message-${msg.sender_type}`}>
                  {msg.content}

                  {/* RAG sources indicator */}
                  {msg.sender_type === 'assistant' && msg.rag_sources && msg.rag_sources.length > 0 && (
                    <div>
                      <div 
                        className="sources-toggle"
                        onClick={() => setShowSourcesForMsg(showSourcesForMsg === msg.id ? null : msg.id)}
                      >
                        <Compass size={12} />
                        <span>{showSourcesForMsg === msg.id ? 'Hide references' : `Show references (${msg.rag_sources.length})`}</span>
                      </div>

                      {showSourcesForMsg === msg.id && (
                        <div className="sources-container">
                          {msg.rag_sources.map((src: any, sIdx: number) => (
                            <div key={sIdx} className="source-item">
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, marginBottom: '0.25rem' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                  {src.metadata?.article_id ? <BookOpen size={10} /> : <FileText size={10} />}
                                  {src.metadata?.title || 'Ingested File'}
                                </span>
                                <span style={{ color: 'var(--success)' }}>Match: {Math.round((src.score || 0) * 100)}%</span>
                              </div>
                              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>"{src.text}"</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {msg.sender_type === 'assistant' && msg.latency_ms && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    Latency: {(msg.latency_ms / 1000).toFixed(2)}s • Tokens: {msg.tokens_used}
                  </span>
                )}
              </div>
            ))}
            {isLoading && (
              <div style={{ display: 'flex', gap: '0.5rem', alignSelf: 'flex-start', alignItems: 'center', padding: '0.5rem' }}>
                <Brain size={16} className="pulse" style={{ color: 'var(--primary)' }} />
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>IntelliBot is thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        <form onSubmit={handleSendMessage} className="chat-input-area">
          <input 
            type="text" 
            className="input-field" 
            placeholder="Type your question or query..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isLoading}
            required
          />
          <button type="submit" className="btn btn-primary" disabled={isLoading}>
            <Send size={18} />
          </button>
        </form>
      </div>

      {/* Contextual Ticket side panel for Agents/Staff */}
      {isStaff && (
        <div style={{ width: '320px', borderLeft: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', overflowY: 'auto' }}>
          <div>
            <h3>Agent Toolkit</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Perform automated triage, drafts, and resolution guidance for support tickets.</p>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Ticket ID / ID Number</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input 
                type="text" 
                className="input-field" 
                placeholder="e.g. 1" 
                value={ticketId}
                onChange={(e) => setTicketId(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={handleTriage} disabled={!ticketId || helperLoading}>
              <Cpu size={16} />
              <span>AI Ticket Triage</span>
            </button>
            <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={handleDraftResponse} disabled={!ticketId || helperLoading}>
              <Send size={16} />
              <span>Suggest Agent Reply</span>
            </button>
            <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={handleSummarize} disabled={!ticketId || helperLoading}>
              <Compass size={16} />
              <span>Summarize Comment Thread</span>
            </button>
          </div>

          {/* Assistant Results block */}
          {helperLoading && (
            <div style={{ display: 'flex', justifySelf: 'center', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', gap: '0.5rem' }}>
              <Loader2 className="spin" size={18} style={{ color: 'var(--primary)' }} />
              <span style={{ fontSize: '0.85rem' }}>Querying assistant...</span>
            </div>
          )}

          {ticketHelperResult && (
            <div className="card" style={{ padding: '1rem', backgroundColor: 'var(--bg-tertiary)' }}>
              {ticketHelperResult.type === 'triage' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--primary)' }}>Triage Prediction</div>
                  <div style={{ fontSize: '0.85rem' }}>
                    <div><strong>Category:</strong> {ticketHelperResult.data.predicted_category}</div>
                    <div style={{ marginTop: '0.25rem' }}><strong>Priority:</strong> {ticketHelperResult.data.predicted_priority}</div>
                    <div style={{ marginTop: '0.25rem' }}><strong>Confidence:</strong> {Math.round(ticketHelperResult.data.confidence * 100)}%</div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                    <button className="btn btn-secondary" style={{ flex: 1, padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => handleTriageFeedback(true)}>
                      <ThumbsUp size={12} /> Accept
                    </button>
                    <button className="btn btn-secondary" style={{ flex: 1, padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => handleTriageFeedback(false)}>
                      <ThumbsDown size={12} /> Reject
                    </button>
                  </div>
                </div>
              )}

              {ticketHelperResult.type === 'draft' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--primary)' }}>Suggested Reply</div>
                  <textarea 
                    className="input-field" 
                    style={{ fontSize: '0.8rem', minHeight: '120px', resize: 'vertical' }} 
                    value={ticketHelperResult.content}
                    readOnly
                  />
                  <button className="btn btn-primary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => { navigator.clipboard.writeText(ticketHelperResult.content); alert('Copied to clipboard'); }}>
                    Copy Draft
                  </button>
                </div>
              )}

              {ticketHelperResult.type === 'summary' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--primary)' }}>Thread Summary</div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{ticketHelperResult.content}</p>
                </div>
              )}

              {ticketHelperResult.type === 'error' && (
                <div style={{ color: 'var(--danger)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <Info size={14} />
                  <span>{ticketHelperResult.message}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
