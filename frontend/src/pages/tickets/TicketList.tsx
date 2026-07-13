import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, RefreshCw, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import api from '../../services/api';

interface TicketListItem {
  id: number;
  ticket_number: string;
  title: string;
  status: string;
  priority: string;
  category: string;
  created_at: string;
  assignee?: {
    id: number;
    full_name: string;
    email: string;
  } | null;
  requester?: {
    id: number;
    full_name: string;
    email: string;
  } | null;
}

export const TicketList: React.FC = () => {
  const navigate = useNavigate();

  const [tickets, setTickets] = useState<TicketListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Pagination & Filters State
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [status, setStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [_sortBy, _setSortBy] = useState('created_at');
  const [_order, _setOrder] = useState('desc');

  // New ticket modal trigger
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newTicket, setNewTicket] = useState({
    title: '',
    description: '',
    priority: 'medium',
    category: 'General'
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchTickets();
  }, [page, status, priority, category]);

  const fetchTickets = async () => {
    setIsLoading(true);
    try {
      const params: any = {
        page,
        per_page: 10,
        sort_by: 'created_at',
        order: 'desc',
      };

      if (status) params.status = status;
      if (priority) params.priority = priority;
      if (category) params.category = category;
      if (search) params.search = search;

      const response = await api.get('/tickets/', { params });
      setTickets(response.data.data);
      if (response.data.pagination) {
        setTotalPages(response.data.pagination.pages);
        setTotalItems(response.data.pagination.total);
      }
    } catch (e) {
      console.error('Error fetching tickets:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTickets();
  };

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTicket.title.trim() || !newTicket.description.trim()) return;
    setIsSubmitting(true);
    try {
      await api.post('/tickets/', newTicket);
      setIsCreateModalOpen(false);
      setNewTicket({
        title: '',
        description: '',
        priority: 'medium',
        category: 'General'
      });
      setPage(1);
      fetchTickets();
    } catch (err: any) {
      alert(err.response?.data?.error?.message || 'Failed to create ticket');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPriorityBadge = (p: string) => {
    switch (p) {
      case 'critical': return 'badge-danger';
      case 'high': return 'badge-warning';
      case 'medium': return 'badge-info';
      default: return 'badge-success';
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'resolved': return 'badge-success';
      case 'closed': return 'badge-secondary';
      case 'in_progress': return 'badge-info';
      case 'pending': return 'badge-warning';
      default: return 'badge-primary';
    }
  };

  return (
    <div className="page-container">
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '2rem' }}>Support Tickets</h1>
          <p style={{ color: 'var(--text-secondary)' }}>View, manage, and track all IT service tickets</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-primary" onClick={() => setIsCreateModalOpen(true)}>
            <Plus size={16} />
            <span>Raise Ticket</span>
          </button>
          <button className="btn btn-secondary" onClick={fetchTickets}>
            <RefreshCw size={16} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-end' }}>
          {/* Search Input */}
          <div className="form-group" style={{ flex: 1, minWidth: '240px', marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: 600 }}>Search Tickets</label>
            <div style={{ position: 'relative' }}>
              <input 
                type="text" 
                className="input-field" 
                placeholder="Search by title, number or text..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: '2.5rem' }}
              />
              <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>
          </div>

          {/* Status Filter */}
          <div className="form-group" style={{ width: '150px', marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: 600 }}>Status</label>
            <select className="input-field" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
              <option value="">All Statuses</option>
              <option value="new">New</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="pending">Pending</option>
              <option value="escalated">Escalated</option>
              <option value="on_hold">On Hold</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          {/* Priority Filter */}
          <div className="form-group" style={{ width: '150px', marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: 600 }}>Priority</label>
            <select className="input-field" value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1); }}>
              <option value="">All Priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Category Filter */}
          <div className="form-group" style={{ width: '150px', marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: 600 }}>Category</label>
            <select className="input-field" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }}>
              <option value="">All Categories</option>
              <option value="General">General</option>
              <option value="Hardware">Hardware</option>
              <option value="Software">Software</option>
              <option value="Network">Network</option>
              <option value="Access/Permissions">Access/Permissions</option>
              <option value="Email">Email</option>
              <option value="Database">Database</option>
              <option value="Security">Security</option>
            </select>
          </div>

          {/* Search/Submit Action */}
          <button type="submit" className="btn btn-secondary" style={{ padding: '0.65rem 1.25rem' }}>
            <span>Search</span>
          </button>
        </form>
      </div>

      {/* Tickets List Card */}
      <div className="card">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>Loading tickets list...</div>
        ) : tickets.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            No tickets found matching the filter criteria.
          </div>
        ) : (
          <>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Number</th>
                    <th>Title</th>
                    <th>Requester</th>
                    <th>Assignee</th>
                    <th>Category</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th style={{ width: '80px', textAlign: 'center' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t) => (
                    <tr key={t.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/tickets/${t.id}`)}>
                      <td style={{ fontWeight: 700 }}>{t.ticket_number}</td>
                      <td style={{ fontWeight: 500 }}>{t.title}</td>
                      <td>
                        {t.requester ? t.requester.full_name : '-'}
                      </td>
                      <td>
                        {t.assignee ? (
                          <span style={{ fontWeight: 600, color: 'var(--primary)' }}>
                            {t.assignee.full_name}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Unassigned</span>
                        )}
                      </td>
                      <td>{t.category}</td>
                      <td>
                        <span className={`badge ${getPriorityBadge(t.priority)}`}>
                          {t.priority}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${getStatusBadge(t.status)}`} style={{ textTransform: 'capitalize' }}>
                          {t.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {new Date(t.created_at).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '0.35rem 0.6rem' }} 
                          onClick={() => navigate(`/tickets/${t.id}`)}
                          title="View Details"
                        >
                          <Eye size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 1.5rem', borderTop: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Showing page <strong>{page}</strong> of <strong>{totalPages}</strong> ({totalItems} total tickets)
                </span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button 
                    className="btn btn-secondary" 
                    style={{ padding: '0.4rem' }}
                    onClick={() => setPage(prev => Math.max(prev - 1, 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button 
                    className="btn btn-secondary" 
                    style={{ padding: '0.4rem' }}
                    onClick={() => setPage(prev => Math.min(prev + 1, totalPages))}
                    disabled={page === totalPages}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Create Ticket Modal */}
      {isCreateModalOpen && (
        <div className="modal-overlay" onClick={() => setIsCreateModalOpen(false)}>
          <div className="modal-content card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px', width: '100%', padding: '2rem' }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Raise a New Support Ticket</h2>
            <form onSubmit={handleCreateTicket} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" htmlFor="new-title" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Title</label>
                <input 
                  type="text" 
                  id="new-title"
                  className="input-field" 
                  placeholder="e.g. Cannot access VPN from home"
                  value={newTicket.title}
                  onChange={(e) => setNewTicket(prev => ({ ...prev, title: e.target.value }))}
                  required
                  minLength={5}
                />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" htmlFor="new-description" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Description</label>
                <textarea 
                  id="new-description"
                  className="input-field" 
                  style={{ minHeight: '120px', resize: 'vertical' }}
                  placeholder="Describe the issue in detail..."
                  value={newTicket.description}
                  onChange={(e) => setNewTicket(prev => ({ ...prev, description: e.target.value }))}
                  required
                  minLength={10}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label" htmlFor="new-priority" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Priority</label>
                  <select 
                    id="new-priority"
                    className="input-field"
                    value={newTicket.priority}
                    onChange={(e) => setNewTicket(prev => ({ ...prev, priority: e.target.value }))}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label" htmlFor="new-category" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Category</label>
                  <select 
                    id="new-category"
                    className="input-field"
                    value={newTicket.category}
                    onChange={(e) => setNewTicket(prev => ({ ...prev, category: e.target.value }))}
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
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsCreateModalOpen(false)} disabled={isSubmitting}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Submitting...' : 'Create Ticket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
