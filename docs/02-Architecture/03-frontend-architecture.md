# 3. Frontend Architecture

## 3.1 Overview

The frontend is a React 18 SPA built with TypeScript and Vite. It follows a **feature-based architecture** where each business module is a self-contained feature folder.

## 3.2 State Management Strategy

| State Type | Technology | Usage |
|-----------|-----------|-------|
| Server State | React Query (TanStack Query) | API data fetching, caching, mutations, pagination |
| Client State | Redux Toolkit | Auth state, UI state (sidebar, theme, modals) |
| Form State | React Hook Form | Form validation, submission |
| URL State | React Router v6 | Route params, search params, filters |

**Why this split:**
- React Query handles all server data (tickets, incidents, etc.) — automatic caching, refetching, and optimistic updates
- Redux Toolkit only manages truly global client state (auth tokens, theme preference, sidebar collapse)
- This avoids putting API data in Redux (anti-pattern)

## 3.3 Feature Module Structure

Each feature follows a consistent internal structure:

```
features/tickets/
├── components/           # Feature-specific React components
│   ├── TicketList.tsx
│   ├── TicketDetail.tsx
│   ├── TicketForm.tsx
│   ├── TicketFilters.tsx
│   ├── TicketTimeline.tsx
│   └── TicketAISidebar.tsx
├── hooks/                # Feature-specific hooks
│   ├── useTickets.ts     # React Query hook for ticket list
│   ├── useTicket.ts      # React Query hook for single ticket
│   └── useCreateTicket.ts# React Query mutation hook
├── services/             # API calls for this feature
│   └── ticketApi.ts      # Axios calls to /api/v1/tickets
├── types/                # TypeScript types for this feature
│   └── ticket.types.ts
├── utils/                # Feature-specific helpers
│   └── ticketHelpers.ts
└── index.ts              # Public exports
```

## 3.4 Shared Component Library

```
components/
├── ui/                   # Base design system components
│   ├── Button.tsx        # Variants: primary, secondary, ghost, danger
│   ├── Input.tsx         # Text, email, password, textarea
│   ├── Select.tsx        # Dropdown select
│   ├── Modal.tsx         # Dialog overlay
│   ├── Card.tsx          # Content card
│   ├── Badge.tsx         # Status/priority badges
│   ├── Avatar.tsx        # User avatar
│   ├── Tooltip.tsx       # Hover tooltip
│   ├── Spinner.tsx       # Loading spinner
│   ├── Skeleton.tsx      # Loading skeleton
│   ├── Toast.tsx         # Notification toast
│   └── Dropdown.tsx      # Dropdown menu
├── layout/
│   ├── AppLayout.tsx     # Main app shell (sidebar + header + content)
│   ├── Sidebar.tsx       # Navigation sidebar (role-aware)
│   ├── Header.tsx        # Top bar (search, notifications, profile)
│   ├── Footer.tsx        # Page footer
│   └── PageWrapper.tsx   # Page title, breadcrumbs, actions
├── data-display/
│   ├── DataTable.tsx     # Sortable, filterable table
│   ├── KPICard.tsx       # Metric card with icon + trend
│   ├── StatusBadge.tsx   # Ticket/incident status badge
│   ├── PriorityBadge.tsx # Priority indicator
│   ├── Timeline.tsx      # Activity timeline
│   ├── EmptyState.tsx    # No data placeholder
│   └── Pagination.tsx    # Page navigation
└── charts/
    ├── LineChart.tsx      # Trend lines
    ├── BarChart.tsx       # Bar/column charts
    ├── DonutChart.tsx     # Donut/pie charts
    ├── RadarChart.tsx     # Multi-axis comparison
    └── HeatMap.tsx        # Day × hour heat map
```

## 3.5 Routing Architecture

```typescript
// app/router.tsx

const router = createBrowserRouter([
  // Public routes
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/verify-email/:token', element: <VerifyEmailPage /> },
  
  // Protected routes (wrapped in AuthGuard + RoleGuard)
  {
    path: '/',
    element: <AuthGuard><AppLayout /></AuthGuard>,
    children: [
      { index: true, element: <DashboardPage /> },
      
      // Tickets
      { path: 'tickets', element: <TicketListPage /> },
      { path: 'tickets/new', element: <CreateTicketPage /> },
      { path: 'tickets/:id', element: <TicketDetailPage /> },
      
      // Incidents
      { path: 'incidents', element: <RoleGuard roles={['agent','manager','admin','super_admin']}><IncidentListPage /></RoleGuard> },
      { path: 'incidents/:id', element: <IncidentDetailPage /> },
      
      // Knowledge Base
      { path: 'knowledge', element: <KnowledgeBasePage /> },
      { path: 'knowledge/:id', element: <ArticleDetailPage /> },
      
      // AI Assistant
      { path: 'ai-assistant', element: <AIChatPage /> },
      
      // Analytics (Manager+)
      { path: 'analytics', element: <RoleGuard roles={['manager','admin','super_admin']}><AnalyticsPage /></RoleGuard> },
      { path: 'reports', element: <ReportsPage /> },
      
      // Admin (Admin+)
      { path: 'admin', element: <RoleGuard roles={['admin','super_admin']}><AdminLayout /></RoleGuard>,
        children: [
          { path: 'users', element: <UserManagementPage /> },
          { path: 'departments', element: <DepartmentManagementPage /> },
          { path: 'settings', element: <SettingsPage /> },
          { path: 'audit-logs', element: <AuditLogPage /> },
          { path: 'prompts', element: <PromptManagementPage /> },
          { path: 'system', element: <RoleGuard roles={['super_admin']}><SystemMonitorPage /></RoleGuard> },
        ]
      },
      
      // Profile
      { path: 'profile', element: <ProfilePage /> },
      { path: 'notifications', element: <NotificationsPage /> },
    ]
  },
  
  // 404
  { path: '*', element: <NotFoundPage /> },
]);
```

## 3.6 API Client Architecture

```typescript
// services/apiClient.ts

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL + '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Request interceptor — attach JWT
apiClient.interceptors.request.use((config) => {
  const token = store.getState().auth.accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor — handle 401 + auto-refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      const newToken = await refreshAccessToken();
      error.config.headers.Authorization = `Bearer ${newToken}`;
      return apiClient(error.config);
    }
    return Promise.reject(error);
  }
);
```

## 3.7 Theme System (Dark/Light Mode)

```
Theme Toggle Flow:
  User clicks toggle → Redux dispatch → CSS class on <html> → TailwindCSS dark: variants
  Preference saved to localStorage + user profile API
  
  System detection: window.matchMedia('(prefers-color-scheme: dark)')
  Priority: User preference > System preference > Default (dark)
```

## 3.8 WebSocket Client

```typescript
// services/socketClient.ts

import { io } from 'socket.io-client';

const socket = io(import.meta.env.VITE_WS_URL, {
  auth: { token: getAccessToken() },
  autoConnect: false,
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 5,
});

// Event handlers
socket.on('ticket_created', (data) => {
  queryClient.invalidateQueries(['tickets']);
  showToast('New ticket created', 'info');
});

socket.on('notification_new', (data) => {
  queryClient.invalidateQueries(['notifications']);
  showToast(data.message, data.type);
});

socket.on('dashboard_refresh', (data) => {
  queryClient.setQueryData(['dashboard-kpis'], data);
});
```
