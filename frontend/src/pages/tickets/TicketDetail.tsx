import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, User, Tag, Shield, Send, MessageSquare, Cpu, ThumbsUp, ThumbsDown, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';

const renderMarkdown = (text: string) => {
  if (!text) return null;
  const lines = text.split('\n');
  return lines.map((line, idx) => {
    let cleanLine = line.trim();
    const isBullet = cleanLine.startsWith('* ') || cleanLine.startsWith('- ') || cleanLine.startsWith('*');
    if (isBullet) {
      cleanLine = cleanLine.replace(/^[\*\-]\s*/, '');
    }
    const parts = cleanLine.split('**');
    const content = parts.map((part, i) => {
      if (i % 2 === 1) {
        return <strong key={i}>{part}</strong>;
      }
      return part;
    });
    if (isBullet) {
      return (
        <li key={idx} style={{ marginLeft: '1rem', marginBottom: '0.25rem', listStyleType: 'disc' }}>
          {content}
        </li>
      );
    }
    return (
      <p key={idx} style={{ marginBottom: '0.5rem', minHeight: cleanLine ? 'auto' : '0.5rem' }}>
        {content}
      </p>
    );
  });
};

interface Comment {
  id: number;
  body: string;
  is_internal: boolean;
  created_at: string;
  author: {
    id: number;
    full_name: string;
    role: string;
  };
}

interface TicketDetailData {
  id: number;
  ticket_number: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  category: string;
  resolution_notes?: string | null;
  created_at: string;
  sla_resolution_deadline?: string | null;
  sla_breached?: boolean;
  requester: {
    id: number;
    full_name: string;
    email: string;
  };
  assignee?: {
    id: number;
    full_name: string;
    email: string;
  } | null;
}

const VALID_TICKET_TRANSITIONS: Record<string, string[]> = {
  'new': ['open', 'closed'],
  'open': ['in_progress', 'closed'],
  'in_progress': ['pending', 'resolved', 'escalated', 'on_hold'],
  'pending': ['in_progress', 'resolved', 'closed'],
  'escalated': ['in_progress', 'pending'],
  'on_hold': ['in_progress'],
  'resolved': ['closed', 'in_progress'],
  'closed': ['in_progress']
};

// No hardcoded agents — always fetched live from the backend

