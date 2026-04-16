import { HiCheck, HiX, HiShieldCheck } from 'react-icons/hi';

export default function UserTable({ users, onToggleActive, onToggleRole }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#e8e8ed]">
            <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Name</th>
            <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Email</th>
            <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Role</th>
            <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Status</th>
            <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Joined</th>
            <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b border-[#f5f5f7] hover:bg-[#f5f5f7]/50 transition-colors">
              <td className="py-3 font-medium text-[#1d1d1f]">{user.full_name}</td>
              <td className="py-3 text-[#6e6e73]">{user.email}</td>
              <td className="py-3">
                <span
                  className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium ${
                    user.role === 'admin' ? 'bg-[#0071e3]/10 text-[#0071e3]' : 'bg-[#f5f5f7] text-[#6e6e73]'
                  }`}
                >
                  {user.role}
                </span>
              </td>
              <td className="py-3">
                <span
                  className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium ${
                    user.is_active ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'
                  }`}
                >
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td className="py-3 text-[#86868b] text-xs">{new Date(user.created_at).toLocaleDateString()}</td>
              <td className="py-3 flex gap-1.5">
                <button
                  onClick={() => onToggleActive(user.id, !user.is_active)}
                  className={`w-7 h-7 rounded-full flex items-center justify-center transition-all ${
                    user.is_active ? 'text-red-500 hover:bg-red-500/10' : 'text-green-500 hover:bg-green-500/10'
                  }`}
                  title={user.is_active ? 'Deactivate' : 'Activate'}
                >
                  {user.is_active ? <HiX className="w-3.5 h-3.5" /> : <HiCheck className="w-3.5 h-3.5" />}
                </button>
                <button
                  onClick={() => onToggleRole(user.id, user.role === 'admin' ? 'user' : 'admin')}
                  className="w-7 h-7 rounded-full flex items-center justify-center text-[#0071e3] hover:bg-[#0071e3]/10 transition-all"
                  title={user.role === 'admin' ? 'Demote to user' : 'Promote to admin'}
                >
                  <HiShieldCheck className="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
