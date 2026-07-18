import React, { useEffect, useState, useCallback } from 'react';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import {
  FileText, CheckCircle, Cpu, Download, Calendar,
  AlertTriangle, RefreshCw, Plus, TrendingUp, Users, BarChart2
} from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area,
  BarChart, Bar, PieChart, Pie, Cell, Tooltip, Legend,
  XAxis, YAxis, CartesianGrid,
} from 'recharts';

// ─── Colour palette ───────────────────────────────────────────────────────────
const COLORS = {
  primary:  '#6366f1',
  success:  '#22c55e',
  warning:  '#f59e0b',
  danger:   '#ef4444',
  info:     '#38bdf8',
  purple:   '#a855f7',
  teal:     '#14b8a6',
};
const PIE_COLORS = [COLORS.primary, COLORS.success, COLORS.warning, COLORS.danger, COLORS.info, COLORS.purple, COLORS.teal];

// ─── Custom tooltip ───────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, padding: '0.75rem 1rem', fontSize: '0.82rem' }}>
      {label && <p style={{ fontWeight: 700, marginBottom: 4 }}>{label}</p>}
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: p.color, display: 'inline-block' }} />
          <span style={{ color: 'var(--text-secondary)' }}>{p.name}:</span>
          <span style={{ fontWeight: 600 }}>{typeof p.value === 'number' && p.name?.includes('%') ? `${p.value.toFixed(1)}%` : p.value}</span>
        </div>
      ))}
    </div>
  );
};