export const TicketDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [ticket, setTicket] = useState<TicketDetailData | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  
  // Loading & Action states
  const [isLoading, setIsLoading] = useState(true);
  const [commentBody, setCommentBody] = useState('');
  const [isInternalComment, setIsInternalComment] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [showResolutionForm, setShowResolutionForm] = useState(false);

  // AI Copilot States
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<any>(null);

  const isStaff = user && ['agent', 'manager', 'admin', 'super_admin'].includes(user.role);
  const isManagerOrAbove = user && ['manager', 'admin', 'super_admin'].includes(user.role);

  useEffect(() => {
    fetchTicketData();
    if (isStaff) {
      fetchAgents();
    }
  }, [id]);

  const fetchTicketData = async () => {
    setIsLoading(true);
    try {
      const ticketRes = await api.get(`/tickets/${id}`);
      setTicket(ticketRes.data.data);

      const commentsRes = await api.get(`/tickets/${id}/comments`);
      setComments(commentsRes.data.data);
    } catch (e) {
      console.error('Error fetching ticket data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAgents = async () => {
    try {
      // /users/assignable is accessible to Agent+ and returns only agents & managers
      const response = await api.get('/users/assignable');
      const staffUsers = (response.data.data || []).map((u: any) => ({
        id: u.id,
        full_name: u.full_name || `${u.first_name || ''} ${u.last_name || ''}`.trim(),
        role: u.role,
        email: u.email,
      }));
      setAgents(staffUsers);
    } catch (e) {
      console.error('Failed to fetch assignable users:', e);
      // Leave agents as empty — the dropdown will show only 'Unassigned'
    }
  };

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentBody.trim()) return;

    try {
      const response = await api.post(`/tickets/${id}/comments`, {
        body: commentBody,
        is_internal: isInternalComment
      });
      setComments(prev => [...prev, response.data.data]);
      setCommentBody('');
      setIsInternalComment(false);
    } catch (err: any) {
      alert(err.response?.data?.error?.message || 'Failed to post comment');
    }
  };

  const handleAttributeChange = async (field: string, value: any) => {
    if (!ticket) return;
    setIsUpdating(true);
    try {
      const payload: any = { [field]: value };
      
      // If resolving, require resolution notes
      if (field === 'status' && value === 'resolved') {
        if (!resolutionNotes.trim()) {
          setShowResolutionForm(true);
          setIsUpdating(false);
          return;
        }
        payload.resolution_notes = resolutionNotes;
      }

      const res = await api.put(`/tickets/${id}`, payload);
      setTicket(res.data.data);
      setShowResolutionForm(false);
      setResolutionNotes('');
      // Reload comments in case a system note was added
      const commentsRes = await api.get(`/tickets/${id}/comments`);
      setComments(commentsRes.data.data);
    } catch (err: any) {
      alert(err.response?.data?.error?.message || 'Failed to update ticket');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAssigneeChange = async (assigneeId: string) => {
    if (!ticket) return;
    setIsUpdating(true);
    try {
      const parsedId = assigneeId ? parseInt(assigneeId, 10) : null;
      const res = await api.put(`/tickets/${id}/assign`, { assignee_id: parsedId });
      setTicket(res.data.data);
      // Refresh comments
      const commentsRes = await api.get(`/tickets/${id}/comments`);
      setComments(commentsRes.data.data);
    } catch (err: any) {
      alert(err.response?.data?.error?.message || 'Failed to reassign ticket');
    } finally {
      setIsUpdating(false);
    }
  };

  // AI Assistant Integrations
  const handleAITriage = async () => {
    setAiLoading(true);
    setAiResult(null);
    try {
      const response = await api.post(`/ai/tickets/${id}/classify`);
      setAiResult({ type: 'triage', data: response.data.data });
    } catch (err: any) {
      setAiResult({ type: 'error', message: err.response?.data?.error?.message || 'AI Triage failed' });
    } finally {
      setAiLoading(false);
    }
  };

  const handleTriageFeedback = async (accepted: boolean) => {
    if (!aiResult || !aiResult.data) return;
    try {
      if (accepted) {
        // Automatically apply the AI recommendations to the ticket properties
        await api.put(`/tickets/${id}`, {
          category: aiResult.data.predicted_category,
          priority: aiResult.data.predicted_priority
        });
      }
      
      // Send feedback to backend to improve the model
      await api.post(`/ai/tickets/${id}/classification/feedback`, {
        was_accepted: accepted
      });
      
      alert(accepted ? 'AI Triage Accepted & Applied!' : 'AI Triage Rejected');
      setAiResult(null);
      fetchTicketData(); // Reload updated category/priority
    } catch (err: any) {
      alert(err.response?.data?.error?.message || 'Feedback submission failed');
    }
  };

  const handleAISuggestReply = async () => {
    setAiLoading(true);
    setAiResult(null);
    try {
      const response = await api.post(`/ai/tickets/${id}/suggest-response`);
      setAiResult({ type: 'reply', content: response.data.data.suggestion });
    } catch (err: any) {
      setAiResult({ type: 'error', message: err.response?.data?.error?.message || 'Failed to generate suggestion' });
    } finally {
      setAiLoading(false);
    }
  };

  const handleAISummarize = async () => {
    setAiLoading(true);
    setAiResult(null);
    try {
      const response = await api.post(`/ai/tickets/${id}/summarize`);
      setAiResult({ type: 'summary', content: response.data.data.summary });
    } catch (err: any) {
      setAiResult({ type: 'error', message: err.response?.data?.error?.message || 'Failed to summarize timeline' });
    } finally {
      setAiLoading(false);
    }
  };

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Loading ticket details...</div>;
  }

  if (!ticket) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <h2>Ticket Not Found</h2>
        <button className="btn btn-secondary" onClick={() => navigate('/tickets')} style={{ marginTop: '1rem' }}>
          <ArrowLeft size={16} /> Back to list
        </button>
      </div>
    );
  }

  // Get allowed statuses based on current ticket status
  const allowedStatuses = VALID_TICKET_TRANSITIONS[ticket.status] || [];

  return (
    <div className="page-container">
      {/* Back Button & Navigation */}
      <button 
        className="btn btn-secondary" 
        onClick={() => navigate('/tickets')} 
        style={{ marginBottom: '1.5rem', width: 'fit-content' }}
      >
        <ArrowLeft size={16} />
        <span>Back to Tickets</span>
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: '2.5fr 1fr', gap: '2rem' }}>
        {/* LEFT COLUMN: Main Ticket Workspace */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Main Detail Card */}
          <div className="card" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <span className="badge badge-info" style={{ fontSize: '0.8rem', fontWeight: 700, padding: '0.2rem 0.6rem' }}>
                  {ticket.ticket_number}
                </span>
                <h1 style={{ marginTop: '0.5rem', marginBottom: '0.25rem', fontSize: '1.75rem' }}>{ticket.title}</h1>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <User size={14} /> Requester: <strong>{ticket.requester.full_name}</strong> ({ticket.requester.email})
                  </span>
                  <span>•</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <Clock size={14} /> Created: {new Date(ticket.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            <hr style={{ margin: '1.5rem 0', borderColor: 'var(--border-color)' }} />

            <div>
              <h3 style={{ marginBottom: '0.75rem' }}>Description</h3>
              <div 
                className="input-field" 
                style={{ 
                  backgroundColor: 'var(--bg-tertiary)', 
                  padding: '1.25rem', 
                  borderRadius: 'var(--radius-sm)', 
                  whiteSpace: 'pre-wrap', 
                  border: 'none',
                  minHeight: '100px',
                  color: 'var(--text-primary)',
                  fontSize: '0.95rem',
                  lineHeight: 1.5
                }}
              >
                {ticket.description}
              </div>
            </div>

            {ticket.resolution_notes && (
              <div style={{ marginTop: '1.5rem', borderLeft: '4px solid var(--success)', paddingLeft: '1rem' }}>
                <h4 style={{ color: 'var(--success)', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <CheckCircle size={16} /> Resolution Notes
                </h4>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{ticket.resolution_notes}</p>
              </div>
            )}

            {/* SLA Alert banner */}
            {ticket.sla_resolution_deadline && (
              <div style={{ 
                marginTop: '1.5rem', 
                padding: '1rem', 
                borderRadius: 'var(--radius-sm)', 
                backgroundColor: ticket.sla_breached ? 'var(--danger-light)' : 'var(--success-light)',
                border: `1px solid ${ticket.sla_breached ? 'var(--danger)' : 'var(--success)'}`,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.85rem'
              }}>
                {ticket.sla_breached ? (
                  <>
                    <AlertTriangle size={16} style={{ color: 'var(--danger)' }} />
                    <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                      SLA Breached! Deadline was: {new Date(ticket.sla_resolution_deadline).toLocaleString()}
                    </span>
                  </>
                ) : (
                  <>
                    <Clock size={16} style={{ color: 'var(--success)' }} />
                    <span style={{ color: 'var(--success)', fontWeight: 600 }}>
                      SLA Active. Deadline: {new Date(ticket.sla_resolution_deadline).toLocaleString()}
                    </span>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Timeline & Discussion Thread */}
          <div className="card" style={{ padding: '2rem' }}>
            <h3 style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MessageSquare size={20} /> Discussion Timeline
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '1.5rem', maxHeight: '400px', overflowY: 'auto', paddingRight: '0.5rem' }}>
              {comments.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem', padding: '1.5rem' }}>
                  No messages on this ticket yet.
                </div>
              ) : (
                comments.map((c) => (
                  <div 
                    key={c.id} 
                    style={{ 
                      padding: '1rem', 
                      borderRadius: 'var(--radius-sm)', 
                      border: '1px solid var(--border-color)',
                      backgroundColor: c.is_internal ? 'rgba(245, 158, 11, 0.08)' : 'var(--bg-secondary)',
                      alignSelf: 'stretch'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', fontSize: '0.8rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <strong>{c.author.full_name}</strong>
                        <span className="badge badge-secondary" style={{ fontSize: '0.65rem' }}>{c.author.role}</span>
                        {c.is_internal && (
                          <span className="badge badge-warning" style={{ fontSize: '0.65rem' }}>Internal Note</span>
                        )}
                      </div>
                      <span style={{ color: 'var(--text-secondary)' }}>
                        {new Date(c.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.9rem', whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>{c.body}</p>
                  </div>
                ))
              )}
            </div>

            {/* Post comment form */}
            <form onSubmit={handlePostComment} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <textarea 
                  className="input-field" 
                  style={{ minHeight: '80px', resize: 'vertical' }}
                  placeholder="Type a message or note..."
                  value={commentBody}
                  onChange={(e) => setCommentBody(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {isStaff ? (
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                      <input 
                        type="radio" 
                        name="commentType" 
                        checked={!isInternalComment} 
                        onChange={() => setIsInternalComment(false)}
                      />
                      <span>Public Reply</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--warning)' }}>
                      <input 
                        type="radio" 
                        name="commentType" 
                        checked={isInternalComment} 
                        onChange={() => setIsInternalComment(true)}
                      />
                      <span>Internal Note</span>
                    </label>
                  </div>
                ) : <div />}

                <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-end' }}>
                  <Send size={14} />
                  <span>Send</span>
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* RIGHT COLUMN: Ticket Attributes & AI Copilot */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Attributes Panel */}
          <div className="card" style={{ padding: '1.5rem' }}>
            <h3 style={{ marginBottom: '1.25rem' }}>Ticket Properties</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Status Dropdown */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" style={{ fontWeight: 600 }}>Status</label>
                {isStaff ? (
                  <select 
                    className="input-field" 
                    value={ticket.status} 
                    onChange={(e) => handleAttributeChange('status', e.target.value)}
                    disabled={isUpdating}
                    style={{ textTransform: 'capitalize' }}
                  >
                    <option value={ticket.status}>{ticket.status.replace('_', ' ')} (Current)</option>
                    {allowedStatuses.map(statusVal => (
                      <option key={statusVal} value={statusVal}>
                        {statusVal.replace('_', ' ')}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="input-field" style={{ textTransform: 'capitalize', backgroundColor: 'var(--bg-tertiary)' }}>
                    {ticket.status.replace('_', ' ')}
                  </div>
                )}
              </div>

              {/* Resolution Form inline */}
              {showResolutionForm && (
                <div style={{ padding: '0.75rem', border: '1px solid var(--warning)', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(245,158,11,0.05)' }}>
                  <label className="form-label" style={{ fontWeight: 600, color: 'var(--warning)' }}>Resolution Notes Required</label>
                  <textarea 
                    className="input-field" 
                    style={{ minHeight: '60px', resize: 'vertical', fontSize: '0.85rem' }} 
                    placeholder="Describe how the ticket was resolved..."
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    required
                  />
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', justifyContent: 'flex-end' }}>
                    <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => setShowResolutionForm(false)}>Cancel</button>
                    <button className="btn btn-primary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => handleAttributeChange('status', 'resolved')}>Resolve</button>
                  </div>
                </div>
              )}

              {/* Priority Selection */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" style={{ fontWeight: 600 }}>Priority</label>
                {isManagerOrAbove ? (
                  <select 
                    className="input-field" 
                    value={ticket.priority} 
                    onChange={(e) => handleAttributeChange('priority', e.target.value)}
                    disabled={isUpdating}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                ) : (
                  <div className="input-field" style={{ textTransform: 'capitalize', backgroundColor: 'var(--bg-tertiary)' }}>
                    {ticket.priority}
                  </div>
                )}
              </div>

              {/* Category Selection */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" style={{ fontWeight: 600 }}>Category</label>
                {isStaff ? (
                  <select 
                    className="input-field" 
                    value={ticket.category} 
                    onChange={(e) => handleAttributeChange('category', e.target.value)}
                    disabled={isUpdating}
                  >
                    <option value="General">General</option>
                    <option value="Hardware">Hardware</option>
                    <option value="Software">Software</option>
                    <option value="Network">Network</option>
                    <option value="Access/Permissions">Access/Permissions</option>
                    <option value="Email">Email</option>
                    <option value="Database">Database</option>
                    <option value="Security">Security</option>
                  </select>
                ) : (
                  <div className="input-field" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                    {ticket.category}
                  </div>
                )}
              </div>

              {/* Assignee Selection */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" style={{ fontWeight: 600 }}>Assignee</label>
                {isManagerOrAbove ? (
                  <select 
                    className="input-field" 
                    value={ticket.assignee?.id || ''} 
                    onChange={(e) => handleAssigneeChange(e.target.value)}
                    disabled={isUpdating}
                  >
                    <option value="">Unassigned</option>
                    {agents.map(a => (
                      <option key={a.id} value={a.id}>{a.full_name} ({a.role})</option>
                    ))}
                  </select>
                ) : (
                  <div className="input-field" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                    {ticket.assignee ? ticket.assignee.full_name : 'Unassigned'}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* AI Assistant toolkit */}
          {isStaff && (
            <div className="card" style={{ padding: '1.5rem' }}>
              <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Cpu size={18} style={{ color: 'var(--primary)' }} /> AI Agent Assistant
              </h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
                <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={handleAITriage} disabled={aiLoading}>
                  <Shield size={16} />
                  <span>AI Ticket Triage</span>
                </button>
                <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={handleAISuggestReply} disabled={aiLoading}>
                  <Send size={16} />
                  <span>Suggest Reply</span>
                </button>
                <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={handleAISummarize} disabled={aiLoading}>
                  <Tag size={16} />
                  <span>Summarize Thread</span>
                </button>
              </div>

              {aiLoading && (
                <div style={{ display: 'flex', justifySelf: 'center', alignItems: 'center', justifyContent: 'center', padding: '1rem', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Processing prompt...</span>
                </div>
              )}

              {aiResult && (
                <div className="card" style={{ padding: '1rem', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-color)' }}>
                  {aiResult.type === 'triage' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
                      <div style={{ fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)', fontSize: '0.75rem' }}>Predicted Triage</div>
                      <div><strong>Category:</strong> {aiResult.data.predicted_category}</div>
                      <div><strong>Priority:</strong> {aiResult.data.predicted_priority}</div>
                      <div><strong>Confidence:</strong> {Math.round((aiResult.data.confidence_score ?? aiResult.data.confidence ?? 0) * 100)}%</div>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button className="btn btn-secondary" style={{ flex: 1, padding: '0.25rem 0.5rem', fontSize: '0.7rem' }} onClick={() => handleTriageFeedback(true)}>
                          <ThumbsUp size={12} /> Accept
                        </button>
                        <button className="btn btn-secondary" style={{ flex: 1, padding: '0.25rem 0.5rem', fontSize: '0.7rem' }} onClick={() => handleTriageFeedback(false)}>
                          <ThumbsDown size={12} /> Reject
                        </button>
                      </div>
                    </div>
                  )}

                  {aiResult.type === 'reply' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <div style={{ fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)', fontSize: '0.75rem' }}>Suggested Reply</div>
                      <textarea 
                        className="input-field" 
                        style={{ fontSize: '0.8rem', minHeight: '120px', resize: 'vertical' }} 
                        value={aiResult.content}
                        readOnly
                      />
                      <button className="btn btn-primary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', width: 'fit-content' }} onClick={() => { navigator.clipboard.writeText(aiResult.content); alert('Copied to clipboard'); }}>
                        Copy Reply
                      </button>
                    </div>
                  )}

                  {aiResult.type === 'summary' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <div style={{ fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)', fontSize: '0.75rem' }}>Thread Summary</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                        {renderMarkdown(aiResult.content)}
                      </div>
                    </div>
                  )}

                  {aiResult.type === 'error' && (
                    <div style={{ color: 'var(--danger)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Info size={12} />
                      <span>{aiResult.message}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
