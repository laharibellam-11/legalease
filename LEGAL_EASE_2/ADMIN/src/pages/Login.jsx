import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../services/api';
import { HiScale } from 'react-icons/hi';
import toast from 'react-hot-toast';

export default function Login({ onLogin }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await adminApi.login(email, password);
      const user = await adminApi.getMe();
      if (user.role !== 'admin') {
        adminApi.logout();
        toast.error('Admin access required');
        return;
      }
      onLogin(user);
      toast.success('Welcome, Admin!');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f5f5f7]">
      <div className="w-full max-w-sm animate-fade-in">
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-[#0071e3] flex items-center justify-center shadow-apple-md mb-4">
            <HiScale className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-xl font-bold text-[#1d1d1f] tracking-tight">LegalEase Admin</h1>
          <p className="text-sm text-[#86868b] mt-1">Platform administration</p>
        </div>
        <div className="bg-white/80 backdrop-blur-xl rounded-apple-xl shadow-apple-md border border-white/60 p-7 animate-slide-up">
          <h2 className="text-base font-semibold text-[#1d1d1f] mb-5">Sign In</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#6e6e73] mb-1.5">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" required />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#6e6e73] mb-1.5">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" required />
            </div>
            <button type="submit" className="btn-primary w-full mt-2" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
