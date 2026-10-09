import React, { useEffect, useState, useRef, useCallback } from "react";
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
  /** True when the SSE stream closed before the server sent a done event. */
  isStreamInterrupted?: boolean;
  /** True when one or more SSE frames failed JSON.parse during the stream. */
  hadParseError?: boolean;
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

// Base API URL for the SSE streaming endpoint.
// This is a plain HTTP POST — no WebSocket, no Socket.IO.
// Works through AWS ALB, Nginx, CloudFront — any HTTP proxy.
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export const AIAssistant: React.FC = () => {
  const { user } = useAuthStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingIdRef = useRef<number | null>(null);
  // AbortController lets us cancel an in-flight SSE stream (e.g. user navigates away)
  const abortCtrlRef = useRef<AbortController | null>(null);

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionUuid, setActiveSessionUuid] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [showSourcesForMsg, setShowSourcesForMsg] = useState<number | null>(null);

  const [ticketId, setTicketId] = useState("");
  const [ticketHelperResult, setTicketHelperResult] = useState<any | null>(null);
  const [helperLoading, setHelperLoading] = useState(false);

  const activeSessionUuidRef = useRef<string | null>(null);
  useEffect(() => {
    activeSessionUuidRef.current = activeSessionUuid;
  }, [activeSessionUuid]);

  // Cancel any in-flight stream when the component unmounts
  useEffect(() => {
    return () => { abortCtrlRef.current?.abort(); };
  }, []);



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
        // Restore warning banner for messages that were interrupted mid-stream.
        // is_truncated comes from the DB via the backend DTO.
        isStreamInterrupted: m.is_truncated === true,
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
      if (!inputText.trim() || isStreaming) return;

      const userMessageContent = inputText;
      setInputText("");
      setIsStreaming(true);

      // 1. Show user message immediately
      const userMsgId = Date.now();
      setMessages((prev) => [
        ...prev,
        { id: userMsgId, sender_type: "user", content: userMessageContent },
      ]);

      // 2. Add empty assistant placeholder
      const assistantMsgId = userMsgId + 1;
      streamingIdRef.current = assistantMsgId;
      setMessages((prev) => [
        ...prev,
        { id: assistantMsgId, sender_type: "assistant", content: "", isStreaming: true },
      ]);

      // 3. Stream via SSE (plain HTTP POST — works through any proxy or load balancer)
      const abortCtrl = new AbortController();
      abortCtrlRef.current = abortCtrl;

      try {
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_BASE}/ai/chat/stream`, {
          method:  "POST",
          headers: {
            "Content-Type":  "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body:   JSON.stringify({
            query:        userMessageContent,
            session_uuid: activeSessionUuidRef.current || null,
            ticket_id:    null,
          }),
          signal: abortCtrl.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`Server error ${response.status}`);
        }

        const reader  = response.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = "";

        // ── Resilience flags ────────────────────────────────────────────────
        // receivedDone: set only when the server emits {"type": "done"}.
        // If the TCP socket closes before this flag is set, the stream was
        // truncated (e.g. NGINX idle timeout, dropped Wi-Fi, backend crash).
        // This distinguishes transport EOF from a clean application completion.
        let receivedDone  = false;

        // hadParseError: set if any SSE data line fails JSON.parse.
        // We do NOT silently drop parse errors — we surface them to the user
        // so a malformed chunk cannot masquerade as a complete response.
        let hadParseError = false;
        // ────────────────────────────────────────────────────────────────────

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE frames are separated by double newline.
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? ""; // Retain incomplete frame in buffer.

          for (const frame of parts) {
            for (const line of frame.split("\n")) {
              // Skip SSE comment lines (e.g. proxy keep-alive ": ping").
              if (!line.startsWith("data: ")) continue;

              let event: any;
              try {
                event = JSON.parse(line.slice(6));
              } catch {
                // A data line that cannot be parsed is a genuine protocol
                // error — not a keep-alive comment. Flag it so we can warn
                // the user after the stream ends instead of silently dropping
                // tokens that may have been meaningful.
                hadParseError = true;
                console.warn("[SSE] Unparseable data frame — possible network corruption:", line);
                continue;
              }

              if (event.type === "start") {
                // Capture session UUID returned by the server on the first event.
                if (!activeSessionUuidRef.current && event.session_uuid) {
                  setActiveSessionUuid(event.session_uuid);
                  activeSessionUuidRef.current = event.session_uuid;
                }

              } else if (event.type === "chunk") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, content: m.content + event.content }
                      : m
                  )
                );

              } else if (event.type === "done") {
                // Server confirmed clean completion — mark flag before updating state.
                receivedDone = true;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? {
                          ...m,
                          isStreaming:    false,
                          hadParseError:  hadParseError,
                          rag_sources:    event.sources,
                          latency_ms:     event.latency_ms,
                          tokens_used:    event.tokens_used,
                          ticket_created: event.ticket_created || null,
                        }
                      : m
                  )
                );
                fetchSessions(false);

              } else if (event.type === "error") {
                // Server emitted an explicit application-level error event.
                receivedDone = true; // Treat server error as intentional end.
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, isStreaming: false, content: `⚠️ ${event.message}` }
                      : m
                  )
                );
              }
            }
          }
        }

        // ── Post-stream truncation check ─────────────────────────────────────
        // If the TCP socket closed (reader.read() done=true) without the server
        // ever emitting {"type": "done"}, the response was interrupted.
        // Common causes: NGINX idle timeout, dropped Wi-Fi, backend OOM crash.
        // We mark the message as interrupted so the UI can warn the user.
        if (!receivedDone) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    isStreaming:        false,
                    isStreamInterrupted: true,
                  }
                : m
            )
          );
        }
        // ────────────────────────────────────────────────────────────────────

      } catch (err: any) {
        if (err.name === "AbortError") return; // User navigated away — clean exit.
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, isStreaming: false, content: `⚠️ Connection error: ${err.message}` }
              : m
          )
        );
      } finally {
        streamingIdRef.current = null;
        setIsStreaming(false);
      }
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
  const sendDisabled = isStreaming || !inputText.trim();

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

                  {/* ── Stream interruption warning ──────────────────────────
                      Shown when transport EOF arrived before the server sent
                      {"type": "done"}. Indicates a network drop, NGINX idle
                      timeout, or backend crash mid-generation. The user needs
                      to know the response may be incomplete so they can retry.
                  */}
                  {!msg.isStreaming && msg.isStreamInterrupted && (
                    <div style={{
                      marginTop: "0.75rem",
                      padding: "0.5rem 0.75rem",
                      borderRadius: "6px",
                      background: "rgba(234, 179, 8, 0.1)",
                      border: "1px solid rgba(234, 179, 8, 0.35)",
                      color: "var(--warning, #ca8a04)",
                      fontSize: "0.78rem",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.4rem",
                    }}>
                      <span>⚠</span>
                      <span>
                        Response was interrupted before completion. This may be caused by a network
                        disconnect or a server timeout. Please retry your message.
                      </span>
                    </div>
                  )}

                  {/* ── Parse error warning ───────────────────────────────────
                      Shown when one or more SSE data frames failed JSON.parse
                      during the stream. The response completed (done event was
                      received) but some tokens may have been lost to corruption.
                  */}
                  {!msg.isStreaming && !msg.isStreamInterrupted && msg.hadParseError && (
                    <div style={{
                      marginTop: "0.75rem",
                      padding: "0.5rem 0.75rem",
                      borderRadius: "6px",
                      background: "rgba(234, 179, 8, 0.08)",
                      border: "1px solid rgba(234, 179, 8, 0.25)",
                      color: "var(--warning, #ca8a04)",
                      fontSize: "0.78rem",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.4rem",
                    }}>
                      <span>⚠</span>
                      <span>
                        Part of this response may be incomplete due to a network data error.
                        If the answer looks truncated, please retry.
                      </span>
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
            placeholder={isStreaming ? "IntelliBot is responding…" : "Type your question or query..."}
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
