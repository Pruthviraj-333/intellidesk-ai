import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Sun, Moon, Bell, BellOff, X, Ticket, AlertCircle, CheckCircle, Info } from 'lucide-react';
import api from '../../services/api';

interface Notification {
  id: number;
  title: string;
  body: string;
  type: string;
  resource_type: string | null;
  resource_id: number | null;
  is_read: boolean;
  created_at: string;
}

export const Header: React.FC = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark';
  });

  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifLoading, setNotifLoading] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
    } else {
      root.removeAttribute('data-theme');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Close popover on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Fetch notifications when popover opens
  useEffect(() => {
    if (showNotifications) {
      fetchNotifications();
    }
  }, [showNotifications]);

  // Fetch unread count on mount
  useEffect(() => {
    fetchUnreadCount();
    // Poll every 60 seconds
    const interval = setInterval(fetchUnreadCount, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchUnreadCount = async () => {
    try {
      const res = await api.get('/notifications/', { params: { is_read: false, per_page: 1 } });
      setUnreadCount(res.data.meta?.unread_count ?? res.data.pagination?.total ?? 0);
    } catch {
      // Silently fail — non-critical
    }
  };

  const fetchNotifications = async () => {
    setNotifLoading(true);
    try {
      const res = await api.get('/notifications/', { params: { per_page: 15 } });
      setNotifications(res.data.data || []);
      setUnreadCount(res.data.meta?.unread_count ?? 0);
    } catch {
      setNotifications([]);
    } finally {
      setNotifLoading(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.put('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // Silently fail
    }
  };

  const handleDelete = async (notifId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/notifications/${notifId}`);
      setNotifications(prev => prev.filter(n => n.id !== notifId));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      // Silently fail
    }
  };

  const handleNotificationClick = async (n: Notification) => {
    if (!n.is_read) {
      try {
        await api.put(`/notifications/${n.id}/read`);
        setNotifications(prev => prev.map(notif => notif.id === n.id ? { ...notif, is_read: true } : notif));
        setUnreadCount(prev => Math.max(0, prev - 1));
      } catch (err) {
        console.error('Failed to mark notification as read:', err);
      }
    }
    setShowNotifications(false);
    if (n.resource_type === 'ticket' && n.resource_id) {
      navigate(`/tickets/${n.resource_id}`);
    } else if (n.resource_type === 'incident' && n.resource_id) {
      navigate(`/incidents/${n.resource_id}`);
    }
  };

  const getNotifIcon = (type: string) => {
    switch (type) {
      case 'ticket_assigned': return <Ticket size={14} style={{ color: 'var(--primary)' }} />;
      case 'sla_warning': return <AlertCircle size={14} style={{ color: 'var(--danger)' }} />;
      case 'ticket_resolved': return <CheckCircle size={14} style={{ color: 'var(--success)' }} />;
      default: return <Info size={14} style={{ color: 'var(--text-secondary)' }} />;
    }
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const getInitials = () => {
    if (!user) return 'U';
    return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h2>IT Service Dashboard</h2>
      </div>

      <div className="topbar-right">
        <button 
          className="btn btn-secondary" 
          style={{ padding: '0.5rem', borderRadius: '50%' }}
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
        </button>

        {/* Notifications Bell */}
        <div ref={popoverRef} style={{ position: 'relative' }}>
          <button
            className="btn btn-secondary"
            style={{ padding: '0.5rem', borderRadius: '50%', position: 'relative' }}
            onClick={() => setShowNotifications(prev => !prev)}
            title="Notifications"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span style={{
                position: 'absolute',
                top: '2px',
                right: '2px',
                width: '16px',
                height: '16px',
                backgroundColor: 'var(--danger)',
                borderRadius: '50%',
                fontSize: '0.6rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                lineHeight: 1
              }}>
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Popover Panel */}
          {showNotifications && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 0.75rem)',
              right: 0,
              width: '360px',
              maxHeight: '480px',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
              display: 'flex',
              flexDirection: 'column',
              zIndex: 1000,
              overflow: 'hidden'
            }}>
              {/* Header */}
              <div style={{ 
                padding: '1rem 1.25rem', 
                borderBottom: '1px solid var(--border-color)', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center' 
              }}>
                <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Notifications</span>
                {unreadCount > 0 && (
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
                    onClick={handleMarkAllRead}
                  >
                    Mark all read
                  </button>
                )}
              </div>

              {/* Body */}
              <div style={{ overflowY: 'auto', flex: 1 }}>
                {notifLoading ? (
                  <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    Loading...
                  </div>
                ) : notifications.length === 0 ? (
                  <div style={{ padding: '2rem', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
                    <BellOff size={32} style={{ color: 'var(--text-muted)' }} />
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>You're all caught up!</span>
                  </div>
                ) : (
                  notifications.map(n => (
                    <div
                      key={n.id}
                      onClick={() => handleNotificationClick(n)}
                      style={{
                        padding: '0.875rem 1.25rem',
                        borderBottom: '1px solid var(--border-color)',
                        display: 'flex',
                        gap: '0.75rem',
                        alignItems: 'flex-start',
                        backgroundColor: n.is_read ? 'transparent' : 'rgba(99,102,241,0.07)',
                        transition: 'background 0.2s',
                        cursor: 'pointer'
                      }}
                    >
                      {/* Icon */}
                      <div style={{ marginTop: '2px', flexShrink: 0 }}>
                        {getNotifIcon(n.type)}
                      </div>

                      {/* Content */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ 
                          fontWeight: n.is_read ? 400 : 600, 
                          fontSize: '0.85rem', 
                          whiteSpace: 'nowrap', 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis' 
                        }}>
                          {n.title}
                        </div>
                        <div style={{ 
                          fontSize: '0.78rem', 
                          color: 'var(--text-secondary)', 
                          marginTop: '0.2rem',
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical' as const,
                        }}>
                          {n.body}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
                          {new Date(n.created_at).toLocaleString()}
                        </div>
                      </div>

                      {/* Delete */}
                      <button
                        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.2rem', flexShrink: 0 }}
                        onClick={(e) => handleDelete(n.id, e)}
                        title="Dismiss"
                      >
                        <X size={13} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="user-profile-menu">
          <div className="avatar">
            {getInitials()}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>
              {user ? `${user.first_name} ${user.last_name}` : 'Support User'}
            </span>
            <span className={`badge badge-info`} style={{ fontSize: '0.65rem', alignSelf: 'flex-start', padding: '0.1rem 0.4rem', marginTop: '0.1rem' }}>
              {user?.role || 'Guest'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
