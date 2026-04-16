import { useEffect, useState } from 'react';
import { adminApi } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';

const RISK_COLORS = { Low: '#34c759', Medium: '#ff9f0a', High: '#ff3b30' };

export default function Analytics() {
  const [stats, setStats] = useState(null);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      adminApi.getStats(),
      adminApi.getDocuments(0, 100),
    ]).then(([s, d]) => {
      setStats(s);
      setDocs(d.documents || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center py-20">
      <div className="w-8 h-8 border-[3px] border-[#e8e8ed] border-t-[#0071e3] rounded-full animate-spin" />
    </div>
  );

  const riskDist = { Low: 0, Medium: 0, High: 0 };
  docs.forEach((d) => {
    if (d.risk_level && riskDist[d.risk_level] !== undefined) riskDist[d.risk_level]++;
  });
  const riskData = Object.entries(riskDist).map(([name, value]) => ({ name, value })).filter((d) => d.value > 0);

  const dayMap = {};
  docs.forEach((d) => {
    const day = new Date(d.upload_date).toLocaleDateString();
    dayMap[day] = (dayMap[day] || 0) + 1;
  });
  const uploadData = Object.entries(dayMap).slice(-7).map(([date, count]) => ({ date, count }));

  const tooltipStyle = { borderRadius: 12, border: 'none', boxShadow: '0 4px 24px rgba(0,0,0,0.08)', fontSize: 13 };

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#1d1d1f] tracking-tight">Analytics</h1>
        <p className="text-sm text-[#86868b] mt-0.5">Platform insights and trends</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk Distribution */}
        <div className="card">
          <h3 className="text-sm font-semibold text-[#1d1d1f] mb-4">Risk Distribution</h3>
          {riskData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={riskData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} dataKey="value" label={{ fontSize: 12 }} stroke="none">
                  {riskData.map((entry) => (
                    <Cell key={entry.name} fill={RISK_COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: '#6e6e73' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[#86868b] text-sm text-center py-10">No analyzed documents yet</p>
          )}
        </div>

        {/* Upload Activity */}
        <div className="card">
          <h3 className="text-sm font-semibold text-[#1d1d1f] mb-4">Upload Activity</h3>
          {uploadData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={uploadData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8e8ed" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#86868b' }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#86868b' }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" fill="#0071e3" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[#86868b] text-sm text-center py-10">No upload data yet</p>
          )}
        </div>

        {/* Platform Summary */}
        <div className="card lg:col-span-2">
          <h3 className="text-sm font-semibold text-[#1d1d1f] mb-4">Platform Summary</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-[#0071e3]/5 rounded-apple p-4 text-center">
              <p className="text-2xl font-bold text-[#0071e3] tracking-tight">{stats?.total_users || 0}</p>
              <p className="text-[11px] text-[#86868b] mt-0.5">Registered Users</p>
            </div>
            <div className="bg-[#5856d6]/5 rounded-apple p-4 text-center">
              <p className="text-2xl font-bold text-[#5856d6] tracking-tight">{stats?.total_documents || 0}</p>
              <p className="text-[11px] text-[#86868b] mt-0.5">Documents Uploaded</p>
            </div>
            <div className="bg-green-500/5 rounded-apple p-4 text-center">
              <p className="text-2xl font-bold text-[#34c759] tracking-tight">{stats?.documents_ready || 0}</p>
              <p className="text-[11px] text-[#86868b] mt-0.5">Analyzed</p>
            </div>
            <div className="bg-amber-500/5 rounded-apple p-4 text-center">
              <p className="text-2xl font-bold text-[#ff9f0a] tracking-tight">{stats?.avg_risk_score ? `${stats.avg_risk_score}%` : '—'}</p>
              <p className="text-[11px] text-[#86868b] mt-0.5">Avg Risk</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
