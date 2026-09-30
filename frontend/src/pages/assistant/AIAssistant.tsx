import React, { useEffect, useState, useRef, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import api from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import { FormattedMarkdown } from "../../components/common/FormattedMarkdown";
import {
  Plus, Trash2, Send, MessageSquare, Compass, Info,
  BookOpen, User, Cpu, Brain, ThumbsUp, ThumbsDown,
  Loader2, FileText, TicketCheck, ExternalLink,
} from "lucide-react";

interface ChatSession {
  session_uuid: string;
  title: string;
  created_at: string;
}

interface ChatMessage {
  id: number;
  sender_type: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  rag_sources?: any[];
  latency_ms?: number;
  tokens_used?: number;
  ticket_created?: {
    id: number;
    ticket_number: string;
    title: string;
    priority: string;
    category: string;
    status: string;
  } | null;
}

const SOCKET_URL =
  (import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1").replace(
    "/api/v1",
    ""
  );

function createSocket(token: string): Socket {
  return io(SOCKET_URL, {
    auth: { token },
    transports: ["websocket"],  // Direct WS to port 8000 — polling via nginx drops auth token
    autoConnect: false,         // We manually call .connect() after setting up all handlers
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10,
    timeout: 20000,
  });
}

export const AIAssistant: React.FC = () => {
  const { user } = useAuthStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<Socket | null>(null);
  const streamingIdRef = useRef<number | null>(null);

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionUuid, setActiveSessionUuid] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [socketReady, setSocketReady] = useState(false);
  const [showSourcesForMsg, setShowSourcesForMsg] = useState<number | null>(null);

  const [ticketId, setTicketId] = useState("");
  const [ticketHelperResult, setTicketHelperResult] = useState<any | null>(null);
  const [helperLoading, setHelperLoading] = useState(false);

  // Active session uuid ref for use inside socket callbacks
  const activeSessionUuidRef = useRef<string | null>(null);
  useEffect(() => {
    activeSessionUuidRef.current = activeSessionUuid;
  }, [activeSessionUuid]);

  // ── Socket setup ────────────────────────────────────────────────────────────
  useEffect(() => {
    // Only connect once the user is authenticated
    if (!user) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    const socket = createSocket(token);
    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("[Socket] Connected:", socket.id);
      setSocketReady(true);
    });
    socket.on("disconnect", (reason) => {
      console.warn("[Socket] Disconnected:", reason);
      setSocketReady(false);
    });
    socket.on("connect_error", (err) => {
      console.error("[Socket] Connection error:", err.message);
      // Retry with fresh token if available
      const freshToken = localStorage.getItem("access_token");
      if (freshToken && (socket.auth as any)?.token !== freshToken) {
        console.log("[Socket] Retrying with refreshed token...");
        socket.auth = { token: freshToken };
        setTimeout(() => socket.connect(), 500);
      }
    });
    socket.on("connected", (data: any) => {
      console.log("[Socket] Server ack:", data);
    });

    socket.on("ai:stream:start", (data: { session_uuid: string; session_title: string }) => {
      const streamId = Date.now() + 1;
      streamingIdRef.current = streamId;
      setMessages((prev) => [
        ...prev,
        { id: streamId, sender_type: "assistant", content: "", isStreaming: true },
      ]);
      if (!activeSessionUuidRef.current && data.session_uuid) {
        setActiveSessionUuid(data.session_uuid);
        activeSessionUuidRef.current = data.session_uuid;
      }
    });

    socket.on("ai:stream:chunk", (data: { chunk: string }) => {
      const id = streamingIdRef.current;
      if (id === null) return;
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, content: m.content + data.chunk } : m))
      );
    });

    socket.on(
      "ai:stream:done",
      (data: {
        session_uuid: string;
        session_title: string;
        model: string;
        tokens_used: number;
        latency_ms: number;
        sources: any[];
        ticket_created: any | null;
      }) => {
        const id = streamingIdRef.current;
        if (id !== null) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === id
                ? {
                    ...m,
                    isStreaming: false,
                    rag_sources: data.sources,
                    latency_ms: data.latency_ms,
                    tokens_used: data.tokens_used,
                    ticket_created: data.ticket_created || null,
                  }
                : m
            )
          );
          streamingIdRef.current = null;
        }
        setIsStreaming(false);
        fetchSessions(false);
      }
    );

    socket.on("ai:stream:error", (data: { message: string }) => {
      const id = streamingIdRef.current;
      if (id !== null) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === id
              ? { ...m, isStreaming: false, content: `⚠️ Error: ${data.message}` }
              : m
          )
        );
        streamingIdRef.current = null;
      } else {
        setMessages((prev) => [
          ...prev,
          { id: Date.now(), sender_type: "assistant", content: `⚠️ Error: ${data.message}` },
        ]);
      }
      setIsStreaming(false);
    });

    // Connect AFTER all handlers are registered (autoConnect is false)
    socket.connect();

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);


  const handleSelectSession = (uuid: string) => {
    if (activeSessionUuid === uuid) return;
    setActiveSessionUuid(uuid);
    activeSessionUuidRef.current = uuid;
    fetchMessages(uuid);
  };

  useEffect(() => {
    fetchSessions(true);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchSessions = async (autoSelectFirst: boolean = false) => {
    try {
      const response = await api.get("/ai/sessions");
      const list = response.data.data || [];
      setSessions(list);
      if (autoSelectFirst && list.length > 0 && !activeSessionUuidRef.current) {
        const firstUuid = list[0].session_uuid;
        setActiveSessionUuid(firstUuid);
        activeSessionUuidRef.current = firstUuid;
        fetchMessages(firstUuid);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMessages = async (sessionUuid: string) => {
    try {
      const response = await api.get(`/ai/sessions/${sessionUuid}`);
      const formatted = (response.data.data || []).map((m: any) => ({
        id: m.id,
        sender_type: m.role,
        content: m.content,
        rag_sources: m.rag_sources,
        latency_ms: m.latency_ms,
        tokens_used: m.tokens_used,
        ticket_created: m.ticket_created,
      }));
      setMessages(formatted);
    } catch (e) {
      console.error(e);
    }
  };

  const startNewChat = () => {
    setActiveSessionUuid(null);
    activeSessionUuidRef.current = null;
    setMessages([]);
  };

  const handleDeleteSession = async (uuid: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/ai/sessions/${uuid}`);
      setSessions((prev) => prev.filter((s) => s.session_uuid !== uuid));
      if (activeSessionUuid === uuid) startNewChat();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendMessage = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const socket = socketRef.current;
      if (!inputText.trim() || isStreaming || !socket?.connected) return;

      const userMessageContent = inputText;
      setInputText("");
      setIsStreaming(true);

      setMessages((prev) => [
        ...prev,
        { id: Date.now(), sender_type: "user", content: userMessageContent },
      ]);

      socket.emit("ai:chat", {
        query: userMessageContent,
        session_uuid: activeSessionUuidRef.current || null,
        ticket_id: null,
      });
    },
    [inputText, isStreaming]
  );

  const handleTriage = async () => {
    if (!ticketId) return;
    setHelperLoading(true);
    setTicketHelperResult(null);
    try {
      const response = await api.get(`/ai/tickets/${ticketId}/classification`);
      setTicketHelperResult({ type: "triage", data: response.data.data });
    } catch {
      try {
        const response = await api.post(`/ai/tickets/${ticketId}/classify`);
        setTicketHelperResult({ type: "triage", data: response.data.data });
      } catch (innerErr: any) {
        setTicketHelperResult({ type: "error", message: innerErr.response?.data?.error?.message || "Error executing AI classification" });
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
        override_priority: ticketHelperResult.data.predicted_priority,
      });
      alert("Thank you for your feedback! The AI model classification logic will adapt.");
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
      setTicketHelperResult({ type: "draft", content: response.data.data.suggestion });
    } catch (err: any) {
      setTicketHelperResult({ type: "error", message: err.response?.data?.error?.message || "Error generating suggested response" });
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
      setTicketHelperResult({ type: "summary", content: response.data.data.summary });
    } catch (err: any) {
      setTicketHelperResult({ type: "error", message: err.response?.data?.error?.message || "Error generating thread summary" });
    } finally {
      setHelperLoading(false);
    }
  };

  const isStaff = user && ["agent", "manager", "admin", "super_admin"].includes(user.role);
  const sendDisabled = isStreaming || !inputText.trim() || !socketReady;

  return (
    <div className="chat-page">
      <div className="chat-sidebar">
        <div style={{ padding: "1rem", borderBottom: "1px solid var(--border-color)" }}>
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={startNewChat}>
            <Plus size={16} />
            <span>New Chat</span>
          </button>
        </div>
        <div className="chat-session-list">
          {sessions.length === 0 ? (
            <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem", padding: "1rem" }}>
              No conversations yet
            </div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.session_uuid}
                className={`chat-session-item ${activeSessionUuid === s.session_uuid ? "active" : ""}`}
                onClick={() => handleSelectSession(s.session_uuid)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", overflow: "hidden" }}>
                  <MessageSquare size={16} style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.title}</span>
                </div>
                <button
                  style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                  onClick={(e) => handleDeleteSession(s.session_uuid, e)}
                >
                  <Trash2 size={14} className="hover-red" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="chat-area">
        {messages.length === 0 ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem", textAlign: "center", gap: "1.5rem" }}>
            <div className="avatar" style={{ width: "64px", height: "64px", fontSize: "2rem" }}>AI</div>
            <div>
              <h2>IntelliBot</h2>
              <p style={{ color: "var(--text-secondary)", maxWidth: "400px", marginTop: "0.5rem" }}>
                Ask questions to query ingestion articles &amp; technical files. IntelliBot uses context retrieval (RAG) to write precise guides.
              </p>
            </div>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", justifyContent: "center" }}>
              <div className="card" style={{ padding: "0.75rem 1rem", fontSize: "0.85rem", maxWidth: "240px", cursor: "pointer" }} onClick={() => setInputText("How do I reset my company VPN password?")}>
                "VPN Password Reset procedure"
              </div>
              <div className="card" style={{ padding: "0.75rem 1rem", fontSize: "0.85rem", maxWidth: "240px", cursor: "pointer" }} onClick={() => setInputText("What is the standard SLA policy for critical tickets?")}>
                "Standard SLA policy response timings"
              </div>
            </div>
          </div>
        ) : (
          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} style={{ display: "flex", flexDirection: "column", alignSelf: msg.sender_type === "user" ? "flex-end" : "flex-start", width: "100%", alignItems: msg.sender_type === "user" ? "flex-end" : "flex-start" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {msg.sender_type === "assistant" ? (
                    <><Cpu size={12} style={{ color: "var(--primary)" }} /><span>IntelliBot</span></>
                  ) : (
                    <><User size={12} /><span>You</span></>
                  )}
                </div>

                <div className={`message-bubble message-${msg.sender_type}`}>
                  {msg.sender_type === "assistant" ? (
                    msg.isStreaming ? (
                      <span style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                        {msg.content}
                        <span className="streaming-cursor">▌</span>
                      </span>
                    ) : (
                      <FormattedMarkdown content={msg.content} />
                    )
                  ) : (
                    msg.content
                  )}

                  {!msg.isStreaming && msg.sender_type === "assistant" && msg.rag_sources && msg.rag_sources.length > 0 && (
                    <div>
                      <div className="sources-toggle" onClick={() => setShowSourcesForMsg(showSourcesForMsg === msg.id ? null : msg.id)}>
                        <Compass size={12} />
                        <span>{showSourcesForMsg === msg.id ? "Hide references" : `Show references (${msg.rag_sources.length})`}</span>
                      </div>
                      {showSourcesForMsg === msg.id && (
                        <div className="sources-container">
                          {msg.rag_sources.map((src: any, sIdx: number) => (
                            <div key={sIdx} className="source-item">
                              <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 600, marginBottom: "0.25rem" }}>
                                <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                                  {src.metadata?.article_id ? <BookOpen size={10} /> : <FileText size={10} />}
                                  {src.metadata?.title || "Ingested File"}
                                </span>
                                <span style={{ color: "var(--success)" }}>Match: {Math.round((src.score || 0) * 100)}%</span>
                              </div>
                              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>"{src.text}"</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {msg.sender_type === "assistant" && msg.ticket_created && (
                    <div className="ticket-created-card">
                      <div className="ticket-created-header">
                        <TicketCheck size={16} />
                        <span>Ticket Created Successfully</span>
                      </div>
                      <div className="ticket-created-body">
                        <div className="ticket-created-number">{msg.ticket_created.ticket_number}</div>
                        <div className="ticket-created-title">{msg.ticket_created.title}</div>
                        <div className="ticket-created-meta">
                          <span className={`badge badge-${msg.ticket_created.priority === "critical" ? "danger" : msg.ticket_created.priority === "high" ? "warning" : "info"}`}>
                            {msg.ticket_created.priority}
                          </span>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{msg.ticket_created.category}</span>
                        </div>
                      </div>
                      <a href={`/tickets/${msg.ticket_created.id}`} className="ticket-created-link">
                        <ExternalLink size={13} />
                        View Ticket
                      </a>
                    </div>
                  )}
                </div>

                {!msg.isStreaming && msg.sender_type === "assistant" && msg.latency_ms && (
                  <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                    Latency: {(msg.latency_ms / 1000).toFixed(2)}s • Tokens: {msg.tokens_used}
                  </span>
                )}
              </div>
            ))}

            {isStreaming && streamingIdRef.current === null && (
              <div style={{ display: "flex", gap: "0.5rem", alignSelf: "flex-start", alignItems: "center", padding: "0.5rem" }}>
                <Brain size={16} className="pulse" style={{ color: "var(--primary)" }} />
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>IntelliBot is thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        <form onSubmit={handleSendMessage} className="chat-input-area">
          <input
            type="text"
            className="input-field"
            placeholder={socketReady ? "Type your question or query..." : "Connecting to IntelliBot…"}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isStreaming}
            required
          />
          <button type="submit" className="btn btn-primary" disabled={sendDisabled}>
            <Send size={18} />
          </button>
        </form>
      </div>

      {isStaff && (
        <div style={{ width: "320px", borderLeft: "1px solid var(--border-color)", backgroundColor: "var(--bg-secondary)", padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1.5rem", overflowY: "auto" }}>
          <div>
            <h3>Agent Toolkit</h3>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>Perform automated triage, drafts, and resolution guidance for support tickets.</p>
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Ticket ID / ID Number</label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <input type="text" className="input-field" placeholder="e.g. 1" value={ticketId} onChange={(e) => setTicketId(e.target.value)} />
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <button className="btn btn-secondary" style={{ width: "100%", justifyContent: "flex-start" }} onClick={handleTriage} disabled={!ticketId || helperLoading}>
              <Cpu size={16} /><span>AI Ticket Triage</span>
            </button>
            <button className="btn btn-secondary" style={{ width: "100%", justifyContent: "flex-start" }} onClick={handleDraftResponse} disabled={!ticketId || helperLoading}>
              <Send size={16} /><span>Suggest Agent Reply</span>
            </button>
            <button className="btn btn-secondary" style={{ width: "100%", justifyContent: "flex-start" }} onClick={handleSummarize} disabled={!ticketId || helperLoading}>
              <Compass size={16} /><span>Summarize Comment Thread</span>
            </button>
          </div>

          {helperLoading && (
            <div style={{ display: "flex", justifySelf: "center", alignItems: "center", justifyContent: "center", padding: "1.5rem", gap: "0.5rem" }}>
              <Loader2 className="spin" size={18} style={{ color: "var(--primary)" }} />
              <span style={{ fontSize: "0.85rem" }}>Querying assistant...</span>
            </div>
          )}

          {ticketHelperResult && (
            <div className="card" style={{ padding: "1rem", backgroundColor: "var(--bg-tertiary)" }}>
              {ticketHelperResult.type === "triage" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <div style={{ fontWeight: 700, fontSize: "0.85rem", textTransform: "uppercase", color: "var(--primary)" }}>Triage Prediction</div>
                  <div style={{ fontSize: "0.85rem" }}>
                    <div><strong>Category:</strong> {ticketHelperResult.data.predicted_category}</div>
                    <div style={{ marginTop: "0.25rem" }}><strong>Priority:</strong> {ticketHelperResult.data.predicted_priority}</div>
                    <div style={{ marginTop: "0.25rem" }}><strong>Confidence:</strong> {Math.round(ticketHelperResult.data.confidence * 100)}%</div>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                    <button className="btn btn-secondary" style={{ flex: 1, padding: "0.25rem 0.5rem", fontSize: "0.75rem" }} onClick={() => handleTriageFeedback(true)}><ThumbsUp size={12} /> Accept</button>
                    <button className="btn btn-secondary" style={{ flex: 1, padding: "0.25rem 0.5rem", fontSize: "0.75rem" }} onClick={() => handleTriageFeedback(false)}><ThumbsDown size={12} /> Reject</button>
                  </div>
                </div>
              )}
              {ticketHelperResult.type === "draft" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <div style={{ fontWeight: 700, fontSize: "0.85rem", textTransform: "uppercase", color: "var(--primary)" }}>Suggested Reply</div>
                  <textarea className="input-field" style={{ fontSize: "0.8rem", minHeight: "120px", resize: "vertical" }} value={ticketHelperResult.content} readOnly />
                  <button className="btn btn-primary" style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }} onClick={() => { navigator.clipboard.writeText(ticketHelperResult.content); alert("Copied to clipboard"); }}>Copy Draft</button>
                </div>
              )}
              {ticketHelperResult.type === "summary" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <div style={{ fontWeight: 700, fontSize: "0.85rem", textTransform: "uppercase", color: "var(--primary)" }}>Thread Summary</div>
                  <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>{ticketHelperResult.content}</p>
                </div>
              )}
              {ticketHelperResult.type === "error" && (
                <div style={{ color: "var(--danger)", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                  <Info size={14} /><span>{ticketHelperResult.message}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
