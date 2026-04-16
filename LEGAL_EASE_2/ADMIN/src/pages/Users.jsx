import { useEffect, useState } from 'react';
import { adminApi } from '../services/api';
import UserTable from '../components/UserTable';
import toast from 'react-hot-toast';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const limit = 20;

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getUsers(page * limit, limit);
      setUsers(data.users);
      setTotal(data.total);
    } catch {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page]);

  const handleToggleActive = async (userId, isActive) => {
    try {
      await adminApi.updateUser(userId, { is_active: isActive });
      toast.success(`User ${isActive ? 'activated' : 'deactivated'}`);
      fetchUsers();
    } catch {
      toast.error('Failed to update user');
    }
  };

  const handleToggleRole = async (userId, role) => {
    try {
      await adminApi.updateUser(userId, { role });
      toast.success(`Role updated to ${role}`);
      fetchUsers();
    } catch {
      toast.error('Failed to update role');
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#1d1d1f] tracking-tight">Users</h1>
        <p className="text-sm text-[#86868b] mt-0.5">{total} registered users</p>
      </div>

      <div className="card">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-7 h-7 border-[3px] border-[#e8e8ed] border-t-[#0071e3] rounded-full animate-spin" />
          </div>
        ) : (
          <UserTable users={users} onToggleActive={handleToggleActive} onToggleRole={handleToggleRole} />
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-[#e8e8ed]">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="btn-secondary text-sm disabled:opacity-40">
              Previous
            </button>
            <span className="text-xs text-[#86868b]">Page {page + 1} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="btn-secondary text-sm disabled:opacity-40">
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