// ─── Types ────────────────────────────────────────────────────────────────────
interface KPI { total_tickets?: number; open_tickets?: number; overall_sla_compliance?: number; ai_sessions_total?: number; total_agents?: number; ticket_stats?: any; unread_notifications?: number; }
interface TrendPoint { date: string; tickets_created: number; tickets_resolved: number; sla_compliance_rate: number; }
interface SLAItem { priority: string; compliance_rate: number; compliant: number; breached: number; total: number; }
interface VolumeItem { category: string; count: number; }
interface AgentItem { agent_name: string; tickets_resolved: number; resolution_rate: number; sla_breached: number; }
interface ReportInfo { id: string; name: string; format: string; description: string; endpoint: string; }

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  const isManager = user && ['manager', 'admin', 'super_admin'].includes(user.role);

  const [kpis,    setKpis]    = useState<KPI | null>(null);
  const [trends,  setTrends]  = useState<TrendPoint[]>([]);
  const [sla,     setSla]     = useState<SLAItem[]>([]);
  const [volume,  setVolume]  = useState<VolumeItem[]>([]);
  const [agents,  setAgents]  = useState<AgentItem[]>([]);
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [tickets, setTickets] = useState<any[]>([]);
  const [trendDays, setTrendDays] = useState(30);
  const [loading, setLoading] = useState(true);

  const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  const today = new Date();
  const [reportDates, setReportDates] = useState({ from: fmt(new Date(today.getFullYear(), today.getMonth(), 1)), to: fmt(today) });

  const [createOpen, setCreateOpen] = useState(false);
  const [newTicket,  setNewTicket]  = useState({ title: '', description: '', priority: 'medium', category: 'General' });
  const [submitting, setSubmitting] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      if (isManager) {
        const [kpiRes, trendsRes, slaRes, volRes, agentsRes, reportsRes, ticketsRes] = await Promise.all([
          api.get('/analytics/summary'),
          api.get(`/dashboard/ticket-trends?days=${trendDays}`),
          api.get('/analytics/sla-compliance'),
          api.get('/analytics/ticket-volume'),
          api.get(`/dashboard/live-agent-leaderboard?days=${trendDays}&limit=8`),
          api.get('/reports/available'),
          api.get('/tickets/'),
        ]);
        setKpis(kpiRes.data.data);
        setTrends(trendsRes.data.data.trends ?? []);
        // normalise SLA to flat array
        const slaRaw = slaRes.data.data.sla_by_priority ?? {};
        setSla(Object.entries(slaRaw).map(([priority, v]: [string, any]) => ({ priority, ...v })));
        setVolume(volRes.data.data ?? []);
        setAgents(agentsRes.data.data.agents ?? []);
        setReports(reportsRes.data.data ?? []);
        setTickets((ticketsRes.data.data ?? []).slice(0, 5));
      } else {
        const [kpiRes, ticketsRes] = await Promise.all([
          api.get('/dashboard/summary'),
          api.get('/tickets/'),
        ]);
        setKpis(kpiRes.data.data);
        setTickets((ticketsRes.data.data ?? []).slice(0, 5));
      }
    } catch (e) {
      console.error('Dashboard fetch error', e);
    } finally {
      setLoading(false);
    }
  }, [isManager, trendDays]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/tickets/', newTicket);
      setCreateOpen(false);
      setNewTicket({ title: '', description: '', priority: 'medium', category: 'General' });
      fetchAll();
    } catch (err: any) {
      alert(err.response?.data?.error?.message || 'Failed to create ticket');
    } finally { setSubmitting(false); }
  };

  const handleDownload = (endpoint: string, format: string) => {
    const clean = endpoint.replace(/^\/api\/v1/, '');
    api.get(`${clean}?from_date=${reportDates.from}&to_date=${reportDates.to}`, { responseType: 'blob' })
      .then(r => {
        const url = window.URL.createObjectURL(new Blob([r.data]));
        const a = document.createElement('a');
        a.href = url;
        a.setAttribute('download', `report_${reportDates.from}_${reportDates.to}.${format.toLowerCase().includes('pdf') ? 'pdf' : format.toLowerCase().includes('csv') ? 'csv' : 'xlsx'}`);
        document.body.appendChild(a); a.click(); a.remove();
      }).catch(() => alert('Download failed.'));
  };

  if (loading) return <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>Loading dashboard...</div>;

  // ─── KPI values ──────────────────────────────────────────────────────────────
  const kpiCards = isManager ? [
    { label: 'Total Tickets',    value: kpis?.total_tickets ?? 0,    icon: <FileText size={22}/>,      color: COLORS.primary },
    { label: 'Open Tickets',     value: kpis?.open_tickets ?? 0,     icon: <AlertTriangle size={22}/>, color: COLORS.warning },
    { label: 'SLA Compliance',   value: `${Math.round(kpis?.overall_sla_compliance ?? 0)}%`, icon: <CheckCircle size={22}/>, color: COLORS.success },
    { label: 'AI Chat Sessions', value: kpis?.ai_sessions_total ?? 0, icon: <Cpu size={22}/>,          color: COLORS.info },
    { label: 'Total Agents',     value: kpis?.total_agents ?? 0,      icon: <Users size={22}/>,        color: COLORS.purple },
  ] : user?.role === 'agent' ? [
    { label: 'Assigned to Me',   value: kpis?.ticket_stats?.assigned_to_me ?? 0,  icon: <FileText size={22}/>,      color: COLORS.primary },
    { label: 'Resolved by Me',   value: kpis?.ticket_stats?.resolved_by_me ?? 0,  icon: <CheckCircle size={22}/>,   color: COLORS.success },
    { label: 'Overdue',          value: kpis?.ticket_stats?.overdue ?? 0,          icon: <AlertTriangle size={22}/>, color: COLORS.danger },
    { label: 'Notifications',    value: kpis?.unread_notifications ?? 0,           icon: <Cpu size={22}/>,           color: COLORS.info },
  ] : [
    { label: 'Total Tickets',    value: kpis?.ticket_stats?.total ?? 0,    icon: <FileText size={22}/>,      color: COLORS.primary },
    { label: 'Open',             value: kpis?.ticket_stats?.open ?? 0,     icon: <AlertTriangle size={22}/>, color: COLORS.warning },
    { label: 'Resolved',         value: kpis?.ticket_stats?.resolved ?? 0, icon: <CheckCircle size={22}/>,   color: COLORS.success },
    { label: 'Notifications',    value: kpis?.unread_notifications ?? 0,   icon: <Cpu size={22}/>,           color: COLORS.info },
  ];

  return (
    <div className="page-container">
      {/* ── Header ── */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'1rem' }}>
        <div>
          <h1 style={{ margin:0, fontSize:'1.9rem' }}>Welcome, {user?.first_name}</h1>
          <p style={{ color:'var(--text-secondary)', margin:0 }}>IT Service Desk — Live Overview</p>
        </div>
        <div style={{ display:'flex', gap:'0.75rem' }}>
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}><Plus size={16}/><span>Raise Ticket</span></button>
          <button className="btn btn-secondary" onClick={fetchAll}><RefreshCw size={16}/><span>Refresh</span></button>
        </div>
      </div>

      {/* ── KPI Cards ── */}
      <div className="stats-grid">
        {kpiCards.map(k => (
          <div key={k.label} className="stat-card">
            <div className="stat-icon" style={{ background: k.color + '22', color: k.color }}>{k.icon}</div>
            <div className="stat-info">
              <span className="stat-value">{k.value}</span>
              <span className="stat-label">{k.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* ── Manager Charts ── */}
      {isManager && (
        <>
          {/* Trend Controls */}
          <div style={{ display:'flex', alignItems:'center', gap:'1rem', flexWrap:'wrap' }}>
            <div style={{ display:'flex', alignItems:'center', gap:'0.5rem', fontWeight:600, color:'var(--text-secondary)', fontSize:'0.85rem' }}>
              <TrendingUp size={16}/> Trend Period:
            </div>
            {[7, 14, 30, 90].map(d => (
              <button key={d} onClick={() => setTrendDays(d)}
                className={trendDays === d ? 'btn btn-primary' : 'btn btn-secondary'}
                style={{ padding:'0.3rem 0.85rem', fontSize:'0.82rem' }}>
                {d}d
              </button>
            ))}
          </div>

          {/* Row 1: Trend Line + SLA Bar */}
          <div className="dashboard-grid-2">
            {/* Ticket Trend */}
            <div className="card">
              <div className="card-header"><h3 className="card-title">Ticket Volume Trend</h3></div>
              {trends.length === 0
                ? <p style={{ color:'var(--text-muted)', padding:'2rem', textAlign:'center' }}>No trend data available yet.</p>
                : <ResponsiveContainer width="100%" height={240}>
                    <AreaChart data={trends} margin={{ top:8, right:8, bottom:0, left:0 }}>
                      <defs>
                        <linearGradient id="gc" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor={COLORS.primary} stopOpacity={0.3}/>
                          <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="gr" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor={COLORS.success} stopOpacity={0.3}/>
                          <stop offset="95%" stopColor={COLORS.success} stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                      <XAxis dataKey="date" tick={{ fontSize:10, fill:'var(--text-muted)' }} tickLine={false} axisLine={false}
                        tickFormatter={v => v.slice(5)} />
                      <YAxis tick={{ fontSize:10, fill:'var(--text-muted)' }} tickLine={false} axisLine={false} />
                      <Tooltip content={<CustomTooltip/>} />
                      <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize:'0.78rem' }} />
                      <Area type="monotone" dataKey="tickets_created" name="Created" stroke={COLORS.primary} fill="url(#gc)" strokeWidth={2} dot={false} />
                      <Area type="monotone" dataKey="tickets_resolved" name="Resolved" stroke={COLORS.success} fill="url(#gr)" strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
              }
            </div>

            {/* SLA Compliance by Priority */}
            <div className="card">
              <div className="card-header"><h3 className="card-title">SLA Compliance by Priority</h3></div>
              {sla.length === 0
                ? <p style={{ color:'var(--text-muted)', padding:'2rem', textAlign:'center' }}>No SLA data available yet.</p>
                : <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={sla} margin={{ top:8, right:8, bottom:0, left:0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                      <XAxis dataKey="priority" tick={{ fontSize:11, fill:'var(--text-muted)' }} tickFormatter={v => v ? v.charAt(0).toUpperCase() + v.slice(1) : ''} tickLine={false} axisLine={false} />
                      <YAxis domain={[0,100]} tickFormatter={v=>`${v}%`} tick={{ fontSize:10, fill:'var(--text-muted)' }} tickLine={false} axisLine={false} />
                      <Tooltip content={<CustomTooltip/>} />
                      <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize:'0.78rem' }} />
                      <Bar dataKey="compliance_rate" name="Compliance %" radius={[6,6,0,0]}
                        fill={COLORS.success}>
                        {sla.map((entry, i) => (
                          <Cell key={i} fill={entry.compliance_rate >= 80 ? COLORS.success : entry.compliance_rate >= 60 ? COLORS.warning : COLORS.danger} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
              }
            </div>
          </div>

          {/* Row 2: Category Donut + Agent Leaderboard */}
          <div className="dashboard-grid-2">
            {/* Ticket Volume by Category */}
            <div className="card">
              <div className="card-header"><h3 className="card-title">Tickets by Category</h3></div>
              {volume.length === 0
                ? <p style={{ color:'var(--text-muted)', padding:'2rem', textAlign:'center' }}>No category data yet.</p>
                : <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie data={volume} dataKey="count" nameKey="category" cx="50%" cy="50%"
                        innerRadius={55} outerRadius={85} paddingAngle={3} label={({ percent }) => `${((percent || 0)*100).toFixed(0)}%`}
                        labelLine={true}>
                        {volume.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                      </Pie>
                      <Tooltip content={<CustomTooltip/>} />
                      <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize:'0.78rem' }} />
                    </PieChart>
                  </ResponsiveContainer>
              }
            </div>

            {/* Agent Leaderboard */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Agent Leaderboard</h3>
                <BarChart2 size={18} style={{ color:'var(--text-muted)' }} />
              </div>
              {agents.length === 0
                ? <p style={{ color:'var(--text-muted)', padding:'2rem', textAlign:'center' }}>No agent data yet.</p>
                : <ResponsiveContainer width="100%" height={260}>
                    <BarChart layout="vertical" data={agents.slice(0,6)} margin={{ top:4, right:16, bottom:0, left:60 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize:10, fill:'var(--text-muted)' }} tickLine={false} axisLine={false} />
                      <YAxis type="category" dataKey="agent_name" tick={{ fontSize:10, fill:'var(--text-muted)' }} tickLine={false} axisLine={false} width={55} />
                      <Tooltip content={<CustomTooltip/>} />
                      <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize:'0.78rem' }} />
                      <Bar dataKey="tickets_resolved" name="Resolved" fill={COLORS.primary} radius={[0,4,4,0]} />
                      <Bar dataKey="sla_breached" name="SLA Breached" fill={COLORS.danger} radius={[0,4,4,0]} />
                    </BarChart>
                  </ResponsiveContainer>
              }
            </div>
          </div>

          {/* Row 3: SLA Trend Line */}
          {trends.length > 0 && (
            <div className="card">
              <div className="card-header"><h3 className="card-title">SLA Compliance Over Time</h3></div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trends} margin={{ top:8, right:16, bottom:0, left:0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="date" tick={{ fontSize:10, fill:'var(--text-muted)' }} tickLine={false} axisLine={false} tickFormatter={v => v.slice(5)} />
                  <YAxis domain={[0,100]} tickFormatter={v=>`${v}%`} tick={{ fontSize:10, fill:'var(--text-muted)' }} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip/>} />
                  <Line type="monotone" dataKey="sla_compliance_rate" name="SLA %" stroke={COLORS.teal} strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* ── Bottom Grid: Tickets + Reports ── */}
      <div className={isManager ? "dashboard-grid-3" : "dashboard-grid-1"}>
        {/* Recent Tickets */}
        <div className="card">
          <div className="card-header"><h3 className="card-title">Recent Tickets</h3></div>
          {tickets.length === 0
            ? <div style={{ textAlign:'center', padding:'2rem', color:'var(--text-muted)' }}>No tickets yet.</div>
            : <div className="table-container">
                <table className="data-table">
                  <thead><tr><th>Number</th><th>Title</th><th>Priority</th><th>Status</th></tr></thead>
                  <tbody>
                    {tickets.map(t => (
                      <tr key={t.id}>
                        <td style={{ fontWeight:700 }}>{t.ticket_number}</td>
                        <td>{t.title}</td>
                        <td><span className={`badge badge-${t.priority==='critical'?'danger':t.priority==='high'?'warning':t.priority==='medium'?'info':'success'}`}>{t.priority}</span></td>
                        <td><span style={{ textTransform:'capitalize', fontWeight:600 }}>{t.status.replace('_',' ')}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
          }
        </div>

        {/* Reports Panel */}
        {isManager && (
          <div className="card">
            <div className="card-header"><h3 className="card-title">Executive Reports</h3></div>
            <div style={{ background:'var(--bg-tertiary)', borderRadius:'var(--radius-sm)', padding:'0.75rem', marginBottom:'0.75rem' }}>
              <div style={{ display:'flex', alignItems:'center', gap:'0.5rem', fontSize:'0.82rem', fontWeight:600, color:'var(--text-secondary)', marginBottom:'0.5rem' }}>
                <Calendar size={14}/> Report Period
              </div>
              <div style={{ display:'flex', gap:'0.5rem' }}>
                <input type="date" className="input-field" style={{ padding:'0.35rem', fontSize:'0.78rem', flex:1 }}
                  value={reportDates.from} onChange={e => setReportDates(p => ({ ...p, from: e.target.value }))} />
                <input type="date" className="input-field" style={{ padding:'0.35rem', fontSize:'0.78rem', flex:1 }}
                  value={reportDates.to} onChange={e => setReportDates(p => ({ ...p, to: e.target.value }))} />
              </div>
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:'0.6rem' }}>
              {reports.map(rep => (
                <div key={rep.id} style={{ padding:'0.65rem 0.75rem', border:'1px solid var(--border-color)', borderRadius:'var(--radius-sm)' }}>
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'0.2rem' }}>
                    <span style={{ fontWeight:700, fontSize:'0.85rem' }}>{rep.name}</span>
                    <span className="badge badge-info" style={{ fontSize:'0.6rem' }}>{rep.format}</span>
                  </div>
                  <p style={{ fontSize:'0.72rem', color:'var(--text-secondary)', marginBottom:'0.4rem' }}>{rep.description}</p>
                  <button className="btn btn-secondary" style={{ padding:'0.3rem 0.65rem', fontSize:'0.75rem' }}
                    onClick={() => handleDownload(rep.endpoint, rep.format)}>
                    <Download size={11}/><span>Download</span>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Create Ticket Modal ── */}
      {createOpen && (
        <div className="modal-overlay" onClick={() => setCreateOpen(false)}>
          <div className="modal-content card" onClick={e => e.stopPropagation()} style={{ maxWidth:500, width:'100%', padding:'2rem' }}>
            <h2 style={{ marginBottom:'1.5rem' }}>Raise a New Support Ticket</h2>
            <form onSubmit={handleCreateTicket} style={{ display:'flex', flexDirection:'column', gap:'1.1rem' }}>
              <div className="form-group" style={{ marginBottom:0 }}>
                <label className="form-label" htmlFor="t-title" style={{ display:'block', marginBottom:'0.4rem', fontWeight:600 }}>Title</label>
                <input id="t-title" type="text" className="input-field" placeholder="e.g. Cannot access VPN from home"
                  value={newTicket.title} onChange={e => setNewTicket(p => ({ ...p, title: e.target.value }))} required minLength={5} />
              </div>
              <div className="form-group" style={{ marginBottom:0 }}>
                <label className="form-label" htmlFor="t-desc" style={{ display:'block', marginBottom:'0.4rem', fontWeight:600 }}>Description</label>
                <textarea id="t-desc" className="input-field" style={{ minHeight:110, resize:'vertical' }}
                  placeholder="Describe the issue in detail..."
                  value={newTicket.description} onChange={e => setNewTicket(p => ({ ...p, description: e.target.value }))} required minLength={10} />
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1rem' }}>
                <div className="form-group" style={{ marginBottom:0 }}>
                  <label className="form-label" htmlFor="t-prio" style={{ display:'block', marginBottom:'0.4rem', fontWeight:600 }}>Priority</label>
                  <select id="t-prio" className="input-field" value={newTicket.priority} onChange={e => setNewTicket(p => ({ ...p, priority: e.target.value }))}>
                    <option value="low">Low</option><option value="medium">Medium</option>
                    <option value="high">High</option><option value="critical">Critical</option>
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom:0 }}>
                  <label className="form-label" htmlFor="t-cat" style={{ display:'block', marginBottom:'0.4rem', fontWeight:600 }}>Category</label>
                  <select id="t-cat" className="input-field" value={newTicket.category} onChange={e => setNewTicket(p => ({ ...p, category: e.target.value }))}>
                    {['General','Hardware','Software','Network','Access/Permissions','Email','Database','Security'].map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div style={{ display:'flex', gap:'1rem', justifyContent:'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setCreateOpen(false)} disabled={submitting}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Submitting...' : 'Create Ticket'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
