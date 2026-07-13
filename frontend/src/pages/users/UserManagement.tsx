import React, { useEffect, useState, useCallback } from 'react';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import {
  Search, Shield, User, Users, RefreshCw,
  ChevronDown, CheckCircle, XCircle, AlertTriangle, Edit2
} from 'lucide-react';
import { Navigate } from 'react-router-dom';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Role {
  id: number;
  name: string;
  display_name?: string;
}

interface UserRecord {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  role: string;          // e.g. "employee", "agent" — matches API response
  status: string;
  department?: { id: number; name: string };
  created_at: string;
  last_login_at?: string;
}

// ─── Role badge styles ─────────────────────────────────────────────────────
const ROLE_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  super_admin: { label: 'Super Admin', color: '#ef4444', bg: '#fef2f2', icon: <Shield size={12} /> },
  admin:       { label: 'Admin',       color: '#f59e0b', bg: '#fffbeb', icon: <Shield size={12} /> },
  manager:     { label: 'Manager',     color: '#6366f1', bg: '#eef2ff', icon: <User size={12} /> },
  agent:       { label: 'Agent',       color: '#22c55e', bg: '#f0fdf4', icon: <User size={12} /> },
  employee:    { label: 'Employee',    color: '#64748b', bg: '#f8fafc', icon: <User size={12} /> },
};

// ─── Hierarchy description ─────────────────────────────────────────────────
const ROLE_DESC: Record<string, string> = {
  super_admin: 'Full platform access. Can assign any role including Admin. Cannot be modified by anyone except another Super Admin.',
  admin:       'Platform configuration & user management. Can assign roles up to Manager. Cannot modify Super Admins.',
  manager:     'Department-level oversight. Manages agents, views department analytics, downloads reports.',
  agent:       'IT Support staff. Handles assigned tickets, uses AI assistant, uploads knowledge documents.',
  employee:    'End users. Can raise tickets, track their own requests, and chat with the AI assistant.',
};

