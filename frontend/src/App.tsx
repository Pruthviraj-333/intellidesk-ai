import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';

// Layouts
import { DashboardLayout } from './components/layout/DashboardLayout';
import { AuthLayout } from './components/layout/AuthLayout';

// Pages
import { Login } from './pages/auth/Login';
import { Register } from './pages/auth/Register';
import { Dashboard } from './pages/dashboard/Dashboard';
import { KBList } from './pages/knowledge/KBList';
import { KBDetail } from './pages/knowledge/KBDetail';
import { KBSearch } from './pages/knowledge/KBSearch';
import { KBEditor } from './pages/knowledge/KBEditor';
import { DocumentMgmt } from './pages/documents/DocumentMgmt';
import { AIAssistant } from './pages/assistant/AIAssistant';
import { TicketList } from './pages/tickets/TicketList';
import { TicketDetail } from './pages/tickets/TicketDetail';
import { ProfileSettings } from './pages/profile/ProfileSettings';
import { UserManagement } from './pages/users/UserManagement';

const App: React.FC = () => {
  const { initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>

        {/* Dashboard/Core App routes */}
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/assistant" element={<AIAssistant />} />
          <Route path="/knowledge" element={<KBList />} />
          <Route path="/knowledge/articles/:slug" element={<KBDetail />} />
          <Route path="/knowledge/search" element={<KBSearch />} />
          <Route path="/knowledge/new" element={<KBEditor />} />
          <Route path="/knowledge/edit/:slug" element={<KBEditor />} />
          <Route path="/documents" element={<DocumentMgmt />} />
          <Route path="/tickets" element={<TicketList />} />
          <Route path="/tickets/:id" element={<TicketDetail />} />
          <Route path="/profile" element={<ProfileSettings />} />
          <Route path="/users" element={<UserManagement />} />
        </Route>

        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
