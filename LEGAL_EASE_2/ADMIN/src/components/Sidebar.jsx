import { Link, useLocation, useNavigate } from 'react-router-dom';
import { HiHome, HiUsers, HiDocument, HiChartBar, HiLogout, HiScale } from 'react-icons/hi';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: HiHome },
  { path: '/users', label: 'Users', icon: HiUsers },
  { path: '/documents', label: 'Documents', icon: HiDocument },
  { path: '/analytics', label: 'Analytics', icon: HiChartBar },
];

export default function Sidebar({ onLogout }) {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    if (onLogout) onLogout();
    localStorage.removeItem('admin_access_token');
    localStorage.removeItem('admin_refresh_token');
    navigate('/login');
  };

  return (
    <aside className="w-60 fixed inset-y-0 left-0 bg-white/80 backdrop-blur-xl border-r border-[#e8e8ed] flex flex-col z-40">
      {/* Header */}
      <div className="px-5 py-5 border-b border-[#e8e8ed]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-apple bg-[#0071e3] flex items-center justify-center">
            <HiScale className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[#1d1d1f] tracking-tight">LegalEase</h1>
            <p className="text-[10px] text-[#86868b] uppercase tracking-widest">Admin</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-apple text-sm font-medium transition-all ${
                isActive
                  ? 'bg-[#0071e3] text-white shadow-sm'
                  : 'text-[#6e6e73] hover:bg-[#f5f5f7] hover:text-[#1d1d1f]'
              }`}
            >
              <item.icon className="w-[18px] h-[18px]" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="px-3 py-4 border-t border-[#e8e8ed]">
        <button
          onClick={handleLogout}
          className="flex items-center gap-2.5 text-[#86868b] hover:text-[#ff3b30] text-sm w-full px-3 py-2.5 rounded-apple transition-all hover:bg-red-500/5"
        >
          <HiLogout className="w-[18px] h-[18px]" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
