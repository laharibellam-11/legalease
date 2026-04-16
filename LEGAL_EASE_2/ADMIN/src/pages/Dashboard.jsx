import { useEffect, useState } from 'react';
import { adminApi } from '../services/api';
import StatsCard from '../components/StatsCard';
import { HiUsers, HiDocument, HiShieldExclamation, HiClock, HiCheckCircle, HiXCircle, HiTag } from 'react-icons/hi';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#34c759', '#0071e3', '#ff3b30'];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.getStats().then(setStats).finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-[3px] border-[#e8e8ed] border-t-[#0071e3] rounded-full animate-spin" />
    </div>
  );
  if (!stats) return <div className="text-red-500 text-sm">Failed to load stats</div>;

  const pieData = [
    { name: 'Ready', value: stats.documents_ready },
    { name: 'Processing', value: stats.documents_processing },
    { name: 'Error', value: stats.documents_error },
  ].filter((d) => d.value > 0);

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#1d1d1f] tracking-tight">Dashboard</h1>
        <p className="text-sm text-[#86868b] mt-0.5">Platform overview at a glance</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <StatsCard title="Total Users" value={stats.total_users} icon={HiUsers} color="text-[#0071e3]" />
        <StatsCard title="Total Documents" value={stats.total_documents} icon={HiDocument} color="text-[#5856d6]" />
        <StatsCard
          title="Avg Risk Score"
          value={stats.avg_risk_score ? `${stats.avg_risk_score}%` : '—'}
          icon={HiShieldExclamation}
          color={stats.avg_risk_score > 50 ? 'text-[#ff3b30]' : stats.avg_risk_score > 25 ? 'text-[#ff9f0a]' : 'text-[#34c759]'}
        />
        <StatsCard title="Total Clauses" value={stats.total_clauses || 0} icon={HiTag} color="text-[#5856d6]" />
        <StatsCard title="High Risk Docs" value={stats.high_risk_count || 0} icon={HiShieldExclamation} color="text-[#ff3b30]" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Document Status Pie */}
        <div className="card">
          <h3 className="text-sm font-semibold text-[#1d1d1f] mb-4">Document Status</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={80} dataKey="value" label={{ fontSize: 12 }} stroke="none">
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 24px rgba(0,0,0,0.08)', fontSize: 13 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[#86868b] text-sm text-center py-10">No documents yet</p>
          )}
          <div className="flex justify-center gap-4 mt-1">
            {pieData.map((d, i) => (
              <div key={d.name} className="flex items-center gap-1.5 text-xs text-[#6e6e73]">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i] }} />
                {d.name} ({d.value})
              </div>
            ))}
          </div>
        </div>

        {/* Quick Overview */}
        <div className="card">
          <h3 className="text-sm font-semibold text-[#1d1d1f] mb-4">Quick Overview</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-green-500/5 rounded-apple">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-green-500/10 flex items-center justify-center">
                  <HiCheckCircle className="w-4 h-4 text-green-600" />
                </div>
                <span className="text-sm text-[#1d1d1f]">Ready Documents</span>
              </div>
              <span className="text-lg font-bold text-green-600">{stats.documents_ready}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-[#0071e3]/5 rounded-apple">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-[#0071e3]/10 flex items-center justify-center">
                  <HiClock className="w-4 h-4 text-[#0071e3]" />
                </div>
                <span className="text-sm text-[#1d1d1f]">Processing</span>
              </div>
              <span className="text-lg font-bold text-[#0071e3]">{stats.documents_processing}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-red-500/5 rounded-apple">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-red-500/10 flex items-center justify-center">
                  <HiXCircle className="w-4 h-4 text-red-600" />
                </div>
                <span className="text-sm text-[#1d1d1f]">Errors</span>
              </div>
              <span className="text-lg font-bold text-red-600">{stats.documents_error}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
