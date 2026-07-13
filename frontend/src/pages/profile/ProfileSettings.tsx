import React, { useEffect, useState } from 'react';
import { UserCircle, Mail, Building2, Shield, Save, Key, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';

interface ProfileData {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  status: string;
  department_id: number | null;
  phone?: string;
  created_at?: string;
}

type AlertType = { type: 'success' | 'error'; message: string } | null;

export const ProfileSettings: React.FC = () => {
  const { initialize } = useAuthStore();

  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [alert, setAlert] = useState<AlertType>(null);

  // Profile form
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');

  // Password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [isChangingPw, setIsChangingPw] = useState(false);
  const [pwAlert, setPwAlert] = useState<AlertType>(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setIsLoading(true);
    try {
      const res = await api.get('/users/me');
      const data: ProfileData = res.data.data;
      setProfile(data);
      setFirstName(data.first_name);
      setLastName(data.last_name);
      setPhone(data.phone || '');
    } catch (e) {
      setAlert({ type: 'error', message: 'Failed to load profile data.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstName.trim() || !lastName.trim()) return;
    setIsSaving(true);
    setAlert(null);
    try {
      await api.put('/users/me', { first_name: firstName, last_name: lastName, phone });
      await initialize(); // Refresh global user state
      setAlert({ type: 'success', message: 'Profile updated successfully.' });
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to save profile.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwAlert(null);
    if (newPassword !== confirmPassword) {
      setPwAlert({ type: 'error', message: 'New passwords do not match.' });
      return;
    }
    if (newPassword.length < 8) {
      setPwAlert({ type: 'error', message: 'New password must be at least 8 characters.' });
      return;
    }
    setIsChangingPw(true);
    try {
      await api.put('/users/me/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: confirmPassword
      });
      setPwAlert({ type: 'success', message: 'Password changed successfully.' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPwAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to change password.' });
    } finally {
      setIsChangingPw(false);
    }
  };

  const getRoleBadgeClass = (role: string) => {
    switch (role) {
      case 'super_admin': return 'badge-danger';
      case 'admin': return 'badge-warning';
      case 'manager': return 'badge-info';
      case 'agent': return 'badge-primary';
      default: return 'badge-success';
    }
  };

  const getInitials = () => {
    if (!profile) return 'U';
    return `${profile.first_name[0]}${profile.last_name[0]}`.toUpperCase();
  };

  if (isLoading) {
    return <div className="page-container" style={{ textAlign: 'center', padding: '3rem' }}>Loading profile...</div>;
  }

  return (
    <div className="page-container" style={{ maxWidth: '800px' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ margin: 0 }}>Profile & Settings</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Manage your account information and security settings
        </p>
      </div>

      {/* Profile Summary Card */}
      <div className="card" style={{ padding: '2rem', marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
        <div className="avatar" style={{ width: '72px', height: '72px', fontSize: '1.75rem', flexShrink: 0 }}>
          {getInitials()}
        </div>
        <div style={{ flex: 1 }}>
          <h2 style={{ margin: 0, marginBottom: '0.25rem' }}>
            {profile?.first_name} {profile?.last_name}
          </h2>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.9rem' }}>
              <Mail size={14} /> {profile?.email}
            </span>
            <span className={`badge ${getRoleBadgeClass(profile?.role || '')}`} style={{ textTransform: 'capitalize' }}>
              <Shield size={10} style={{ marginRight: '0.2rem' }} />
              {profile?.role?.replace('_', ' ')}
            </span>
            <span className="badge badge-secondary" style={{ textTransform: 'capitalize' }}>
              {profile?.status}
            </span>
          </div>
          {profile?.created_at && (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.5rem' }}>
              Member since {new Date(profile.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          )}
        </div>
      </div>

      {/* Edit Profile Card */}
      <div className="card" style={{ padding: '2rem', marginBottom: '2rem' }}>
        <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <UserCircle size={20} /> Personal Information
        </h3>

        {alert && (
          <div style={{
            padding: '0.875rem 1rem',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            backgroundColor: alert.type === 'success' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
            border: `1px solid ${alert.type === 'success' ? 'var(--success)' : 'var(--danger)'}`,
            color: alert.type === 'success' ? 'var(--success)' : 'var(--danger)',
            fontSize: '0.875rem'
          }}>
            {alert.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
            {alert.message}
          </div>
        )}

        <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" style={{ fontWeight: 600 }}>First Name</label>
              <input
                type="text"
                className="input-field"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                minLength={2}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" style={{ fontWeight: 600 }}>Last Name</label>
              <input
                type="text"
                className="input-field"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                minLength={2}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: 600 }}>Email Address</label>
            <div style={{ position: 'relative' }}>
              <input
                type="email"
                className="input-field"
                value={profile?.email || ''}
                disabled
                style={{ backgroundColor: 'var(--bg-tertiary)', cursor: 'not-allowed', paddingLeft: '2.5rem' }}
              />
              <Mail size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>Email address cannot be changed after verification.</p>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: 600 }}>Phone Number <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(optional)</span></label>
            <input
              type="tel"
              className="input-field"
              placeholder="+1 (555) 000-0000"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: 600 }}>Role</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 0.875rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-tertiary)' }}>
              <Building2 size={15} style={{ color: 'var(--text-muted)' }} />
              <span style={{ textTransform: 'capitalize', fontSize: '0.9rem' }}>{profile?.role?.replace('_', ' ')}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: '0.25rem' }}>(managed by admin)</span>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button type="submit" className="btn btn-primary" disabled={isSaving}>
              <Save size={16} />
              <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Change Password Card */}
      <div className="card" style={{ padding: '2rem' }}>
        <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Key size={20} /> Change Password
        </h3>

        {pwAlert && (
          <div style={{
            padding: '0.875rem 1rem',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            backgroundColor: pwAlert.type === 'success' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
            border: `1px solid ${pwAlert.type === 'success' ? 'var(--success)' : 'var(--danger)'}`,
            color: pwAlert.type === 'success' ? 'var(--success)' : 'var(--danger)',
            fontSize: '0.875rem'
          }}>
            {pwAlert.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
            {pwAlert.message}
          </div>
        )}

        <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: 600 }}>Current Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showCurrent ? 'text' : 'password'}
                className="input-field"
                placeholder="Your current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                style={{ paddingRight: '2.5rem' }}
              />
              <button
                type="button"
                onClick={() => setShowCurrent(p => !p)}
                style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0 }}
              >
                {showCurrent ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" style={{ fontWeight: 600 }}>New Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showNew ? 'text' : 'password'}
                  className="input-field"
                  placeholder="Min 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  style={{ paddingRight: '2.5rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowNew(p => !p)}
                  style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0 }}
                >
                  {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" style={{ fontWeight: 600 }}>Confirm New Password</label>
              <input
                type="password"
                className="input-field"
                placeholder="Repeat new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button type="submit" className="btn btn-primary" disabled={isChangingPw}>
              <Key size={16} />
              <span>{isChangingPw ? 'Updating...' : 'Update Password'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
