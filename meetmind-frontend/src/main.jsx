import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import App from './App.jsx';

/* ── Page Components ──────────────────────────────────────────────────────── */
import Home from './pages/Home.jsx';
import Workspace from './pages/workspace/Workspace.jsx';
import Dashboard from './pages/workspace/Dashboard.jsx';
import Meetings from './pages/workspace/Meetings.jsx';
import Tasks from './pages/workspace/Tasks.jsx';
import Chat from './pages/workspace/Chat.jsx';
import Documentation from './pages/Documentation.jsx';
import Contact from './pages/Contact.jsx';
import NotFound from './pages/NotFound.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<Home />} />
          <Route path="workspace" element={<Workspace />}>
            <Route index element={<Navigate to="/workspace/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="meetings" element={<Meetings />} />
            <Route path="tasks" element={<Tasks />} />
            <Route path="chat" element={<Chat />} />
          </Route>
          <Route path="docs" element={<Documentation />} />
          <Route path="contact" element={<Contact />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
