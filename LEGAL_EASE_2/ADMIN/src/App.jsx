import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { adminApi } from './services/api';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Documents from './pages/Documents';
import Analytics from './pages/Analytics';

function AdminLayout({ children, onLogout }) {
  return (
    <div className="flex min-h-screen bg-[#f5f5f7]">
      <Sidebar onLogout={onLogout} />
      <main className="flex-1 ml-60 p-6">{children}</main>
    </div>
  );
}

function ProtectedRoute({ user, children, onLogout }) {
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'admin') {
    adminApi.logout();
    return <Navigate to="/login" replace />;
  }
  return <AdminLayout onLogout={onLogout}>{children}</AdminLayout>;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('admin_access_token');
    if (token) {
      adminApi
        .getMe()
        .then((u) => {
          if (u.role === 'admin') setUser(u);
          else adminApi.logout();
        })
        .catch(() => adminApi.logout())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogout = () => {
    adminApi.logout();
    setUser(null);
  };

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f5f5f7]">
        <div className="w-8 h-8 border-[3px] border-[#e8e8ed] border-t-[#0071e3] rounded-full animate-spin" />
      </div>
    );

  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/dashboard" replace /> : <Login onLogin={setUser} />}
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute user={user} onLogout={handleLogout}>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/users"
          element={
            <ProtectedRoute user={user} onLogout={handleLogout}>
              <Users />
            </ProtectedRoute>
          }
        />
        <Route
          path="/documents"
          element={
            <ProtectedRoute user={user} onLogout={handleLogout}>
              <Documents />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute user={user} onLogout={handleLogout}>
              <Analytics />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
