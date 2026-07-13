import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { 
  LayoutDashboard, 
  MessageSquare, 
  BookOpen, 
  UploadCloud, 
  LogOut, 
  LifeBuoy,
  Ticket,
  UserCircle,
  Users
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuthStore();

  const menuItems = [
    { name: 'Dashboard', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Tickets', path: '/tickets', icon: <Ticket size={20} /> },
    { name: 'AI Assistant', path: '/assistant', icon: <MessageSquare size={20} /> },
    { name: 'Knowledge Base', path: '/knowledge', icon: <BookOpen size={20} /> },
  ];

  // Only show Document Upload for AGENT, MANAGER, ADMIN, SUPER_ADMIN
  const canUpload = user && ['agent', 'manager', 'admin', 'super_admin'].includes(user.role);
  if (canUpload) {
    menuItems.push({ name: 'Document Ingest', path: '/documents', icon: <UploadCloud size={20} /> });
  }

  // Only show User Management for ADMIN and SUPER_ADMIN
  const canManageUsers = user && ['admin', 'super_admin'].includes(user.role);
  if (canManageUsers) {
    menuItems.push({ name: 'User Management', path: '/users', icon: <Users size={20} /> });
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <LifeBuoy size={24} />
        <span>IntelliDesk AI</span>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink 
            key={item.name} 
            to={item.path} 
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            end={item.path === '/'}
          >
            {item.icon}
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <NavLink
          to="/profile"
          className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          style={{ marginBottom: '0.5rem' }}
        >
          <UserCircle size={18} />
          <span>
            {user ? `${user.first_name} ${user.last_name}` : 'Profile'}
          </span>
        </NavLink>
        <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={logout}>
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