// ─── Component ────────────────────────────────────────────────────────────────
export const UserManagement: React.FC = () => {
  const { user: currentUser } = useAuthStore();

  // Guard: only admin+ can access this page
  if (!currentUser || !['admin', 'super_admin'].includes(currentUser.role)) {
    return <Navigate to="/" replace />;
  }

  const isSuperAdmin = currentUser.role === 'super_admin';

  const [users,       setUsers]       = useState<UserRecord[]>([]);
  const [roles,       setRoles]       = useState<Role[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [search,      setSearch]      = useState('');
  const [filterRole,  setFilterRole]  = useState('');
  const [editUser,    setEditUser]    = useState<UserRecord | null>(null);
  const [newRoleId,   setNewRoleId]   = useState<number | ''>('');
  const [saving,      setSaving]      = useState(false);
  const [toast,       setToast]       = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const [totalItems,  setTotalItems]  = useState(0);
  const [page,        setPage]        = useState(1);

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [usersRes, rolesRes] = await Promise.all([
        api.get('/users/', { params: { search: search || undefined, role: filterRole || undefined, page, per_page: 15 } }),
        api.get('/users/roles'),
      ]);
      setUsers(usersRes.data.data ?? []);
      setTotalItems(usersRes.data.pagination?.total_items ?? 0);
      setRoles(rolesRes.data.data ?? []);
    } catch (e: any) {
      showToast(e.response?.data?.error?.message || 'Failed to load users', 'error');
    } finally {
      setLoading(false);
    }
  }, [search, filterRole, page]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); fetchAll(); }, 400);
    return () => clearTimeout(t);
  }, [search]); // eslint-disable-line

  const openEdit = (u: UserRecord) => {
    setEditUser(u);
    // Derive current role_id from the roles list
    const matched = roles.find(r => r.name === u.role);
    setNewRoleId(matched?.id ?? '');
  };

  const saveRoleChange = async () => {
    if (!editUser || newRoleId === '') return;
    const currentRoleId = roles.find(r => r.name === editUser.role)?.id;
    if (newRoleId === currentRoleId) { setEditUser(null); return; }
    setSaving(true);
    try {
      await api.put(`/users/${editUser.id}`, { role_id: newRoleId });
      showToast(`${editUser.first_name}'s role updated successfully.`);
      setEditUser(null);
      fetchAll();
    } catch (e: any) {
      showToast(e.response?.data?.error?.message || 'Update failed.', 'error');
    } finally {
      setSaving(false);
    }
  };

  // Roles the current user is allowed to assign
  const assignableRoles = roles.filter(r => {
    if (isSuperAdmin) return true; // super_admin can assign any role
    return !['super_admin', 'admin'].includes(r.name); // admin can only assign up to manager
  });

  return (
    <div className="page-container">
      {/* ── Toast ── */}
      {toast && (
        <div style={{
          position: 'fixed', top: '1.5rem', right: '1.5rem', zIndex: 9999,
          background: toast.type === 'success' ? '#22c55e' : '#ef4444',
          color: '#fff', padding: '0.75rem 1.25rem', borderRadius: '0.5rem',
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)', fontWeight: 600, fontSize: '0.9rem',
        }}>
          {toast.type === 'success' ? <CheckCircle size={16}/> : <XCircle size={16}/>}
          {toast.msg}
        </div>
      )}

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.9rem' }}>User Management</h1>
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
            Manage user roles and access levels — {totalItems} total user{totalItems !== 1 ? 's' : ''}
          </p>
        </div>
        <button className="btn btn-secondary" onClick={fetchAll} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* ── Role Hierarchy Info Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem' }}>
        {Object.entries(ROLE_CONFIG).map(([key, cfg]) => (
          <div key={key} style={{
            padding: '0.75rem 1rem',
            border: `2px solid ${cfg.color}33`,
            borderRadius: '0.6rem',
            background: 'var(--bg-secondary)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.35rem' }}>
              <span style={{ color: cfg.color }}>{cfg.icon}</span>
              <span style={{ fontWeight: 700, fontSize: '0.85rem', color: cfg.color }}>{cfg.label}</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {ROLE_DESC[key]}
            </p>
          </div>
        ))}
      </div>

      {/* ── Filters ── */}
      <div className="card" style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: '220px' }}>
            <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="input-field"
              placeholder="Search by name or email..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ paddingLeft: '2.25rem' }}
            />
          </div>
          <div style={{ position: 'relative' }}>
            <select
              className="input-field"
              value={filterRole}
              onChange={e => { setFilterRole(e.target.value); setPage(1); }}
              style={{ paddingRight: '2rem', appearance: 'none', minWidth: '160px' }}
            >
              <option value="">All Roles</option>
              {roles.map(r => <option key={r.id} value={r.name}>{ROLE_CONFIG[r.name]?.label ?? r.name}</option>)}
            </select>
            <ChevronDown size={14} style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
          </div>
        </div>
      </div>

      {/* ── User Table ── */}
      <div className="card">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading users...</div>
        ) : users.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <Users size={40} style={{ marginBottom: '0.75rem', opacity: 0.4 }} />
            <p>No users found.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Current Role</th>
                  <th>Department</th>
                  <th>Status</th>
                  <th>Joined</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => {
                  const cfg = ROLE_CONFIG[u.role] ?? { label: u.role, color: '#64748b', bg: '#f8fafc', icon: <User size={12}/> };
                  const isProtected = u.role === 'super_admin' && !isSuperAdmin;
                  const isSelf = u.id === currentUser.id;
                  return (
                    <tr key={u.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          <div style={{
                            width: 32, height: 32, borderRadius: '50%',
                            background: `${cfg.color}22`, color: cfg.color,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: 700, fontSize: '0.8rem', flexShrink: 0,
                          }}>
                            {u.first_name[0]}{u.last_name[0]}
                          </div>
                          <span style={{ fontWeight: 600 }}>{u.first_name} {u.last_name}</span>
                          {isSelf && <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>(you)</span>}
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{u.email}</td>
                      <td>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                          padding: '0.25rem 0.6rem', borderRadius: '1rem', fontSize: '0.75rem',
                          fontWeight: 700, color: cfg.color, background: `${cfg.color}18`,
                          border: `1px solid ${cfg.color}33`,
                        }}>
                          {cfg.icon}{cfg.label}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                        {u.department?.name ?? <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                      </td>
                      <td>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                          fontSize: '0.75rem', fontWeight: 600,
                          color: u.status === 'active' ? '#22c55e' : '#f59e0b',
                        }}>
                          {u.status === 'active' ? <CheckCircle size={12}/> : <AlertTriangle size={12}/>}
                          {u.status}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td>
                        {isProtected || isSelf ? (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            {isSelf ? 'Cannot edit self' : 'Protected'}
                          </span>
                        ) : (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.3rem 0.65rem', fontSize: '0.78rem' }}
                            onClick={() => openEdit(u)}
                          >
                            <Edit2 size={13}/><span>Change Role</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalItems > 15 && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', padding: '1rem' }}>
            <button className="btn btn-secondary" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>← Prev</button>
            <span style={{ padding: '0.4rem 0.75rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Page {page} of {Math.ceil(totalItems / 15)}
            </span>
            <button className="btn btn-secondary" onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(totalItems / 15)}>Next →</button>
          </div>
        )}
      </div>

      {/* ── Role Change Modal ── */}
      {editUser && (
        <div className="modal-overlay" onClick={() => setEditUser(null)}>
          <div className="modal-content card" onClick={e => e.stopPropagation()} style={{
            maxWidth: 480,
            width: '100%',
            padding: '1.75rem',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <h2 style={{ marginBottom: '0.25rem' }}>Change User Role</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
              Update access level for <strong>{editUser.first_name} {editUser.last_name}</strong> ({editUser.email})
            </p>

            {/* Scrollable Body */}
            <div className="custom-scrollbar" style={{ flex: 1, overflowY: 'auto', margin: '1rem 0', paddingRight: '0.5rem' }}>
              {/* Current role */}
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                  Current Role
                </label>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                  padding: '0.35rem 0.8rem', borderRadius: '1rem', fontSize: '0.82rem', fontWeight: 700,
                  color: ROLE_CONFIG[editUser.role]?.color, background: `${ROLE_CONFIG[editUser.role]?.color}18`,
                }}>
                  {ROLE_CONFIG[editUser.role]?.icon}
                  {ROLE_CONFIG[editUser.role]?.label ?? editUser.role}
                </span>
              </div>

              {/* New role selector */}
              <div>
                <label style={{ display: 'block', fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.6rem' }}>
                  Assign New Role
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {assignableRoles.map(r => {
                    const cfg = ROLE_CONFIG[r.name];
                    const selected = newRoleId === r.id;
                    return (
                      <label key={r.id} style={{
                        display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                        padding: '0.75rem 1rem', borderRadius: '0.5rem', cursor: 'pointer',
                        border: `2px solid ${selected ? cfg?.color : 'var(--border-color)'}`,
                        background: selected ? `${cfg?.color}10` : 'var(--bg-secondary)',
                        transition: 'all 0.15s',
                      }}>
                        <input
                          type="radio"
                          name="new_role"
                          value={r.id}
                          checked={selected}
                          onChange={() => setNewRoleId(r.id)}
                          style={{ marginTop: '2px', accentColor: cfg?.color }}
                        />
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 700, fontSize: '0.88rem', color: cfg?.color }}>
                            {cfg?.icon}{cfg?.label ?? r.name}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem', lineHeight: 1.5 }}>
                            {ROLE_DESC[r.name]}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Fixed Footer Buttons */}
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
              <button className="btn btn-secondary" onClick={() => setEditUser(null)} disabled={saving}>Cancel</button>
              <button className="btn btn-primary" onClick={saveRoleChange} disabled={saving || newRoleId === roles.find(r => r.name === editUser.role)?.id}>
                {saving ? 'Saving...' : 'Confirm Role Change'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
