import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext';
import { AuthModalProvider } from './context/AuthModalContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import PublicOnlyRoute from './components/auth/PublicOnlyRoute';

/* ── Page Components ──────────────────────────────────────────────────────── */
import Home from './pages/Home.jsx';
import Workspace from './pages/workspace/Workspace.jsx';
import Dashboard from './pages/workspace/Dashboard.jsx';
import Meetings from './pages/workspace/Meetings.jsx';
import Tasks from './pages/workspace/Tasks.jsx';
import Chat from './pages/workspace/Chat.jsx';
import Documentation from './pages/Documentation.jsx';
import Contact from './pages/Contact.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import NotFound from './pages/NotFound.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <AuthModalProvider>
          <Routes>
            <Route path="/" element={<App />}>
              <Route index element={<Home />} />
              <Route
                path="login"
                element={
                  <PublicOnlyRoute>
                    <Login />
                  </PublicOnlyRoute>
                }
              />
              <Route
                path="register"
                element={
                  <PublicOnlyRoute>
                    <Register />
                  </PublicOnlyRoute>
                }
              />
              <Route
                path="workspace"
                element={
                  <ProtectedRoute>
                    <Workspace />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/workspace/dashboard" replace />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="meetings" element={<Meetings />} />
                <Route path="tasks" element={<Tasks />} />
                <Route path="chat" element={<Chat />} />
              </Route>
              <Route path="chat" element={<Navigate to="/workspace/chat" replace />} />
              <Route path="docs" element={<Documentation />} />
              <Route path="contact" element={<Contact />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </AuthModalProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
